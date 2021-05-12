import unittest
from multiprocessing import shared_memory
from multiprocessing.managers import SharedMemoryManager

import sys

import numpy as np

xdart_dir = 'C:/Users/walroth/Documents/repos/xdart/'
if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.modules.datashare import SMArray, SMArrayDescriptor


class DummyArray:
    smarray = SMArrayDescriptor()

    def __init__(self, arr):
        self._smarray: SMArray = None
        self.smarray = arr


class TestSMArray(unittest.TestCase):
    def test_init(self):
        self._init_test('h')
        self._init_test('int16')
        self._init_test((np.dtype('int16')))
        self._init_test(int)

    def _init_test(self, dtype):
        sma1 = SMArray(shape=(20,5), dtype=dtype)
        sma2 = SMArray(addr=sma1.name())

        sma1.npview[5, 2] = 10
        self.assertEqual(sma1.npview[5, 2], sma2.npview[5, 2])

        sma1.npview[0, 3:6] = 12
        self.assertTrue((sma1.npview[0, 3:6] == sma2.npview[0, 3:6]).all())

    def test_decorator(self):
        smarray = SMArray(shape=(20,5), dtype=int)
        dummy = DummyArray(smarray)
        dummy.smarray = np.ones_like(smarray.npview)*20
        self.assertTrue((smarray.npview == dummy.smarray).all())
        self.assertTrue((dummy.smarray == 20).all())

    def test_reshape(self):
        smarray = SMArray(shape=(20,5), dtype='int16')
        dummy = DummyArray(smarray)
        dummy.smarray = np.arange(100, dtype='int16').reshape(10, 10)
        self.assertEqual(dummy.smarray.shape, (10,10))
        self.assertRaises(ValueError, smarray.reshape, (20,20))
        smarray.reshape((20,20), True)
        self.assertEqual(dummy.smarray.shape, (20, 20))

    def test_setdtype(self):
        smarray = SMArray(shape=(20,5), dtype='int16')
        self.assertRaises(ValueError, smarray.set_dtype, 'int64')
        smarray.set_dtype('int64', True)
        self.assertEqual(smarray.npview.dtype, np.dtype('int64'))


if __name__ == "__main__":
    unittest.main()
