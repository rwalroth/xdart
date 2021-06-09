import copy
import warnings

import numpy as np

from ..datashare import SMBase, synced, locked
from ..datashare.smarray import bytes_to_shape, shape_to_bytes
from .. import _utils as utils
from .int_data import parse_unit, int_1d_data


def _get_size(full_shape, sub_shape):
    length = np.product(sub_shape) * 5 + np.product(full_shape) * 2
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
    def __init__(self, addr=None, sub_shape=0, full_shape=0, no_zeros=False, **kwargs):
        format_list = [
            '0'*128, # shm address
            int(0), # size
            int(0), # capacity
            int(sub_shape), # sub_shape
            int(full_shape), # full_shape
            int(0), # offset for sub data (NOT IMPLEMENTED SHOULD STAY 0)
            True # is non_zero being used (NOT IMPLEMENTED SHOULD STAY FALSE)
        ]
        size = _get_size(full_shape, sub_shape)
        SMBase.__init__(self, addr=addr, format_list=format_list, size=size, **kwargs)
        with self.mutex:
            if addr is None:
                self._shl[3] = sub_shape
                self._shl[4] = full_shape
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

    @synced
    def __setattr__(self, name, value):
        if name in ['raw', 'norm', 'pcount', 'sigma', 'sigma_raw']:
            if value.shape != self.__dict__[name].shape:
                self.resize(sub_shape=value.shape)
            self.__dict__[name][:] = value[:]
        elif name in ['ttheta', 'q']:
            if value.shape != self.__dict__[name].shape:
                self.resize(full_shape=value.shape)
            self.__dict__[name][:] = value[:]
        else:
            super(SMBase, self).__setattr__(name, value)

    @synced
    def resize(self, sub_shape=None, full_shape=None):
        if sub_shape is None:
            _sub_shape = self._shl[3]
        else:
            _sub_shape = sub_shape
        if full_shape is None:
            _full_shape = self._shl[4]
        else:
            _full_shape = full_shape
        size = _get_size(_full_shape, sub_shape)
        self._recap(size)
        self._shl[3] = sub_shape
        self._shl[4] = full_shape
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

    @synced
    def to_hdf5(self, grp, compression=None):
        """Saves data to hdf5 file.

        args:
            grp: h5py Group or File, where the data will be saved
            compression: str, compression algorithm to use. See h5py
                documentation.
        """
        utils.attributes_to_h5(self, grp, ['raw', 'norm', 'pcount', 'sigma', 'sigma_raw', 'ttheta', 'q'],
                               compression=compression)

    @synced
    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.

        args:
            grp: h5py Group or File, object to load data from.
        """
        sub_shape = grp['raw'].size
        full_shape = grp['ttheta'].size
        self.resize(sub_shape=sub_shape, full_shape=full_shape)
        utils.h5_to_attributes(self, grp, ['raw', 'pcount', 'norm', 'ttheta', 'q'])
        try:
            utils.h5_to_attributes(self, grp, ['sigma', 'sigma_raw'])
        except KeyError:
            data = self.norm.copy()
            if data[data > 0].size > 0:
                minval = data[data > 0].min()
                data[data > 0] = np.sqrt(data[data > 0]/minval) * minval
            self.sigma = data
            self.sigma_raw = self.sigma * self.pcount

    @synced
    def __iadd__(self, other):
        try:
            if isinstance(other, self.__class__):
                other.mutex.acquire()
                other.check_memory()
            if not (self.raw.shape == other.raw.shape and self.ttheta.shape == other.ttheta.shape):
                raise ValueError("Cannot add SMIntData for differently sized data")
            if not ((self.ttheta == other.ttheta).all() and (self.q == other.q).all()):
                warnings.warn(RuntimeWarning("Adding SMIntData objects with mismatched x axis"))
            self.raw = self.raw + other.raw
            self.pcount = self.pcount + other.pcount
            self.sigma_raw = self.sigma_raw + other.sigma_raw

            # out.sigma = self.sigma*self.sigma + other.sigma*other.sigma
            # out.sigma.data = np.sqrt(out.sigma.data)
            self.sigma = np.sqrt(self.sigma_raw)
            self.sigma = self.sigma / self.pcount

            self.norm = self.raw / self.pcount
        finally:
            if isinstance(other, self.__class__):
                other.mutex.release()
        return self


class SMIntData2D(SMIntData1D):
    def __init__(self, addr=None, yshape=(0,0), xshape=(0,0), no_zeros=False, **kwargs):
        sub_shape = np.product(yshape)
        full_shape = np.product(xshape)
        format_list = [
            '0'*128, # shm address
            int(0), # size
            int(0), # capacity
            int(sub_shape), # sub_shape
            int(full_shape), # full_shape
            int(yshape[0]),
            int(xshape[0]),
            int(0), # offset for ydata (NOT IMPLEMENTED SHOULD STAY 0)
            int(0), # offset for ydata (NOT IMPLEMENTED SHOULD STAY 0)
            True # is non_zero being used (NOT IMPLEMENTED SHOULD STAY FALSE)
        ]
        size = _get_size(full_shape, sub_shape)
        SMBase.__init__(self, addr=addr, format_list=format_list, size=size, **kwargs)
        with self.mutex:
            if addr is None:
                self._shl[3] = sub_shape
                self._shl[4] = full_shape
                self._shl[5] = yshape[0]
                self._shl[6] = xshape[0]
                self._shl[7] = 0
                self._shl[8] = 0
                self._shl[9] = no_zeros
            self.npview = np.ndarray(
                (self._shl[3] * 5 + self._shl[4] * 3,),
                dtype=float,
                buffer=self._shm.buf
            )
            self._set_arrays()

    def _set_arrays(self):
        super()._set_arrays()

