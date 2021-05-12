import pickle
import sys
import warnings
from multiprocessing.shared_memory import SharedMemory, ShareableList
from multiprocessing.managers import SharedMemoryManager
from multiprocessing import RLock
from functools import wraps
from contextlib import contextmanager

from ._utils import DummyManager, SMBase


def lock(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.mutex:
            out = func(self, *args, **kwargs)
        return out
    return wrapper


class SMDict(SMBase):
    def __init__(self, addr=None, manager=None, mutex=None, size=0,
                 ratio=2) -> None:
        format_list = [
            '0'*128,
            int(size),
            int(size),
        ]
        super().__init__(addr, manager, mutex, format_list, size, ratio)


    def cleanup(self) -> None:
        self._shm.close()

    def move_to_end(self, key: str, last: Optional[bool] = True) -> None:
        warnings.warn(
            'The \'move_to_end\' method will be removed in future versions. '
            'Use pop and reassignment instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        with self.get_dict() as db:
            db[key] = db.pop(key)

    @lock
    def clear(self) -> None:
        self._save_memory({})

    def popitem(self, last=None):
        if last is not None:
            warnings.warn(
                'The \'last\' parameter will be removed in future versions. '
                'The \'popitem\' function now always returns last inserted.',
                DeprecationWarning,
                stacklevel=2,
            )
        with self.get_dict() as db:
            return db.popitem()

    @contextmanager
    @lock
    def get_dict(self):
        db = self._read_memory()
        try:
            yield db
        finally:
            self._save_memory(db)

    def __getitem__(self, key: str):
        return self._read_memory()[key]

    def __setitem__(self, key: str, value) -> None:
        with self.get_dict() as db:
            db[key] = value

    def __len__(self) -> int:
        return len(self._read_memory())

    def __delitem__(self, key: str) -> None:
        with self.get_dict() as db:
            del db[key]

    def __iter__(self):
        return iter(self._read_memory())

    def __reversed__(self):
        return reversed(self._read_memory())

    def __del__(self) -> None:
        self.cleanup()

    def __contains__(self, key: str) -> bool:
        return key in self._read_memory()

    def __eq__(self, other) -> bool:
        return self._read_memory() == other

    def __ne__(self, other) -> bool:
        return self._read_memory() != other

    if sys.version_info > (3, 8):
        def __or__(self, other):
            return self._read_memory() | other

        def __ror__(self, other):
            return other | self._read_memory()

        def __ior__(self, other):
            with self.get_dict() as db:
                db |= other
                return db

    def __str__(self) -> str:
        return str(self._read_memory())

    def __repr__(self) -> str:
        return repr(self._read_memory())

    def get(self, key: str, default=None):
        return self._read_memory().get(key, default)

    def keys(self):  # type: ignore
        return self._read_memory().keys()

    def values(self):  # type: ignore
        return self._read_memory().values()

    def items(self):  # type: ignore
        return self._read_memory().items()

    def pop(self, key: str, default=None):
        with self.get_dict() as db:
            if default is None:
                return db.pop(key)
            return db.pop(key, default)

    def update(self, other=(), /, **kwds):
        with self.get_dict() as db:
            db.update(other, **kwds)

    def setdefault(self, key: str, default=None):
        with self.get_dict() as db:
            return db.setdefault(key, default)

    def _save_memory(self, db) -> None:
        data = pickle.dumps(db, pickle.HIGHEST_PROTOCOL)
        self._shl[1] = len(data)
        if len(data) > self._shl[2]:
            shm = self._manager.SharedMemory(len(data * 2))
            shm[:len(self._shm.buf)] = self._shm.buf
            self._shl[2] = len(data * 2)
            self._shm.close()
            self._shm = shm
        self._shm.buf[: len(data)] = data  # type: ignore

    def _read_memory(self):
        try:
            return pickle.loads(self._shm.buf[:self._shl[1]].tobytes())
        except pickle.UnpicklingError:
            return {}
