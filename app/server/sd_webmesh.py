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

        
    def public_config(self):
        return { 'webmesh': {
            'enabled': self.enabled,
            'attached': { topic:len(clients) for topic, clients in self._topic_client_table.items() },
        }}


    @slowlette.on_event('post_startup')
    async def startup(self):
        if not self.enabled:
            return
        
        # this needs to be done in "post_startup", as SlowMQ (if used) must be running.
        if self._mesh is None:
            self._mesh = Mesh('slowmq://localhost:18881', name='sd_webmesh')
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
            bad_clients = set()
            async with self._queue_lock:
                for client_id in self._topic_client_table.get(topic, set()):
                    queue = self._client_queue_table.get(client_id)
                    if queue:
                        if queue.qsize() < self._max_queue_size:
                            await queue.put((headers, data))
                        else:
                            bad_clients.add(client_id)

            for client_id in bad_clients:
                await self.detach_client(client_id)
                
        await self._mesh.aio_subscribe('data.>', process_message)
        await self._mesh.aio_subscribe('sd.task.stdout.>', process_message)
        
        
    @slowlette.eventstream('/event/webmesh/attach')
    async def attach(self, eventstream:slowlette.EventStream):
        try:
            await eventstream.accept()
            logging.info(f"EventStream Connected")
        except Exception as e:
            logging.warning(f"EventStream Accept Failed: {e}")

        client_id = secrets.token_urlsafe(32)
        queue = asyncio.Queue()
        self._client_queue_table[client_id] = queue
        disconnect_task = asyncio.create_task(eventstream.wait_disconnected())
        try:
            await eventstream.send({'client_id': client_id}, event='register')
            
            while True:
                queue_task = asyncio.create_task(queue.get())                
                done, pending = await asyncio.wait(
                    [queue_task, disconnect_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if disconnect_task in done:
                    queue_task.cancel()
                    await disconnect_task
                if queue_task not in done:
                    continue
                
                headers, body = await queue_task
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
            logging.info("EventStream Closed by client")
        finally:
            async with self._queue_lock:
                self._client_queue_table.pop(client_id)
                for client_set in self._topic_client_table.values():
                    client_set.discard(client_id)
            
            disconnect_task.cancel()
            try:
                await eventstream.close()
            except Exception:
                pass

            
    async def detach_client(self, client_id):
        async with self._queue_lock:
            self._client_queue_table.pop(client_id)
            for client_set in self._topic_client_table.values():
                client_set.discard(client_id)
        

            
    @slowlette.post('/api/webmesh/subscribe')
    async def subscribe(self, client_id:str, doc:slowlette.DictJSON):
        if client_id not in self._client_queue_table:
            return { 'status': 'error', 'message': f'unknown client id: {client_id}' }
        topic = doc.get('topic')
        if topic is None or len(topic) == 0:
            return { 'status': 'error', 'message': f'bad topic name: {topic}' }
        
        if topic not in self._topic_client_table:
            self._topic_client_table[topic] = set([client_id])
        else:
            self._topic_client_table[topic].add(client_id)

        return { 'status': 'ok' }
            
            

    @slowlette.post('/api/webmesh/publish/{topic}')
    async def publish(self, topic:str, doc:slowlette.DictJSON):
        if topic is None or len(topic) == 0:
            return { 'status': 'error', 'message': f'bad topic name: {topic}' }
        
        if not self._mesh:
            return { 'status': 'error', 'message': f'SlowMesh not running' }

        await self._mesh.aio_publish(topic, doc)
            
        return { 'status': 'ok' }
            
