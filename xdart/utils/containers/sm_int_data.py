import numpy as np

from ..datashare import SMBase, synced, locked
from ..datashare.smarray import bytes_to_shape, shape_to_bytes
from .int_data import parse_unit, int_1d_data


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
        length = ysize * 5 + xsize * 2
        itemsize = np.dtype(float).itemsize
        size = int(itemsize * length)
        if size < itemsize * 2:
            size = itemsize * 2
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
            self.raw = np.ndarray((0,))
            self.pcount = np.ndarray((0,))
            self.norm = np.ndarray((0,))
            self.sigma = np.ndarray((0,))
            self.sigma_raw = np.ndarray((0,))
            self.ttheta = np.ndarray((0,))
            self.q = np.ndarray((0,))
            self._set_arrays()

    def _set_arrays(self):
        start = 0
        end = self._shl[3]
        self.raw = self.npview[start:end]
        start = end
        end += self._shl[3]
        self.pcount = self.npview[start:end]
        start = end
        end += self._shl[3]
        self.norm = self.npview[start:end]
        start = end
        end += self._shl[3]
        self.sigma = self.npview[start:end]
        start = end
        end += self._shl[3]
        self.sigma_raw = self.npview[start:end]
        start = end
        end += self._shl[4]
        self.ttheta = self.npview[start:end]
        start = end
        end += self._shl[4]
        self.q = self.npview[start:end]

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
        length = ysize * 5 + xsize * 2

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
            self.sigma.data = np.sqrt(self.sigma.data)
            self.sigma /= (self.pcount * monitor)
            self.sigma_raw = result._sum_signal / (monitor ** 2)
        else:
            self.sigma = result.sigma / monitor
            self.sigma_raw = ((result._count * result.sigma) ** 2) / (monitor ** 2)
