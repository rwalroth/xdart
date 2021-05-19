import numpy as np

from ..datashare import SMBase, synced, locked
from ..datashare.smarray import bytes_to_shape, shape_to_bytes
from .int_data import parse_unit, int_1d_data


def _get_size(xsize, ysize):
    length = ysize * 5 + xsize * 2
    itemsize = np.dtype(float).itemsize
    size = int(itemsize * length)
    if size < itemsize * 2:
        size = itemsize * 2
    return size


def _get_bounds(arr: np.ndarray):
    if (arr == 0).all():
        return 0, 0
    else:
        c = np.nonzero(arr)[0]
        return c[0], len(c)


class SMIntData1D(SMBase):
    def __init__(self, addr=None, ysize=0, xsize=0, no_zeros=False, **kwargs):
        format_list = [
            '0'*128,
            int(0),
            int(0),
            int(ysize),
            int(xsize),
            int(0),
            True
        ]
        size = _get_size(xsize, ysize)
        SMBase.__init__(self, addr=addr, format_list=format_list, size=size, **kwargs)
        with self.mutex:
            if addr is None:
                self._shl[3] = ysize
                self._shl[4] = xsize
                self._shl[5] = 0
                self._shl[6] = no_zeros
            self.npview = np.ndarray(
                (self._shl[3] * 5 + self._shl[4] * 2,),
                dtype=float,
                buffer=self._shm.buf
            )
            self._set_arrays()

    def _set_arrays(self):
        for i, attr in enumerate(['raw', 'pcount', 'norm', 'sigma', 'sigma_raw']):
            super(SMBase, self).__setattr__(
                attr,
                self.npview[i*self._shl[3]:(i+1)*self._shl[3]]
            )
        for i, attr in enumerate(['ttheta', 'q']):
            super(SMBase, self).__setattr__(
                attr,
                self.npview[5*self._shl[3] + i*self._shl[4]:5*self._shl[3] + (i+1)*self._shl[4]]
            )

    def __setattr__(self, name, value):
        with self.mutex:
            self.check_memory()
            if name in ['raw', 'norm', 'pcount', 'sigma', 'sigma_raw', 'ttheta', 'q']:
                self.__dict__[name][:] = value[:]
            else:
                super(SMBase, self).__setattr__(name, value)

    @synced
    def resize(self, ysize, xsize=None):
        if xsize is None:
            _xsize = ysize
        else:
            _xsize = xsize
        size = _get_size(_xsize, ysize)
        self._recap(size)
        self._shl[3] = ysize
        self._shl[4] = xsize
        self._set_arrays()

    @synced
    def from_result(self, result, wavelength, monitor=1):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.

        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        self.ttheta, self.q = parse_unit(
            result, wavelength)

        self.pcount = result._count
        self.raw = result._sum_signal / monitor
        self.norm = self.raw / self.pcount
        if result.sigma is None:
            self.sigma = result._sum_signal
            self.sigma = np.sqrt(self.sigma)
            self.sigma = self.sigma / (self.pcount * monitor)
            self.sigma_raw = result._sum_signal / (monitor ** 2)
        else:
            self.sigma = result.sigma / monitor
            self.sigma_raw = ((result._count * result.sigma) ** 2) / (monitor ** 2)
