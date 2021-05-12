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
