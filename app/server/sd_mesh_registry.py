# Created by Sanshiro Enomoto on 15 July 2026 #

import time, json, glob, logging
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
        self.sep = '.'
        self.tail_wc = '>'
        self._records: dict[str, RegistryRecord] = {}
        
        self._persistent_nodes = set([
            'pubsub.form.inputs.'
        ])
        
        for filename in glob.glob('registry-*.json'):
            path = self._load_nodes(filename)
            if path is not None:
                self._persistent_nodes.add(f'{path}{self.sep}')
                logging.info(f'Registry: persistent values loaded: {path}: {self.get_tree(path)}')

        
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


    def set(self, key:str, value, *, cas_revision:int|None=None) -> int|None:
        """
        Arguments:
          - key (str): key for the element; if it ends with a tail wildcard character ('>'),
            the value is treated as a dict of subvalues and stored under a subtree prefixed by the key.
          - value (Any): value to write
          - cas_revision (int|None): write only if the CAS revision matches; None not to use CAS.
            Currently CAS is not implemented for set with subvalues (set_tree).
        Return Value (int|None): new CAS revision on success, None otherwise (typically CAS mismatch)
        """

        if len(key) > 0 and key[-1] == self.tail_wc:
            return self.set_tree(key[:-1], value)

        if len(key) > 0 and key[0] == self.sep:
            key = key[1:]
        if len(key) > 0 and key[-1] != self.sep:   # key must always ends with a sep
            key += self.sep
        
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

        for path in self._persistent_nodes:
            if key.startswith(path):
                self._save_nodes(path)
        
        return record.revision
        
        
    def get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any:
        """
        Arguments:
          - key (str): key for the element to read; if it ends with a tail wildcard character ('>'),
            the key is treated as a subtree prefix and the tree under it is returned as a dict.
          - default (Any): value to return if the key does not exist
          - with_meta (bool): if True, return the full registry record including the value and the meta info
        Return Value (Any): value or meta including the value on success, the provided default otherwise
        """

        if len(key) > 0 and key[-1] == self.tail_wc:
            return self.get_tree(key[:-1], default, with_meta=with_meta)

        if len(key) > 0 and key[0] == self.sep:
            key = key[1:]
        if len(key) > 0 and key[-1] != self.sep:
            key += self.sep
        
        record = self._records.get(key)
        if record is None:
            return default

        logging.debug(f'MeshRegistry.get(): "{key}" --> {record}')
        
        return record.to_dict() if with_meta else record.value


    def set_tree(self, path:str, doc) -> None:
        if len(path) > 0 and path[0] == self.sep:
            path = path[1:]
        if len(path) > 0 and path[-1] != self.sep:
            path += self.sep
        
        if not isinstance(doc, dict):
            self.set(path, doc)
        else:
            for key in doc:
                self.set_tree(f'{path}{key}{self.sep}', doc[key])
                
            
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

        tree = {}

        if len(prefix) > 0 and prefix[0] == self.sep:
            prefix = prefix[1:]
        if len(prefix) > 0 and prefix[-1] != self.sep:
            prefix += self.sep
        
        for key, record in self._records.items():
            if not key.startswith(prefix):
                continue

            suffix = key[len(prefix):]
            if len(suffix) == 0:
                continue
            parts = suffix.split(self.sep)
            if len(parts) < 2:
                continue  # should not happen

            node = tree
            for part in parts[:-2]:   # parts[-1] is empty as suffix always ends with a sep
                if part not in node:
                    child = {}
                    node[part] = child
                else:
                    child = node[part]
                if not isinstance(child, dict):
                    child = { '$value': child }
                    node[part] = child
                node = child

            leaf = parts[-2]
            value = record.to_dict() if with_meta else record.value
            if isinstance(node.get(leaf), dict):
                node[leaf]['$value'] = value
            else:
                node[leaf] = value

        root_record = self._records.get(prefix)
        if root_record is not None:
            if len(tree) == 0:
                tree = root_record.to_dict() if with_meta else root_record.value  # this is not a tree
            else:
                tree['$value'] = root_record.to_dict() if with_meta else root_record.value
        elif len(tree) == 0:
            tree = default

        logging.debug(f'MeshRegistry.get_tree(): {prefix} --> {tree}')

        return tree
        
        

    def keys(self, prefix:str='', limit:int|None=1000)->list[str]:
        """
        Arguments:
          - prefix (str): key prefix for filtering
          - limit (int|None): maximum length of the list, None for no limit
        Return Value (list[str]): list of matching keys (full path including the prefix)
        """

        if len(prefix) > 0 and prefix[0] == self.sep:
            prefix = prefix[1:]
        if len(prefix) > 0 and prefix[-1] != self.sep:
            prefix += self.sep

        result = []
        for key in self._records:
            if key.startswith(prefix):
                result.append(key.strip('.'))
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
        
        if len(key) > 0 and key[0] == self.sep:
            key = key[1:]
        if len(key) > 0 and key[-1] != self.sep:
            key += self.sep
        
        record = self._records.get(key)
        if record is None:
            return False
        
        if cas_revision is not None and record.revision != cas_revision:
            return False

        del self._records[key]  # TODO: keep this as a tombstone for future CAS

        logging.debug(f'MeshRegistry.delete(): "{key}"')
        
        return True


    def _load_nodes(self, filename:str) -> str:
        path = filename[len('registry-'):][:-len('.json')]
        try:
            with open(filename, 'r') as f:
                doc = json.load(f)
        except Exception as e:
            logging.warning(f'Unable to load registry values from file: {filename}: {e}')
            return None
                
        for subpath, value in doc.items():
            if subpath == '$root':
                key = path
            else:
                key = f'{path}.{subpath}'
                    
            self.set(key, value.get('value'))   # TODO: no meta for now...

        return path
            
        
    def _save_nodes(self, path:str) -> None:
        doc = {}
        for key in self.keys(path):
            subpath = key[len(path):]
            if len(subpath) == 0:
                subpath = '$root'
            value = self.get(key, with_meta=True)
            value.pop('key')
            doc[subpath] = value
        try:
            with open(f'registry-{path[:-1]}.json', 'w') as f:
                json.dump(doc, f)
        except Exception as e:
            logging.warning(f'Unable to save registry values to file: {path}: {e}')
                
    

class MeshRegistryComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self._registry_module_name = 'sd_mesh_registry'
        self._registry_data_prefix = '@registry:'
        self._pubsub_cache_prefix = 'pubsub'
        self._server_prefix = 'server'

        self.mesh = None
        self.registry = Registry()
        

    @slowlette.on_event('post_startup')
    async def startup(self):
        self.registry.set(f'{self._server_prefix}.url', self.project.server_url)
        
        # this needs to be done in "post_startup", as SlowMQ (if used) must be running.
        if self.mesh is None:
            if self.project.mesh_url is None:
                logging.error(f'WebMesh: Mesh URL is not set')
            else:
                self.mesh = Mesh(self.project.mesh_url, name=self._registry_module_name)
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
                self.registry.set(f'{self._pubsub_cache_prefix}.{topic}', data)
        await self.mesh.aio_subscribe('>', handle_message)

        
    @slowlette.get('/api/registry/keys/{path}')
    async def api_get_keys(self, path:str='.', limit:int=100):
        return self.registry.keys(path, limit=limit)


    @slowlette.get('/api/registry/value/{key}')
    async def api_get_value(self, key:str='.>', with_meta:bool=False):
        value = self.registry.get(key, with_meta=with_meta)
        if value is not None:
            return value
        elif with_meta:
            return {}
        elif len(key) > 0 and not (key[-1].isalnum() or key[-1] == '_'):
            return {}
        else:
            return None


    @slowlette.get('/api/data/{*}')
    async def api_get_data(self, request:slowlette.Request, length:float=3600, to:float=0):
        path_channels = request.path_str[len('/api/data/'):]   # channel name might contain "/"
        channels = path_channels.split(',') if path_channels else []
        
        result = {}
        now = time.time()
        start = (to if to > 0 else to + now) - length
        
        for ch in channels:
            if not ch.startswith(self._registry_data_prefix):
                continue
            key = ch[len(self._registry_data_prefix):]
            
            value = self.registry.get(key)
            if value is None:
                continue
            
            if isinstance(value, dict):
                x = { 'tree': value }
            elif isinstance(value, (int, float, str)):
                x = value
            else:
                try:
                    x = str(value)
                except:
                    x = value
                    
            result[ch] = { 'start': start, 't': now - start, 'x': x }
            
        return result
            


if __name__ == '__main__':
    registry = Registry()

    registry.set('user', {'name':'slowuser', 'email':'user@slow.com'})
    registry.set('state.run>', {'mode':'physics', 'number': 123})
    registry.set('state.run', 'running')

    print(f"registry.keys('.'): {registry.keys('.')}")
    print(f"registry.keys('state.run')): {registry.keys('state.run')}")
    
    print(f"registry.get('>')): {registry.get('>')}")
    print(f"registry.get('user')): {registry.get('user')}")
    print(f"registry.get('state.run.mode')): {registry.get('state.run.mode')}")
    print(f"registry.get('state.run')): {registry.get('state.run')}")
    print(f"registry.get('state.run.>')): {registry.get('state.run.>')}")
