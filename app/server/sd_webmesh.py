# Created by Sanshiro Enomoto on 9 July 2026 #

import secrets, asyncio, logging

import slowlette
from sd_component import Component
from slowpy.mesh import Mesh


class DataCache:
    def __init__(self):
        self._channel_table = {}
        self._last_data = {}

        
    def find_data_type(self, value):
        datatype = None
        if type(value) is list:
            for i in range(len(value)):
                if value[-(i+1)] is None:
                    continue
                value = value[-(i+1)]
                break
            else:
                value = None
                
        if value is None:
            pass
        elif type(value) in [ int, float ]:
            datatype = 'numeric'
        elif type(value) is dict:
            if 'y' in value:
                datatype = 'graph'
            elif 'bins' in value:
                datatype = 'histogram'
            elif 'table' in value:
                datatype = 'table'
            elif 'tree' in value:
                datatype = 'tree'
        else:
            try:
                float(value)
                datatype = 'numeric'
            except:
                pass

        return datatype

                
    def process_data(self, body):
        for channel, data in body.items():
            self._last_data[channel] = data
            if channel in self._channel_table:
                return

            value = data.get('x', None)
            datatype = self.find_data_type(value)
            if datatype is None:
                logging.warning(f'Unknown data type: channel={channel}, value={value}')
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

        self._topic_list = [
            'sd.task.life_event.>', 'sd.task.heartbeat.>', 'sd.task.stdout.>'
        ]

        
    def public_config(self):
        return { 'webmesh': {
            'enabled': self.enabled,
            'attached': {
                topic: [ client_id[0:4] for client_id in clients ]
                for topic, clients in self._topic_client_table.items()
            },
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
        async def handle_message(headers, body):
            topic = headers.get('topic')

            # temporary topic matching
            subscribed_topic = topic
            if topic.startswith('data.'):
                channel = '.'.join(topic.split('.')[2:])
                self._data_cache.process_data(body)
                subscribed_topic = f'data.*.{channel}'
            else:
                for prefix in self._topic_list:
                    if topic.startswith(prefix[:-1]):
                        subscribed_topic = prefix
                        break

            async with self._queue_lock:
                for client_id in tuple(self._topic_client_table.get(subscribed_topic, set())):
                    queue = self._client_queue_table.get(client_id)
                    stop_event = self._client_stop_table.get(client_id)
                    if queue is None or stop_event is None:
                        continue
                    try:
                        queue.put_nowait((subscribed_topic, headers, body))
                    except asyncio.QueueFull:
                        logging.warning(f'WebMesh client queue full; detaching {client_id}')
                        stop_event.set()
                        
        await self._mesh.aio_subscribe('data.>', handle_message)
        for topic in self._topic_list:
            await self._mesh.aio_subscribe(topic, handle_message)
        
        
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
                
                subscribed_topic, headers, body = queue_task.result()
                message = {
                    'subscribed_topic': subscribed_topic,
                    'headers':headers,
                    'body':body
                }
                await eventstream.send(message, event='message')
                
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

            
    @slowlette.post('/api/webmesh/subscribe')
    async def subscribe(self, client_id:str, doc:slowlette.DictJSON):
        client_id = doc.get('client_id')
        topic = doc.get('topic')

        if not (topic.startswith('data.*.') or topic in self._topic_list):
            return { 'status': 'error', 'message': f'invalid topic: {topic}' }

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
