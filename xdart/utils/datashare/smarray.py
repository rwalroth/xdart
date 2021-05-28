import traceback
from multiprocessing.managers import SharedMemoryManager
from multiprocessing.shared_memory import ShareableList, SharedMemory
from multiprocessing import RLock

import numpy as np

from .smbase import SMBase


def shape_to_bytes(shape):
    out = list(shape)
    out.append(-1)
    return np.array(out, dtype=int).tobytes()


def bytes_to_shape(buf):
    out = np.frombuffer(buf, dtype=int)
    return tuple(out[:-1])


class SMArray(SMBase):
    def __init__(self, array=None, addr=None, mutex=None, shape=(0,), dtype='int32',
                 manager=None, ratio=1):
        itemsize = np.dtype(dtype).itemsize
        size = int(itemsize * np.prod(shape))
        if size < itemsize * 2:
            size = itemsize * 2
        shape_length = len(shape)
        if shape_length < 16:
            shape_length = 16
        format_list = [
            '0' * 128,
            size,
            size,
            shape_to_bytes(list(range(shape_length))),
            '000'
        ]
        super().__init__(addr, manager, mutex, format_list, size, ratio)
        with self.mutex:
            if addr is None:
                self._shl[3] = shape_to_bytes(shape)
                self._shl[4] = np.dtype(dtype).char
            self._dtype = np.dtype(self._shl[4])
            self.npview = np.ndarray(
                bytes_to_shape(self._shl[3]),
                dtype=self._dtype,
                buffer=self._shm.buf
            )

    def check_memory(self) -> bool:
        with self.mutex:
            updated = super().check_memory()
            if self._dtype != np.dtype(self._shl[4]):
                self._dtype = np.dtype(self._shl[4])
                updated = True
            if self.npview.shape != bytes_to_shape(self._shl[3]):
                updated = True
            if updated:
                self.npview = np.ndarray(
                    bytes_to_shape(self._shl[3]),
                    dtype=self._dtype,
                    buffer=self._shm.buf
                )
        return updated

    def _recap(self, cap):
        with self.mutex:
            super()._recap(cap)
            if cap > self._shm.size:
                self.npview = np.ndarray(
                    bytes_to_shape(self._shl[3]),
                    dtype=self._dtype,
                    buffer=self._shm.buf
                )

    def set_dtype(self, dtype, resize=False):
        if np.dtype(dtype) != self._dtype:
            with self.mutex:
                self.check_memory()
                needed_cap = np.dtype(dtype).itemsize * np.prod(self.npview.shape)
                if needed_cap > self._shm.size:
                    if resize:
                        self._recap(needed_cap)
                    else:
                        raise ValueError("New dtype overflows buffer")
                self.npview = np.ndarray(self.npview.shape, dtype=dtype,
                                         buffer=self._shm.buf)
                self._dtype = np.dtype(dtype)
                self._shl[4] = self._dtype.char

    def reshape(self, shape, resize=False):
        with self.mutex:
            self.check_memory()
            if np.prod(shape) != np.prod(self.npview.shape):
                if not resize:
                    raise ValueError("New shape would change size, but resize flag is False")
                needed_cap = self.npview.dtype.itemsize * np.prod(shape)
                self._recap(needed_cap)
                self.npview = np.ndarray(shape, dtype=self._dtype,
                                         buffer=self._shm.buf)
            else:
                self.npview = self.npview.reshape(shape)
            self._shl[3] = shape_to_bytes(shape)


class SMArrayDescriptor:
    def __init__(self, signal=None):
        if signal is None:
            self.signal_emit = lambda x: None
        else:
            self.signal_emit = signal

    def __set_name__(self, owner, name):
        self.private_name = '_' + name

    def __get__(self, instance, owner):
        sma: SMArray = getattr(instance, self.private_name)
        update = sma.check_memory()
        if update:
            self.signal_emit(self.private_name)
        return sma.npview

    def __set__(self, instance, value):
        if isinstance(value, SMArray):
            setattr(instance, self.private_name, value)
        elif isinstance(value, np.ndarray):
            sma: SMArray = getattr(instance, self.private_name)
            sma.check_memory()
            if sma.npview.dtype != value.dtype:
                sma.set_dtype(value.dtype, resize=True)
            if sma.npview.shape != value.shape:
                sma.reshape(value.shape, resize=True)
            sma.npview[:] = value[:]
        else:
            raise TypeError(f"Attribute {self.private_name} must be set by " +
                            "ndarray or SMArray")


