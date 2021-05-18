from .typedefs import int_t, dtype_to_key, key_to_dtype
from ._smutils import none_lesser, none_greater, multiply_none
from .smbase import SMBase


class SMVector(SMBase):
    def __init__(self, addr=None, manager=None, mutex=None, size=0, dtype=int_t,
                 ratio=2.0):
        format_list = [
            '0'*128,
            int(size),
            int(size),
            '0' * 16,
            float(ratio)
        ]
        super().__init__(addr, manager, mutex, format_list, size*dtype.size,
                         int(ratio*dtype.size))
        with self.mutex:
            if self._shl[3] == '0' * 16:
                self._shl[3] = dtype_to_key[dtype]
            self._dtype = key_to_dtype[self._shl[3]]
            self._shl[4] = ratio

    def size(self):
        with self.mutex:
            out = self._shl[1]
        return out//self._dtype.size

    def capacity(self):
        with self.mutex:
            out = self._shl[2]
        return out//self._dtype.size

    def dtype(self):
        with self.mutex:
            out = key_to_dtype[self._shl[3]]
        return out

    def push_back(self, val):
        with self.mutex:
            self.check_memory()
            if self._shl[1] == self._shl[2]:
                self._recap(self._shm.size*self._shl[4])
            idx = self._shl[1]
            self._shm.buf[idx:idx + self._dtype.size] = self._dtype.pack(val)
            self._shl[1] += self._dtype.size

    def _check_key(self, key):
        with self.mutex:
            if isinstance(key, slice):
                if none_greater(key.start, self._shl[1]) or none_lesser(key.start, (-self._shl[1])) or \
                        none_greater(key.stop, self._shl[1]) or none_lesser(key.stop, (-self._shl[1])):
                    raise IndexError("Index out of range")
                start = multiply_none(key.start, self._dtype.size)
                stop = multiply_none(key.stop, self._dtype.size)
                if start is not None:
                    if start < 0:
                        start += self._shl[1]
                else:
                    start = 0
                if stop is not None:
                    if stop < 0:
                        stop += self._shl[1]
                else:
                    stop = self._shl[1]
                return slice(
                    start,
                    stop,
                    multiply_none(key.step, self._dtype.size)
                )
            elif isinstance(key, int):
                size = self._shl[1]//self._dtype.size
                if key >= size or key < (-size):
                    raise IndexError("Index out of range")
                return key * self._dtype.size
            else:
                raise TypeError(f"index must be slice or int, not {type(key)}")

    def __getitem__(self, key):
        with self.mutex:
            self.check_memory()
            adj_key = self._check_key(key)
            if isinstance(adj_key, slice):
                out_bytes = self._shm.buf[adj_key]
                out = [self._dtype.unpack(out_bytes[i: i + self._dtype.size])
                       for i in range(0, len(out_bytes), self._dtype.size)]
                out_bytes.release()
            else:
                if adj_key < 0:
                    adj_key += self._shl[1]
                out = self._dtype.unpack(self._shm.buf[adj_key:adj_key + self._dtype.size])

        return out

    def __setitem__(self, key, value):
        with self.mutex:
            self.check_memory()
            adj_key = self._check_key(key)
            if isinstance(adj_key, slice):
                self._shm.buf[adj_key] = b''.join([self._dtype.pack(x) for x in value])
            else:
                if adj_key < 0:
                    adj_key += self._shl[1]
                self._shm.buf[adj_key:adj_key + self._dtype.size] = self._dtype.pack(value)
