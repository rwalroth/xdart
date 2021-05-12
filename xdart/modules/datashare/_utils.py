from multiprocessing import shared_memory
from multiprocessing.managers import SharedMemoryManager
from multiprocessing import RLock
import traceback


def none_greater(a, b):
    if a is None:
        return False
    return a >= b


def none_lesser(a, b):
    if a is None:
        return False
    return a < b


def multiply_none(a, b, default=None):
    if a is None:
        return default
    return a * b


class DummyManager:
    """Behaves like shared_memory.Manager without invoking process

    Used to ensure consistent behavior between using a remote manager
    and using this as its own contained process.
    """
    def __init__(self):
        self._shared = []

    def SharedMemory(self, size):
        """Returns a new SharedMemory instance with the specified size in
        bytes, untracked."""
        sms = shared_memory.SharedMemory(None, create=True, size=size)
        self._shared.append(sms)
        return sms

    def ShareableList(self, sequence):
        """Returns a new ShareableList instance populated with the values
        from the input sequence, untracked."""
        sl = shared_memory.ShareableList(sequence)
        self._shared.append(sl.shm)
        return sl

    def __del__(self):
        for s in self._shared:
            try:
                s.close()
                s.unlink()
            except:
                traceback.print_exc()


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

    def size(self):
        with self.mutex:
            out = self._shl[1]
        return out

    def capacity(self):
        with self.mutex:
            out = self._shl[2]
        return out

    def name(self):
        with self.mutex:
            out = self._shl.shm.name
        return out

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
        with self.mutex:
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
