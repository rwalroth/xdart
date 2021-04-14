import traceback
from multiprocessing.shared_memory import SharedMemory, ShareableList
from multiprocessing import shared_memory
from multiprocessing.managers import SharedMemoryManager
from multiprocessing import RLock

from .typedefs import int_t, dtype_to_key, key_to_dtype
from ._utils import none_lesser, none_greater, multiply_none, DummyManager


class HVector:
    def __init__(self, memory_name=None, mutex=None, size=0, dtype=int_t, manager_address=None):
        if mutex is None:
            self.mutex = RLock()
        else:
            self.mutex = mutex
        if manager_address is None:
            self._manager = DummyManager()
        else:
            self._manager = SharedMemoryManager(address=manager_address)
        capacity = size*2
        if capacity == 0:
            capacity = 2
        with self.mutex:
            if memory_name is None:
                self._shm = self._manager.SharedMemory(size=capacity*dtype.size)
                self._shm_addr = self._shm.name
                self._shl = self._manager.ShareableList([
                    '0'*256,
                    size,
                    capacity,
                    dtype_to_key[dtype]
                ])
                self._shl[0] = self._shm_addr
                self._shl_addr = self._shl.shm.name
            else:
                self._shl_addr = memory_name
                self._shl = ShareableList(name=memory_name)
                self._shm_addr = self._shl[0]
                self._shm = SharedMemory(name=self._shm_addr)
            self._dtype = key_to_dtype[self._shl[3]]

    def size(self):
        with self.mutex:
            out = self._shl[1]
        return out

    def capacity(self):
        with self.mutex:
            out = self._shl[2]
        return out

    def dtype(self):
        with self.mutex:
            out = key_to_dtype[self._shl[3]]
        return out

    def name(self):
        with self.mutex:
            out = self._shl.shm.name
        return out

    def _check_memory(self):
        with self.mutex:
            if self._shm_addr != self._shl[0]:
                try:
                    self._shm.close()
                except:
                    traceback.print_exc()
                self._shm = SharedMemory(name=self._shl[0])
                self._shm_addr = self._shl[0]

    def push_back(self, val):
        with self.mutex:
            self._check_memory()
            if self._shl[1] == self._shl[2]:
                new_shm = self._manager.SharedMemory(size=self._shm.size * 2)
                new_shm.buf[:self._shm.size] = self._shm.buf[:]
                try:
                    self._shm.close()
                    self._shm.unlink()
                except:
                    traceback.print_exc()
                self._shm = new_shm
                self._shm_addr = new_shm.name
                self._shl[0] = new_shm.name
                self._shl[2] = self._shl[1] * 2
            idx = self._shl[1]*self._dtype.size
            self._shm.buf[idx:idx + self._dtype.size] = self._dtype.pack(val)
            self._shl[1] += 1

    def _check_key(self, key):
        with self.mutex:
            if isinstance(key, slice):
                if none_greater(key.start, self._shl[1]) or none_lesser(key.start, (-self._shl[1])) or \
                        none_greater(key.stop, self._shl[1]) or none_lesser(key.stop, (-self._shl[1])):
                    raise IndexError("Index out of range")
                start = key.start
                stop = key.stop
                if start is not None:
                    if start < 0:
                        start += self._shl[1]
                    start *= self._dtype.size
                else:
                    start = 0
                if stop is not None:
                    if stop < 0:
                        stop += self._shl[1]
                    stop *= self._dtype.size
                else:
                    stop = self._dtype.size * self._shl[1]
                return slice(
                    start,
                    stop,
                    multiply_none(key.step, self._dtype.size)
                )
            elif isinstance(key, int):
                if key >= self._shl[1] or key < (-self._shl[1]):
                    raise IndexError("Index out of range")
                return key * self._dtype.size
            else:
                raise TypeError(f"index must be slice or int, not {type(key)}")

    def __getitem__(self, key):
        with self.mutex:
            self._check_memory()
            adj_key = self._check_key(key)
            if isinstance(adj_key, slice):
                out_bytes = self._shm.buf[adj_key]
                out = [self._dtype.unpack(out_bytes[i: i + self._dtype.size])
                       for i in range(0, len(out_bytes), self._dtype.size)]
                out_bytes.release()
            else:
                if adj_key < 0:
                    adj_key += self._shl[1]*self._dtype.size
                out = self._dtype.unpack(self._shm.buf[adj_key:adj_key + self._dtype.size])

        return out

    def __setitem__(self, key, value):
        with self.mutex:
            self._check_memory()
            adj_key = self._check_key(key)
            if isinstance(adj_key, slice):
                self._shm.buf[adj_key] = b''.join([self._dtype.pack(x) for x in value])
            else:
                if adj_key < 0:
                    adj_key += self._shl[1]
                self._shm.buf[adj_key:adj_key + self._dtype.size] = self._dtype.pack(value)

    def __del__(self):
        """
        Note: this does not unlink data. That is expected to be handled
        by the manager.
        """
        self._shm.close()
        self._shl.shm.close()
