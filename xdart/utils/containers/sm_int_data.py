import copy
import warnings

import h5py
import numpy as np

from ..datashare import SMBase, synced, locked
from ..datashare.smarray import bytes_to_shape, shape_to_bytes
from .. import _utils as utils
from .int_data import parse_unit, int_1d_data


def _get_size(length) -> int:
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
            '0'*128,  # 0 shm address
            int(0),   # 1 size
            int(0),   # 2 capacity
            int(0),   # 3 sub_length
            int(0),   # 4 full_length
            int(0),   # 5 offset for sub data (NOT IMPLEMENTED SHOULD STAY 0)
            True      # 6 is non_zero being used (NOT IMPLEMENTED SHOULD STAY FALSE)
        ]
        size = _get_size(np.product(sub_shape) * 5 + np.product(full_shape) * 2)
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

    def _set_arrays(self, arr=None, sub_length=0, full_length=0):
        for i, attr in enumerate(['raw', 'pcount', 'norm', 'sigma', 'sigma_raw']):
            start_idx = i*self._shl[3]
            super(SMBase, self).__setattr__(
                attr,
                self.npview[start_idx:start_idx + self._shl[3]]
            )
            if arr is not None:
                self.npview[start_idx:start_idx + sub_length] = \
                    arr[i*sub_length:(i + 1)*sub_length]
        for i, attr in enumerate(['ttheta', 'q']):
            start_idx = 5 * self._shl[3] + i * self._shl[4]
            super(SMBase, self).__setattr__(
                attr,
                self.npview[start_idx:start_idx + self._shl[4]]
            )
            if arr is not None:
                start_idx_2 = 5 * sub_length + i * full_length
                self.npview[start_idx:start_idx + full_length] = \
                    arr[start_idx_2:start_idx_2 + full_length]

    def __setattr__(self, name, value):
        # TODO: implement no zero option
        if name == "pcount":
            offset, shape = self._get_offset(value)
            if shape != self.__dict__[name].shape:
                self.resize(sub_shape=shape[0], full_shape=value.shape[0])
            self._shl[5] = int(offset)
            self.__dict__[name][:shape[0]] = value[offset:offset + shape[0]]
        elif name in ['raw', 'norm', 'sigma', 'sigma_raw']:
            offset = self._shl[5]
            shape = self._shl[3]
            if shape == value.shape[0]:
                self.__dict__[name][:] = value[:]
            else:
                self.__dict__[name][:shape] = value[offset:offset + shape]
        elif name in ['ttheta', 'q']:
            if value.shape != self.__dict__[name].shape:
                self.resize(full_shape=value.shape[0])
            self.__dict__[name][:] = value[:]
        else:
            super(SMBase, self).__setattr__(name, value)

    def _get_offset(self, value):
        if self._shl[6]:
            _nonzero = np.nonzero(value)[0]
            offset = _nonzero[0]
            shape = (_nonzero[-1] - offset + 1,)
        else:
            offset = 0
            shape = value.shape
        return offset, shape

    @synced
    def resize(self, sub_shape=(None,), full_shape=(None,)):
        if sub_shape[0] is None:
            _sub_shape = self._shl[3]
        else:
            _sub_shape = sub_shape[0]
        if full_shape[0] is None:
            _full_shape = self._shl[4]
        else:
            _full_shape = full_shape[0]
        length = _full_shape*2 + _sub_shape*5
        if length != len(self.npview):
            size = _get_size(length)
            data_copy = self.npview.copy()
            self._recap(size)
            old_shape = (self._shl[3], self._shl[4])
            self._shl[3] = int(_sub_shape)
            self._shl[4] = int(_full_shape)
            self.npview = np.ndarray(
                (self._shl[3] * 5 + self._shl[4] * 2,),
                dtype=float,
                buffer=self._shm.buf
            )
            self._set_arrays(data_copy, *old_shape)

    @synced
    def from_result(self, result, wavelength, monitor=1):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.

        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        full_length = result._count.shape
        offset, sub_length = self._get_offset(result._count)
        self.resize(sub_length, full_length)

        self.ttheta, self.q = parse_unit(
            result, wavelength)

        self.pcount = result._count
        self.raw = utils.div0(result._sum_signal, monitor)
        self.norm = utils.div0(self.raw, self.pcount)
        if result.sigma is None:
            self.sigma = result._sum_signal
            self.sigma = np.sqrt(self.sigma)
            self.sigma = utils.div0(self.sigma, (self.pcount * monitor))
            self.sigma_raw = utils.div0(result._sum_signal, (monitor ** 2))
        else:
            self.sigma = utils.div0(result.sigma, monitor)
            self.sigma_raw = utils.div0(((result._count * result.sigma) ** 2), (monitor ** 2))

    @synced
    def to_hdf5(self, grp: h5py.Group, compression=None):
        """Saves data to hdf5 file.

        args:
            grp: h5py Group or File, where the data will be saved
            compression: str, compression algorithm to use. See h5py
                documentation.
        """
        grp.attrs["encoded"] = "SMIntData1D"
        grp.attrs["sub_shape_r"] = int(self._shl[3])
        grp.attrs["full_shape_r"] = int(self._shl[4])
        grp.attrs["offset_r"] = int(self._shl[5])
        grp.attrs["no_zeros"] = int(self._shl[6])
        utils.attributes_to_h5(self, grp, ['raw', 'norm', 'pcount', 'sigma', 'sigma_raw', 'ttheta', 'q'],
                               compression=compression)

    @synced
    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.

        args:
            grp: h5py Group or File, object to load data from.
        """
        self._shl[6] = bool(grp.attrs["no_zeros"])
        offset = grp.attrs["offset_r"]
        sub_shape = grp.attrs["sub_shape_r"]
        full_shape = grp.attrs["full_shape_r"]
        self.resize(sub_shape=(sub_shape,), full_shape=(full_shape,))
        self._shl[5] = int(offset)
        for i, attr in enumerate(['raw', 'pcount', 'norm']):
            start_idx = i*self._shl[3]
            self.npview[start_idx:start_idx + self._shl[3]] = grp[attr][:]
        for i, attr in enumerate(['ttheta', 'q']):
            start_idx = 5 * self._shl[3] + i * self._shl[4]
            self.npview[start_idx:start_idx + self._shl[4]] = grp[attr][:]
        try:
            utils.h5_to_attributes(self, grp, ['sigma', 'sigma_raw'])
        except KeyError:
            data = self.norm.copy()
            if data[data > 0].size > 0:
                minval = data[data > 0].min()
                data[data > 0] = np.sqrt(data[data > 0]/minval) * minval
            self.sigma = data
            self.sigma_raw = self.sigma * self.pcount

    def _get_full(self, arr, key):
        arr[self._shl[5]:self._shl[5] + self._shl[3]] = getattr(self, key)[()]

    @synced
    def full(self, key):
        arr = np.zeros(self._shl[4])
        self._get_full(arr, key)
        return arr

    @synced
    def __iadd__(self, other):
        if self.ttheta.shape != other.ttheta.shape:
            raise ValueError("Cannot add SMIntData for differently sized data")
        try:
            if isinstance(other, self.__class__):
                other.mutex.acquire()
                other.check_memory()
            if not ((self.ttheta == other.ttheta).all() and (self.q == other.q).all()):
                warnings.warn(RuntimeWarning("Adding SMIntData objects with mismatched x axis"))

            self_arrs = {}
            other_arrs = {}
            for key in ("pcount", "raw", "sigma_raw"):
                self_arrs[key] = self.full(key)
                if isinstance(other, self.__class__):
                    other_arrs[key] = other.full(key)
                elif isinstance(other, int_1d_data):
                    other_arrs[key] = getattr(other, key).full()
                else:
                    other_arrs[key] = getattr(other, key)

            for key in ("pcount", "raw", "sigma_raw"):
                self.__setattr__(key, self_arrs[key] + other_arrs[key])

            # out.sigma = self.sigma*self.sigma + other.sigma*other.sigma
            # out.sigma.data = np.sqrt(out.sigma.data)
            self.sigma = np.sqrt(self.sigma_raw)
            self.sigma = utils.div0(self.sigma, self.pcount)

            self.norm = utils.div0(self.raw, self.pcount)
        finally:
            if isinstance(other, self.__class__):
                other.mutex.release()
        return self


class SMIntData2D(SMIntData1D):
    def __init__(self, addr=None, yshape=(0,0), xshape=(0,0), no_zeros=False, **kwargs):
        sub_shape = np.product(yshape)
        full_shape = np.product(xshape)
        format_list = [
            '0'*128,  # 0 shm address
            int(0),   # 1 size
            int(0),   # 2 capacity
            int(0),   # 3 sub_length_r
            int(0),   # 4 full_length_r
            int(0),   # 5 offset for sub data
            True,     # 6 is non_zero being used
            int(0),   # 7 sub_length_a
            int(0),   # 8 full_length_a
            int(0),   # 9 offset for azimuthal axis
        ]
        size = _get_size(full_shape, sub_shape)
        SMBase.__init__(self, addr=addr, format_list=format_list, size=size, **kwargs)
        with self.mutex:
            if addr is None:
                self._shl[3] = sub_shape
                self._shl[4] = full_shape
                self._shl[5] = 0
                self._shl[6] = no_zeros
                self._shl[7] = 0
                self._shl[8] = 0
                self._shl[9] = 0
            self.npview = np.ndarray(
                (self._shl[3] * 5 + self._shl[4] * 3,),
                dtype=float,
                buffer=self._shm.buf
            )
            self._set_arrays()

    def _set_arrays(self, arr=None, sub_shape=(0, 0), full_shape=(0, 0)):
        _length = self._shl[3] * self._shl[7]
        _shape = (self._shl[3], self._shl[7])
        sub_length = np.product(sub_shape)
        full_length = np.product(full_shape)
        for i, attr in enumerate(['raw', 'pcount', 'norm', 'sigma', 'sigma_raw']):
            start_idx = i*_length
            super(SMBase, self).__setattr__(
                attr,
                self.npview[start_idx:start_idx + _length].reshape(_shape)
            )
            if arr is not None:
                self.npview[start_idx:start_idx + sub_length] = \
                    arr[i*sub_length:(i + 1)*sub_length]
        for i, attr in enumerate(['ttheta', 'q']):
            start_idx = 5 * _length + i * self._shl[4]
            super(SMBase, self).__setattr__(
                attr,
                self.npview[start_idx:start_idx + self._shl[4]]
            )
            if arr is not None:
                start_idx_2 = 5 * sub_length + i * full_shape[0]
                self.npview[start_idx:start_idx + full_shape[0]] = \
                    arr[start_idx_2:start_idx_2 + full_shape[0]]

        start_idx = 5 * _length + 2 * self._shl[4]
        super(SMBase, self).__setattr__(
            "chi",
            self.npview[start_idx:start_idx + self._shl[8]]
        )
        if arr is not None:
            start_idx_2 = 5 * sub_length + 2 * full_length[0]
            self.npview[start_idx:start_idx + full_length[1]] = \
                arr[start_idx_2:start_idx_2 + full_length[1]]

    def __setattr__(self, name, value):
        if name == "pcount":
            offset, shape = self._get_offset(value)
            if shape != self.__dict__[name].shape:
                self.resize(sub_shape=shape, full_shape=value.shape)
            self._shl[5] = int(offset[0])
            self._shl[9] = int(offset[1])
            self.__dict__[name][:shape[0], :shape[1]] = \
                value[offset[0]:offset[0] + shape[0], offset[1]:offset[1] + shape[1]]
        elif name in ['raw', 'norm', 'sigma', 'sigma_raw']:
            offset = (self._shl[5], self._shl[9])
            shape = (self._shl[3], self._shl[5])
            if shape == value.shape[0]:
                self.__dict__[name][:] = value[:]
            else:
                self.__dict__[name][:shape] = value[offset:offset + shape]
        elif name in ['ttheta', 'q', 'chi']:
            if value.shape != self.__dict__[name].shape:
                self.resize(full_shape=(value.shape[0], None))
            self.__dict__[name][:] = value[:]
        elif name == 'chi':
            if value.shape != self.__dict__[name].shape:
                self.resize(full_shape=(None, value.shape[0]))
            self.__dict__[name][:] = value[:]
        else:
            super(SMBase, self).__setattr__(name, value)

    def _get_offset(self, value):
        if self._shl[6]:
            _nonzero = np.nonzero(value)
            offset = (_nonzero[0][0], _nonzero[1][0])
            shape = (_nonzero[0][-1] - offset[0] + 1,
                     _nonzero[1][-1] - offset[1] + 1)
        else:
            offset = (0,0)
            shape = value.shape
        return offset, shape

    @synced
    def resize(self, sub_shape=(None, None), full_shape=(None, None)):
        _subR, _subA = sub_shape
        _fullR, _fullA = full_shape
        if _subR is None:
            _subR = self._shl[3]
        if _subA is None:
            _subA = self._shl[7]
        if _fullR is None:
            _fullR = self._shl[4]
        if _fullA is None:
            _fullA = self._shl[8]
        length = (_fullR * 2) + _fullA + (_subR * _subA * 5)
        if length != len(self.npview):
            size = _get_size(length)
            data_copy = self.npview.copy()
            self._recap(size)
            old_shape = ((self._shl[3], self._shl[7]), (self._shl[4], self._shl[8]))
            self._shl[3] = int(_subR)
            self._shl[4] = int(_fullR)
            self._shl[7] = int(_subA)
            self._shl[8] = int(_fullA)
            self.npview = np.ndarray(
                (self._shl[3] * self._shl[7] * 5 + self._shl[4] * 2 + self._shl[8],),
                dtype=float,
                buffer=self._shm.buf
            )
            self._set_arrays(data_copy, *old_shape)

    @synced
    def from_result(self, result, wavelength, monitor=1):
        super(SMIntData2D, self).from_result(result, wavelength, monitor)
        self.chi = result.azimuthal
