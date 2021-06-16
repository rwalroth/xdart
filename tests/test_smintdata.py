import unittest
from multiprocessing.managers import SharedMemoryManager

from pyFAI import units
import numpy as np

# add xdart to path
import sys
# if __name__ == "__main__":
#     from config import xdart_dir
# else:
#     from .config import xdart_dir
xdart_dir = 'C:/Users/walroth/Documents/repos/xdart/'
if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.utils.containers.sm_int_data import SMIntData1D, SMIntData2D


class Result1D:
    def __init__(self, count, sum_signal, radial, sigma=None, unit=units.TTH_DEG):
        self._count = count
        self._sum_signal = sum_signal
        self.radial = radial
        self.sigma = sigma
        self.unit = unit


class TestSMIntData1D(unittest.TestCase):
    def test_init(self):
        count = np.zeros(1000)
        count[200:600] = 100
        sum_signal = np.round(count * np.random.rand(1000) * 10)
        radial = np.arange(1000)/2
        sigma = np.sqrt(sum_signal)

        result = Result1D(count, sum_signal, radial, sigma)
        intdata = SMIntData1D(no_zeros=True)
        intdata.from_result(result, 1e-10)
        self.assertEqual(intdata._shl[3], 400)
        self.assertEqual(intdata._shl[4], 1000)
