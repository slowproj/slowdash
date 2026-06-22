# Created by Sanshiro Enomoto on 15 July 2026 #

import time, logging
from dataclasses import dataclass, field, asdict
from typing import Any

import slowlette
from sd_component import Component
from slowpy.mesh import Mesh


@dataclass
class RegistryRecord:
    key: str
    value: Any
    revision: int = 1
    updated: float = field(default_factory=time.time)

    
    @classmethod
    def create(cls, key:str, value:Any) -> "RegistryRecord":
        return cls(key=key, value=value, revision=1, updated=time.time())

    
    def update(self, value:Any) -> int:
        self.value = value
        self.revision += 1
        self.updated = time.time()
        return self.revision
    
    
    def to_dict(self) -> dict:
        return {
            'key': self.key,
            'value': self.value,
            'revision': self.revision,
            'updated': self.updated
        }


    
class Registry:
    def __init__(self):
        self._records: dict[str, RegistryRecord] = {}

        
    def export(self, mesh:Mesh):
        def rpc_set(key:str, value, cas_revision=None):
            return self.set(key, value, cas_revision=cas_revision)
        mesh.export('set', rpc_set)
        
        def rpc_get(key:str='', default=None, *, with_meta=False):
            return self.get(key, default, with_meta=with_meta)
        mesh.export('get', rpc_get)
        
        def rpc_keys(prefix:str=''):
            return self.keys(prefix)
        mesh.export('keys', rpc_keys)
        
        def rpc_delete(key:str, cas_revision=None):
            return self.delete(key, cas_revision=cas_revision)
        mesh.export('delete', rpc_delete)


    def set(self, key, value, *, cas_revision:int|None=None) -> int|None:
        """
        Arguments:
          - key (str): key
          - value (Any): value to write
          - cas_revision (int|None): write only if the CAS revision matches; None not to use CAS
        Return Value (int|None): new CAS revision on success, None otherwise (typically CAS mismatch)
        """
        
        record = self._records.get(key)
        if record is None:
            if cas_revision is not None:
                return None
            record = RegistryRecord.create(key, value)
            self._records[key] = record
        else:
            if cas_revision is not None and record.revision != cas_revision:
                return None
            record.update(value)

        logging.debug(f'MeshRegistry.set(): "{key}"={repr(value)} -> {record}')
        
        return record.revision
        
        
    def get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any:
        """
        Arguments:
          - key (str): key for the element to read; if it ends with a separater character,
            the key is treated as a subtree prefix and the tree under it is returned as a dict.
          - default (Any): value to return if the key does not exist
          - with_meta (bool): if True, return the full registry record including the value and the meta info
        Return Value (Any): value or meta including the value on success, the provided default otherwise
        """

        if key is None or len(key) == 0:
            key = '/'
        
        if not (key[-1].isalnum() or key[-1] == '_'):
            return self.get_tree(key, default, with_meta=with_meta)
        
        record = self._records.get(key)
        if record is None:
            return default

        logging.debug(f'MeshRegistry.get(): "{key}" --> {record}')
        
        return record.to_dict() if with_meta else record.value


    def get_tree(self, prefix:str, default:Any=None, *, with_meta:bool=False) -> Any:
        """
        Returns the all values under the "prefix" node as a value (for leaf) or as a dict (for node).
        If a node has both value and child nodes, the value will be stored in the "$value" field.
        Arguments:
          - key (str): key for the element to read, must end with a separater character.
          - default (Any): value to return if the key does not exist
          - with_meta (bool): if True, return the full registry record including the value and the meta info
        Return Value (Any): value or meta including the value on success, the provided default otherwise
        """

        root_key, sep = prefix[:-1], prefix[-1]
        scan_prefix = prefix if len(root_key) > 0 else ''
        tree = {}

        found = False
        root_record = self._records.get(root_key)
        if root_record is not None:
            tree['$value'] = root_record.to_dict() if with_meta else root_record.value
            found = True

        for key, record in self._records.items():
            if not key.startswith(scan_prefix):
                continue

            suffix = key[len(scan_prefix):]
            if len(suffix) == 0:
                continue

            node = tree
            parts = suffix.split(sep)
            for part in parts[:-1]:
                if part not in node:
                    child = {}
                    node[part] = child
                else:
                    child = node[part]
                if not isinstance(child, dict):
                    child = { '$value': child }
                    node[part] = child
                node = child

            leaf = parts[-1]
            value = record.to_dict() if with_meta else record.value
            if isinstance(node.get(leaf), dict):
                node[leaf]['$value'] = value
            else:
                node[leaf] = value
            found = True

        if not found:
            return default

        logging.debug(f'MeshRegistry.get_tree(): {prefix} --> {tree}')

        return tree
        
        

    def keys(self, prefix:str='', limit:int|None=1000)->list[str]:
        """
        Arguments:
          - prefix (str): key prefix for filtering
          - limit (int|None): maximum length of the list, None for no limit
        Return Value (list[str]): list of matching keys (full path including the prefix)
        """

        if len(prefix) == 1 and not (prefix[-1].isalnum() or prefix[-1] == '_'):
            scan_prefix = ''
        else:
            scan_prefix = prefix
        
        result = []
        for key in self._records:
            if key.startswith(scan_prefix):
                result.append(key)
                if limit is not None and len(result) >= limit:
                    break
        
        logging.debug(f'MeshRegistry.keys(): "{prefix}" --> {result}')
        
        return result


    def delete(self, key:str, *, cas_revision:int|None=None) -> bool:
        """
        Arguments:
          - key (str): key for the element to delete
          - cas_revision (int|None): delete only if the CAS revision matches; None not to use CAS
        Return Value (bool): True on success, False otherwise (key error or CAS mismatch)
        """
        
        record = self._records.get(key)
        if record is None:
            return False
        
        if cas_revision is not None and record.revision != cas_revision:
            return False

        del self._records[key]  # TODO: keep this as a tombstone for future CAS

        logging.debug(f'MeshRegistry.delete(): "{key}"')
        
        return True

    

class MeshRegistryComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self._registry_module_name = 'sd_mesh_registry'
        self._registry_data_prefix = '@registry:'
        self._pubsub_cache_prefix = '.pubsub.'

        self.mesh = None
        self.registry = Registry()
        

    @slowlette.on_event('post_startup')
    async def startup(self):
        # this needs to be done in "post_startup", as SlowMQ (if used) must be running.
        if self.mesh is None:
            self.mesh = Mesh('slowmq://localhost:18881', name=self._registry_module_name)
            self.registry.export(self.mesh)
            await self._setup_pubsub_cache()
            await self.mesh.aio_start()

        
    @slowlette.on_event('shutdown')
    async def shutdown(self):
        if self.mesh is not None:
            await self.mesh.aio_stop()


    async def _setup_pubsub_cache(self):
        async def handle_message(headers, data):
            topic = headers.get('topic')
            if topic is not None and not topic.startswith('sd.rpc'):
                self.registry.set(self._pubsub_cache_prefix + topic, data)
        await self.mesh.aio_subscribe('>', handle_message)

        
    @slowlette.get('/api/registry/keys')
    async def api_get_keys(self, prefix:str='', limit:int=100):
        return self.registry.keys(prefix, limit=limit)


    @slowlette.get('/api/registry/value')
    async def api_get_value(self, key:str, with_meta:bool=False):
        return self.registry.get(key, with_meta=with_meta)


    @slowlette.get('/api/data/{*}')
    async def api_get_data(self, request:slowlette.Request, length:float=3600, to:float=0):
        path_channels = request.path_str[len('/api/data/'):]   # channel name might contain "/"
        channels = path_channels.split(',') if path_channels else []

        now = time.time()
        start = (to if to > 0 else to + now) - length
        
        result = {}
        for ch in channels:
            if not ch.startswith(self._registry_data_prefix):
                continue
            key = ch[len(self._registry_data_prefix):]
            value = self.registry.get(key)
            if isinstance(value, dict):
                result[ch] = { 'start': start, 't': now - start, 'x':{ 'tree': value } }
            elif isinstance(value, (int, float, str)):
                result[ch] = { 'start': start, 't': now - start, 'x': value }
            else:
                try:
                    result[ch] = { 'start': start, 't': now - start, 'x': str(value) }
                except:
                    result[ch] = { 'start': start, 't': now - start, 'x': value }
            
        return result
            


if __name__ == '__main__':
    registry = Registry()

    registry.set('user', 'slowuser')
    registry.set('state/run/mode', 'physics')
    registry.set('state/run/number', 123)
    registry.set('state/run', 'running')

    print(registry.keys('/'))
    print(registry.keys('state/run'))
    print(registry.keys('.'))
    print(registry.get('state/run/mode'))
    print(registry.get('state/run'))
    print(registry.get('state/run/'))
    print(registry.get('state/'))
    print(registry.get('/'))

    print('########## PubSub cache')
    registry.set('.pubsub.foo.bar.buz', 'a')
    registry.set('.pubsub.foo.bar.qux', 'b')
    registry.set('.pubsub.foo.buz', 'c')
    print(registry.get('.pubsub.'))
    print(registry.get('.'))
    print(registry.get('.pubsub/'))
    print(registry.get('/'))

