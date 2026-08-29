# Created by Sanshiro Enomoto on 9 July 2026 #

import secrets, asyncio, logging

import slowlette
from sd_component import Component
from slowpy.mesh import Mesh


class WebMeshComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self._max_queue_size = 10
        
        self.enabled = app.is_async
        self._mesh = None

        self._queue_lock = asyncio.Lock()
        self._topic_client_table: dict[str,set[str]] = {}     # topic -> set of client_id
        self._client_queue_table: dict[str, asyncio.Queue] = {}   # client_id -> input message queue
        self._client_stop_table: dict[str, asyncio.Event] = {}   # client_id -> stop event (on quque full)

        
    def public_config(self):
        return { 'webmesh': {
            'enabled': self.enabled,
            'attached': { topic:[cid[0:4] for cid in clients] for topic, clients in self._topic_client_table.items() },
        }}


    @slowlette.on_event('post_startup')
    async def startup(self):
        if not self.enabled:
            return
        
        # this needs to be done in "post_startup", as SlowMQ (if used) must be running.
        if self._mesh is None:
            if self.project.mesh_url is None:
                logging.error(f'WebMesh: Mesh URL is not set')
            else:
                self._mesh = Mesh(self.project.mesh_url, name='sd_webmesh')
                await self._mesh.aio_start()
                await self._subscribe_mesh()
            
        
    @slowlette.on_event('shutdown')
    async def shutdown(self):        
        if self._mesh is not None:
            await self._mesh.aio_close()
            self._mesh = None


    async def _subscribe_mesh(self):
        async def process_message(headers, data):
            topic = headers.get('topic')
            if topic.startswith('data.'):
                topic = 'data.*.' + '.'.join(topic.split('.')[2:])
                
            async with self._queue_lock:
                for client_id in tuple(self._topic_client_table.get(topic, set())):
                    queue = self._client_queue_table.get(client_id)
                    stop_event = self._client_stop_table.get(client_id)
                    if queue is None or stop_event is None:
                        continue
                    try:
                        queue.put_nowait((headers, data))
                    except asyncio.QueueFull:
                        logging.warning(f'WebMesh client queue full; detaching {client_id}')
                        stop_event.set()

        await self._mesh.aio_subscribe('data.>', process_message)
        await self._mesh.aio_subscribe('sd.task.stdout.>', process_message)
        
        
    @slowlette.eventstream('/event/webmesh/attach')
    async def attach(self, eventstream:slowlette.EventStream):
        client_id = secrets.token_urlsafe(32)
        try:
            await eventstream.accept()
            logging.info(f'EventStream Connected: {client_id}')
        except Exception as e:
            logging.warning(f'EventStream Accept Failed: {e}')
            return

        queue = asyncio.Queue(maxsize=self._max_queue_size)
        stop_event = asyncio.Event()

        async with self._queue_lock:
            self._client_queue_table[client_id] = queue
            self._client_stop_table[client_id] = stop_event
            
        queue_task = None
        disconnect_task = asyncio.create_task(eventstream.wait_disconnected())
        stop_task = asyncio.create_task(stop_event.wait())
        
        try:
            await eventstream.send({'client_id': client_id}, event='register')
            
            while True:
                queue_task = asyncio.create_task(queue.get())
                
                done, _ = await asyncio.wait(
                    [ queue_task, disconnect_task, stop_task ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if disconnect_task in done:
                    queue_task.cancel()
                    await disconnect_task   # cause ConnectionClosed
                if stop_task in done:
                    queue_task.cancel()
                    break
                
                headers, body = queue_task.result()
                topic = headers.get('topic', '')
                if topic.startswith('data'):
                    event = 'data'
                    data = body
                elif topic.startswith('sd.task.stdout'):
                    event = 'stdout'
                    data = {
                        'source': headers.get('mesh_id'),
                        'text': body.get('text')
                    }
                else:
                    event = 'mesh'
                    data = { 'headers': headers, 'body': body }
                await eventstream.send(data, event=event)
                
        except slowlette.EventStreamConnectionClosed:
            logging.info(f'EventStream Closed by client: {client_id}')
            
        finally:
            tasks = [ task for task in (queue_task, disconnect_task, stop_task) if task is not None ]
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
                    
            async with self._queue_lock:
                self._client_queue_table.pop(client_id, None)
                self._client_stop_table.pop(client_id, None)

                empty_topics = []
                for topic, clients in self._topic_client_table.items():
                    clients.discard(client_id)
                    if not clients:
                        empty_topics.append(topic)
                for topic in empty_topics:
                    self._topic_client_table.pop(topic, None)
            
            try:
                await eventstream.close()
            except Exception:
                pass

            
    @slowlette.post('/api/webmesh/subscribe/{event}')
    async def subscribe(self, event:str, client_id:str, doc:slowlette.DictJSON):
        if event == 'data':
            channel = doc.get('channel')
            if channel is None or len(channel) == 0:
                return { 'status': 'error', 'message': f'bad channel name: {channel}' }
            topic = f'data.*.{channel}'
        elif event == 'stdout':
            task = doc.get('task')
            if task is None or len(task) == 0:
                return { 'status': 'error', 'message': f'bad task name: {task}' }
            topic = f'sd.task.stdout.{task}'
        else:
            return { 'status': 'error', 'message': f'bad streaming event name: {event}' }

        async with self._queue_lock:
            if client_id not in self._client_queue_table:
                return { 'status': 'error', 'message': f'unknown client id: {client_id}' }

            self._topic_client_table.setdefault(topic, set()).add(client_id)

        return { 'status': 'ok' }
            

    @slowlette.post('/api/webmesh/unsubscribe')
    async def unsubscribe(self, client_id:str):
        async with self._queue_lock:
            empty_topics = []
            for topic, clients in self._topic_client_table.items():
                clients.discard(client_id)
                if not clients:
                    empty_topics.append(topic)
            for topic in empty_topics:
                self._topic_client_table.pop(topic, None)
        
        return { 'status': 'ok' }
            

    @slowlette.post('/api/webmesh/publish/{topic}')
    async def publish(self, topic:str, doc:slowlette.DictJSON):
        if topic is None or len(topic) == 0:
            return { 'status': 'error', 'message': f'bad topic name: {topic}' }
        
        if not self._mesh:
            return { 'status': 'error', 'message': f'SlowMesh not running' }

        await self._mesh.aio_publish(topic, doc)
            
        return { 'status': 'ok' }
