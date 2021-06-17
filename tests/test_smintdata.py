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
from xdart.utils.containers import int_1d_data


class Result1D:
    def __init__(self, count, sum_signal, radial, sigma=None, unit=units.TTH_DEG):
        self._count = count
        self._sum_signal = sum_signal
        self.radial = radial
        self.sigma = sigma
        self.unit = unit


def make_result(shape, nzero1, nzero2):
    count = np.zeros(shape)
    count[nzero1:nzero2] = 100
    sum_signal = np.round(np.random.rand(shape) * 10) * count
    radial = np.linspace(5, 50, shape)
    sigma = np.sqrt(sum_signal)
    return Result1D(count, sum_signal, radial, sigma)


class TestSMIntData1D(unittest.TestCase):
    def setUp(self):
        self.result = make_result(1000, 200, 600)
        self.sm_intdata = SMIntData1D(no_zeros=True)
        self.sm_intdata.from_result(self.result, 1e-10)
        self.old_intdata = int_1d_data()
        self.old_intdata.from_result(self.result, 1e-10)

    def test_init(self):
        self.assertEqual(self.sm_intdata._shl[3], 400)
        self.assertEqual(self.sm_intdata._shl[4], 1000)

        intdata2 = SMIntData1D()
        intdata2.from_result(self.result, 1e-10)
        self.assertEqual(intdata2._shl[3], 1000)
        self.assertEqual(intdata2._shl[4], 1000)

    def test_from_result(self):
        for key in ['raw', 'pcount', 'sigma', 'norm']:
            self.assertTrue((self.sm_intdata.full(key) == getattr(self.old_intdata, key).full()).all())

        intdata = SMIntData1D(no_zeros=False)
        intdata.from_result(self.result, wavelength=1e-10)

        for key in ['raw', 'pcount', 'sigma', 'norm']:
            self.assertTrue((intdata.full(key) == getattr(self.old_intdata, key).full()).all())

    def test_addition(self):
        result2 = make_result(1000, 100, 150)

        sm_intdata2 = SMIntData1D(no_zeros=True)
        old_intdata2 = int_1d_data()

        sm_intdata2.from_result(result2, 1e-10)
        old_intdata2.from_result(result2, 1e-10)

        self.sm_intdata += sm_intdata2
        self.old_intdata += old_intdata2

        for key in ['raw', 'pcount', 'sigma', 'norm']:
            self.assertTrue((self.sm_intdata.full(key) == getattr(self.old_intdata, key).full()).all())

    @unittest.skip("Not implemented")
    def test_hdf5(self):
        # TODO: implement test for hdf5 saving
        pass
