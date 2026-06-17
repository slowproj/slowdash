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
    def __init__(self, mesh:Mesh):
        self._mesh = mesh
        self._records: dict[str, RegistryRecord] = {}

        def rpc_set(key:str, value, cas_revision=None):
            return self._set(key, value, cas_revision=cas_revision)
        self._mesh.export('set', rpc_set)
        
        def rpc_get(key:str, default=None, *, with_meta=False):
            return self._get(key, default, with_meta=with_meta)
        self._mesh.export('get', rpc_get)
        
        def rpc_keys(prefix:str):
            return self._keys(prefix)
        self._mesh.export('keys', rpc_keys)
        
        def rpc_delete(key:str, cas_revision=None):
            return self._delete(key, cas_revision=cas_revision)
        self._mesh.export('delete', rpc_delete)


    def _set(self, key, value, *, cas_revision=None) -> int|None:
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
        
        
    def _get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any:
        """
        Arguments:
          - key (str): key for the element to read
          - default (Any): value to return if the key does not exist
          - with_meta (bool): if True, return the full registry record including the value and the meta info
        Return Value (Any): value or meta including the value on success, the provided default otherwise
        """
        
        record = self._records.get(key)
        if record is None:
            return default

        logging.debug(f'MeshRegistry.get(): "{key}" --> {record}')
        
        return record.to_dict if with_meta else record.value


    def _keys(self, prefix:str, limit:int|None=1000)->list[str]:
        """
        Arguments:
          - prefix (str): key prefix for filtering
          - limit (int|None): maximum length of the list, None for no limit
        Return Value (list[str]): list of matching keys (full path including the prefix)
        """

        result = []
        for key in self._records:
            if key.startswith(prefix):
                result.append(key)
                if limit is not None and len(result) > limit:
                    break
        
        logging.error(f'MeshRegistry.keys(): "{prefix}" --> {result}')
        
        return result


    def _delete(self, key:str, *, cas_revision=int|None) -> bool:
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

        self._mesh = None
        self._registry = None


    @slowlette.on_event('post_startup')
    async def startup(self):
        # this needs to be done in "post_startup", as SlowMQ (if used) must be running.
        if self._mesh is None:
            self._mesh = Mesh('slowmq://localhost:18881', name="sd_mesh_registry")
            self._registry = Registry(self._mesh)
            await self._mesh.aio_start()

        
    @slowlette.on_event('shutdown')
    async def shutdown(self):
        if self._mesh is not None:
            await self._mesh.aio_stop()


    @slowlette.get('/api/registry')
    async def get_registry(self):
        return f"hello from Mesh Registry"
