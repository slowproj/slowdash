# Created by Sanshiro Enomoto on 9 July 2026 #

import secrets, asyncio, logging

import slowlette
from sd_component import Component
from slowpy.mesh import Mesh


class DataCache:
    def __init__(self):
        self._channel_table = {}
        self._last_data = {}


    def process_data(self, channel:str, data):
        self._last_data[channel] = data
        if channel in self._channel_table:
            return
        
        datatype = None
        x = data.get(channel, {}).get('x', None)
        if type(x) is list:
            for i in range(len(x)):
                if x[-(i+1)] is None:
                    continue
                x = x[-(i+1)]
                break
            else:
                x = None
                
        if x is None:
            pass
        elif type(x) in [ int, float ]:
            datatype = 'numeric'
        elif type(x) is dict:
            if 'y' in x:
                datatype = 'graph'
            elif 'bins' in x:
                datatype = 'histogram'
            elif 'table' in x:
                datatype = 'table'
            elif 'tree' in x:
                datatype = 'tree'
        else:
            try:
                float(x)
                datatype = 'numeric'
            except:
                pass

        if datatype is None:
            logging.warning(f'Unknown data type: channel={channel}, value={x}')
            datatype = 'unknown'
            
        self._channel_table[channel] = { 'name': channel, 'type': datatype, 'streaming': True }

        
    @property
    def channel_table(self):
        return self._channel_table

        

class ChannelMergerResponse(slowlette.Response):
    def __init__(self, data_cache:DataCache):
        super().__init__(content=[])
        self._data_cache = data_cache

            
    def merge_response(self, response) -> None:
        if response.content is None:
            response.content = []
        elif type(response.content) is not list:
            logging.error(f'WebMesh:ChannelMergerResponse: bad response data type to merge: {type(resonse.content)}')
            super().merge_response(response)
            return
            
        existing_channels = set([ ch.get('name', '__') for ch in response.content ])
        self.content = [
            ch for name, ch in self._data_cache.channel_table.items()
            if name not in existing_channels
        ]
        super().merge_response(response)


            
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

        self._data_cache = DataCache()

        
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
                channel = '.'.join(topic.split('.')[2:])
                self._data_cache.process_data(channel, data)
                topic = f'data.*.{channel}'
            elif topic.startswith('sd.task.life_event'):
                topic = f'sd.task.life_event'
            elif topic.startswith('sd.task.heartbeat'):
                topic = f'sd.task.heartbeat'
            elif topic.startswith('sd.task.stdout'):
                topic = f'sd.task.stdout'
                
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
        await self._mesh.aio_subscribe('sd.task.life_event.>', process_message)
        await self._mesh.aio_subscribe('sd.task.heartbeat.>', process_message)
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
                elif topic.startswith('sd.task.life_event'):
                    event = 'task_event'
                    data = body
                elif topic.startswith('sd.task.heartbeat'):
                    event = 'heartbeat'
                    data = body
                elif topic.startswith('sd.task.stdout'):
                    event = 'stdout'
                    data = {
                        'source': body.get('name'),
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
        elif event == 'task_event':
            topic = f'sd.task.life_event'
        elif event == 'heartbeat':
            topic = f'sd.task.heartbeat'
        elif event == 'stdout':
            topic = f'sd.task.stdout'
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


    @slowlette.get('/api/channels')
    async def get_stream_channels(self):
        return ChannelMergerResponse(self._data_cache)
