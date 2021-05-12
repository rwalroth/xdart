import unittest
from multiprocessing import shared_memory
from multiprocessing.managers import SharedMemoryManager

# add xdart to path
import sys
# if __name__ == "__main__":
#     from config import xdart_dir
# else:
#     from .config import xdart_dir
xdart_dir = 'C:/Users/walroth/Documents/repos/xdart/'
if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.modules.datashare.smvector import SMVector
from xdart.modules.datashare.typedefs import int_t, char_t, float_t, double_t


class TestSMVector(unittest.TestCase):
    # @unittest.skip("passed")
    def test_push(self):
        self._push_test(int_t)
        self._push_test(char_t)
        self._push_test(float_t)
        self._push_test(double_t)

    def _push_test(self, dtype):
        vector = SMVector(dtype=dtype)
        for i in range(20):
            vector.push_back(i)
        self.assertEqual(vector.size(), 20)
        self.assertEqual(vector.capacity(), 32)

    # @unittest.skip("passed")
    def test_named(self):
        self._named_test(int_t)
        self._named_test(char_t)
        self._named_test(float_t)
        self._named_test(double_t)

    def _named_test(self, dtype):
        vector1 = SMVector(dtype=dtype)
        vector2 = SMVector(addr=vector1.name())
        for i in range(0, 10, 2):
            vector1.push_back(i)
            vector2.push_back(i + 1)
        self.assertEqual(vector1.capacity(), vector2.capacity())
        self.assertEqual(vector1.size(), vector2.size())
        for i in range(10):
            self.assertEqual(vector1[i], vector2[i])

    # @unittest.skip("passed")
    def test_manager(self):
        self._manager_test(int_t)
        self._manager_test(char_t)
        self._manager_test(float_t)
        self._manager_test(double_t)

    def _manager_test(self, dtype):
        with SharedMemoryManager() as smm:
            address = smm.address
            vector = SMVector(manager=address, dtype=dtype)
            for i in range(10):
                vector.push_back(i)
            vector.__del__()

    # @unittest.skip("passed")
    def test_slice(self):
        self._slice_test(int_t)
        self._slice_test(char_t)
        self._slice_test(float_t)
        self._slice_test(double_t)

    def _slice_test(self, dtype):
        vector = SMVector(size=10, dtype=dtype)
        test_list = list(range(10))
        vector[:] = test_list[:]
        test_list[:3] = [10, 10, 10]
        vector[:3] = [10, 10, 10]
        test_list[-3:] = [20, 20, 20]
        vector[-3:] = [20, 20, 20]
        test_list[2:7] = [30, 30, 30, 30, 30]
        vector[2:7] = [30, 30, 30, 30, 30]
        test_list[4:-2] = [40, 40, 40, 40]
        vector[4:-2] = [40, 40, 40, 40]
        for i in range(10):
            self.assertEqual(vector[i], test_list[i])

if __name__ == "__main__":
    unittest.main()
