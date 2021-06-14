from multiprocessing.managers import SharedMemoryManager
from multiprocessing import shared_memory, RLock
import traceback
from functools import wraps

from ._smutils import DummyManager


def synced(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.mutex:
            self.check_memory()
            out = func(self, *args, **kwargs)
        return out
    return wrapper


def locked(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.mutex:
            out = func(self, *args, **kwargs)
        return out
    return wrapper


class SMBase:
    def __init__(self, addr=None, manager=None, mutex=None, format_list=None,
                 size=0, ratio=2):
        if mutex is None:
            self.mutex = RLock()
        else:
            self.mutex = mutex
        if manager is None:
            self._manager = DummyManager()
        elif isinstance(manager, SharedMemoryManager) or isinstance(manager, DummyManager):
            self._manager = manager
        else:
            self._manager = SharedMemoryManager(manager)
        capacity = int(size*ratio)
        if capacity == 0:
            capacity = ratio
        with self.mutex:
            if addr is None:
                if format_list is None:
                    raise ValueError("Either addr or format_list must be provided")
                self._shl = self._manager.ShareableList(format_list)
                self._shl_addr = self._shl.shm.name
                self._shm = self._manager.SharedMemory(capacity)
                self._shm_addr = self._shm.name
                self._shl[0] = self._shm_addr
                self._shl[1] = int(size)
                self._shl[2] = int(capacity)
            else:
                self._shl_addr = addr
                self._shl = shared_memory.ShareableList(name=addr)
                self._shm_addr = self._shl[0]
                self._shm = shared_memory.SharedMemory(name=self._shm_addr)

    @locked
    def size(self):
        return self._shl[1]

    @locked
    def capacity(self):
        return self._shl[2]

    @locked
    def name(self):
        return self._shl.shm.name

    def check_memory(self) -> bool:
        updated = False
        with self.mutex:
            if self._shm_addr != self._shl[0]:
                updated = True
                try:
                    self._shm.close()
                except:
                    traceback.print_exc()
                self._shm = shared_memory.SharedMemory(name=self._shl[0])
                self._shm_addr = self._shl[0]
        return updated

    def _recap(self, cap: int):
        if cap > self._shm.size:
            new_shm = self._manager.SharedMemory(size=int(cap))
            new_shm.buf[:self._shm.size] = self._shm.buf[:]
            try:
                self._shm.close()
                self._shm.unlink()
            except:
                traceback.print_exc()
            self._shm = new_shm
            self._shm_addr = new_shm.name
            self._shl[0] = new_shm.name
            self._shl[2] = int(cap)

    def __del__(self):
        """
        Note: this does not unlink data. That is expected to be handled
        by the manager.
        """
        self._shm.close()
        self._shl.shm.close()
