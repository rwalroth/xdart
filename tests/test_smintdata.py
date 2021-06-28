import unittest
from multiprocessing.managers import SharedMemoryManager
import tempfile

from pyFAI import units
import numpy as np
import h5py

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
from xdart.utils.containers import int_1d_data, int_2d_data


class Result1D:
    def __init__(self, count, sum_signal, radial, sigma=None, unit=units.TTH_DEG, azimuthal=None):
        self._count = count
        self._sum_signal = sum_signal
        self.radial = radial
        self.sigma = sigma
        self.unit = unit
        self.azimuthal = azimuthal


def make_result(shape, nzero1, nzero2):
    count = np.zeros(shape)
    count[nzero1:nzero2] = 100
    sum_signal = np.round(np.random.rand(shape) * 10) * count
    radial = np.linspace(5, 50, shape)
    sigma = np.sqrt(sum_signal)
    return Result1D(count, sum_signal, radial, sigma)


def make_result2d(shape, nzero1, nzero2):
    count = np.zeros(shape)
    count[nzero1[0]:nzero1[1], nzero2[0]:nzero2[1]] = 100
    print(np.nonzero(count))
    sum_signal = np.round(np.random.rand(np.product(shape)) * 10).reshape(shape) * count
    print(np.nonzero(sum_signal))
    radial = np.linspace(5, 50, shape[0])
    azimuthal = np.linspace(40, 140, shape[1])
    sigma = np.sqrt(sum_signal)
    return Result1D(count, sum_signal, radial, sigma, azimuthal=azimuthal)


class TestSMIntData1D(unittest.TestCase):
    def setUp(self):
        self.result = make_result(1000, 200, 600)
        self.sm_intdata = SMIntData1D(no_zeros=True)
        self.sm_intdata.from_result(self.result, 1e-10)
        self.old_intdata = int_1d_data()
        self.old_intdata.from_result(self.result, 1e-10)

        self.result2d = make_result2d((300, 300), (100, 200), (75, 175))
        self.sm_intdata2d = SMIntData2D(no_zeros=True)
        self.sm_intdata2d.from_result(self.result2d, 1e-10)
        self.old_intdata2d = int_2d_data()
        self.old_intdata2d.from_result(self.result2d, 1e-10)

    def test_init(self):
        self.assertEqual(self.sm_intdata._shl[3], 400)
        self.assertEqual(self.sm_intdata._shl[4], 1000)
        self.assertEqual(self.sm_intdata2d._shl[3], 100)
        self.assertEqual(self.sm_intdata2d._shl[4], 300)
        self.assertEqual(self.sm_intdata2d._shl[7], 100)
        self.assertEqual(self.sm_intdata2d._shl[8], 300)

        intdata2 = SMIntData1D()
        intdata2.from_result(self.result, 1e-10)
        self.assertEqual(intdata2._shl[3], 1000)
        self.assertEqual(intdata2._shl[4], 1000)

    def test_from_result(self):
        self._check_old_sm_equal()

        intdata = SMIntData1D(no_zeros=False)
        intdata.from_result(self.result, wavelength=1e-10)

        for key in ['raw', 'pcount', 'sigma', 'norm', 'sigma_raw']:
            self.assertTrue((intdata.full(key) == getattr(self.old_intdata, key).full()).all())
        for key in ['ttheta', 'q']:
            self.assertTrue((getattr(intdata, key) == getattr(self.old_intdata, key)).all())

    def test_addition(self):
        result2 = make_result(1000, 100, 150)

        sm_intdata2 = SMIntData1D(no_zeros=True)
        old_intdata2 = int_1d_data()

        sm_intdata2.from_result(result2, 1e-10)
        old_intdata2.from_result(result2, 1e-10)

        self.sm_intdata += sm_intdata2
        self.old_intdata += old_intdata2

        self._check_old_sm_equal()

    def _check_old_sm_equal(self):
        for key in ['raw', 'pcount', 'sigma', 'norm', 'sigma_raw']:
            self.assertTrue((self.sm_intdata.full(key) == getattr(self.old_intdata, key).full()).all())
        for key in ['ttheta', 'q']:
            self.assertTrue((getattr(self.sm_intdata, key) == getattr(self.old_intdata, key)).all())

    # @unittest.skip("Not implemented")
    def test_hdf5(self):
        # TODO: implement test for hdf5 saving
        with tempfile.TemporaryFile() as file:
            with h5py.File(file, 'w') as hfile:
                self.sm_intdata.to_hdf5(hfile)
                read_intdata = SMIntData1D()
                read_intdata.from_hdf5(hfile)
                for i, val in enumerate(self.sm_intdata._shl):
                    if i > 0:
                        self.assertEqual(val, read_intdata._shl[i])
        for key in ['raw', 'pcount', 'sigma', 'norm', 'sigma_raw']:
            self.assertTrue((self.sm_intdata.full(key) == read_intdata.full(key)).all())
        for key in ['ttheta', 'q']:
            self.assertTrue((getattr(self.sm_intdata, key) == getattr(read_intdata, key)).all())
