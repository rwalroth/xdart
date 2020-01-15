from collections import namedtuple
from dataclasses import dataclass, field
import copy

import numpy as np
from pyFAI import units
import h5py

from .. import utils


class nzarray1d():
    def __init__(self, arr=None):
        if isinstance(arr, self.__class__):
            self.data = copy.deepcopy(arr.data)
            self.shape = copy.deepcopy(arr.shape)
            self.corners = copy.deepcopy(arr.corners)
        elif arr is None:
            self.data = None
            self.shape = None
            self.corners = None
        else:
            self.shape = self.get_shape(arr)
            self.corners = self.get_corners(arr)
            self.data = self.get_data(arr)
    
    def get_shape(self, arr):
        assert len(arr.shape) == 1, "Must be 1d array."
        return arr.shape
    
    def get_corners(self, arr):
        if (arr == 0).all():
            return [0,0]
        else:
            c = np.nonzero(arr)[0]
            return (c[0], c[-1] + 1)
    
    def get_data(self, arr):
        data = arr[
            self.corners[0]:self.corners[1]
        ]
        return data
    
    def full(self):
        if self.data is None:
            return None
        full = np.zeros(self.shape, dtype=self.data.dtype)
        full[self.corners[0]:self.corners[1]] = self.data
        return full

    def intersect(self, other):
        assert \
            self.shape == other.shape, \
            "Can't cast nzarray of different shape"
        out = nzarray1d()
        
        out.shape = self.shape[:]
        out.corners = [min(self.corners[0], other.corners[0]),
                    max(self.corners[1], other.corners[1])]
        out.data = np.zeros((out.corners[1] - out.corners[0],))

        other_data = np.zeros_like(out.data)
        
        i0, i1 = out._shift_index(self.corners)
        out.data[i0:i1] = self.data
        
        i0, i1 = out._shift_index(other.corners)
        other_data[i0:i1] = other.data
        
        return out, other_data
    
    def to_hdf5(self, grp, compression=None):
        utils.attributes_to_h5(
            self, grp, lst_attr=['data', 'shape', 'corners'], 
            compression=compression
        )
    
    def from_hdf5(self, grp):
        utils.h5_to_attributes(
            self, grp, lst_attr=['data', 'shape', 'corners']
        )
        
    
    def _shift_index(self, idx, si=0):
        out = []
        for i, val in enumerate(idx):
            j = i - i % 2 + si
            idx = self._get_idx(val, j)
            out.append(idx - self.corners[j])
        return out
    
    def _get_idx(self, x, i=0):
        if x >= 0:
            idx = x
        else:
            idx = self.shape[i] + x
        return idx
    
    def _shift_slice(self, key, i=0):
        if key.start is None or key.stop is None:
            return key, True
        elif (self._get_idx(key.start, i) >= self.corners[0] and 
              self._get_idx(key.stop, i) <= self.corners[1]):
            start, stop = self._shift_index([key.start, key.stop], i)
            return slice(start, stop, key.step), False
        else:
            return key, True
    
    def __getitem__(self, key):
        if isinstance(key, slice):
            skey, full = self._shift_slice(key)
            if full:
                return self.full()[skey]
            else:
                return self.data[skey]
        elif type(key) == int:
            idx = self._get_idx(key)
            if self.corners[0] <= idx < self.corners[1]:
                return self.data[idx - self.corners[0]]
            else:
                return 0
        else:
            return self.full()[key]
    
    def __set__(self, obj, arr):
        if isinstance(arr, self.__class__):
            self.data = arr.data
            self.shape = arr.shape
            self.corners = arr.corners
        elif arr is None:
            self.data = None
            self.shape = None
            self.corners = None
        else:
            self.shape = self.get_shape(arr)
            self.corners = self.get_corners(arr)
            self.data = self.get_data(arr)
    
    def __add__(self, other):
        if isinstance(other, self.__class__):
            assert self.shape == other.shape, "Cannot add arrays of different shape"
            if other.data.size > 0 and self.data.size > 0:
                out, temp = self.intersect(other)
                out.data += temp
            elif other.data.size > 0:
                out = self.__class__(other)
            else:
                out = self.__class__(self)
        elif np.isscalar(other) or type(other) == np.ndarray:
            out = self.__class__(self.full() + other)
        else:
            raise TypeError(f"Cannot add object of type {type(other)}")
        return out
    
    def __sub__(self, other):
        if isinstance(other, self.__class__):
            assert self.shape == other.shape, "Cannot subtract arrays of different shape"
            if other.data.size > 0 and self.data.size > 0:
                out, temp = self.intersect(other)
                out.data -= temp
            elif other.data.size > 0:
                out = self.__class__(other * -1)
            else:
                out = self.__class__(self)
        elif np.isscalar(other) or type(other) == np.ndarray:
            out = self.__class__(self.full() - other)
        return out
    
    def __mul__(self, other):
        if isinstance(other, self.__class__):
            assert self.shape == other.shape, "Cannot multiply arrays of different shape"
            out, temp = self.intersect(other)
            out.data *= temp
            if other.data.size > 0 and self.data.size > 0:
                out, temp = self.intersect(other)
                out.data *= temp
            elif other.data.size > 0:
                out = self.__class__(self)
            else:
                out = self.__class__(other)
        elif np.isscalar(other):
            if other == 0:
                out = self.__class__(np.zeros(self.shape))
            else:
                out = self.__class__(self)
                out.data *= other
        elif type(other) == np.ndarray:
            out = self.__class__(self.full() * other)
        return out
    
    def __div__(self, other):
        return self.__truediv__(other)
    
    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            assert self.shape == other.shape, "Cannot divide arrays of different shape"
            out, temp = self.intersect(other)
            out.data *= temp
            if other.data.size > 0 and self.data.size > 0:
                out, temp = self.intersect(other)
                out.data = utils.div0(out.data, temp)
            elif other.data.size > 0:
                out = self.__class__(self)
            else:
                out = self.__class__(other)
        elif np.isscalar(other):
            if other == 0:
                out = self.__class__(np.zeros(self.shape))
            else:
                out = self.__class__(self)
                out.data = utils.div0(out.data, other)
        elif type(other) == np.ndarray:
            out = self.__class__(utils.div0(self.full(), other))
        return out
    
    def __floordiv__(self, other):
        if isinstance(other, self.__class__):
            assert self.shape == other.shape, "Cannot divide arrays of different shape"
            out, temp = self.intersect(other)
            out.data *= temp
            if other.data.size > 0 and self.data.size > 0:
                out, temp = self.intersect(other)
                out.data = utils.div0(out.data, temp).astype(int)
            elif other.data.size > 0:
                out = self.__class__(self)
            else:
                out = self.__class__(other)
        elif np.isscalar(other):
            if other == 0:
                out = self.__class__(np.zeros(self.shape))
            else:
                out = self.__class__(self)
                out.data = utils.div0(out.data, other).astype(int)
        elif type(other) == np.ndarray:
            out = self.__class__(utils.div0(self.full(), other).astype(int))
        return out


class nzarray2d(nzarray1d):
    def __init__(self, arr=None):
        super().__init__(arr)
    
    def get_shape(self, arr):
        assert len(arr.shape) == 2, 'Must be 2D array.'
        return arr.shape[:]
    
    def get_corners(self, arr):
        if (arr == 0).all():
            return [0,0,0,0]
        else:
            r = np.nonzero(arr)[0]
            c = np.nonzero(arr)[1]
            return (min(r), max(r) + 1, min(c), max(c) + 1)
    
    def get_data(self, arr):
        data = arr[
            self.corners[0]:self.corners[1], 
            self.corners[2]:self.corners[3]
        ]
        return data
    
    def full(self):
        if self.data is None:
            return None
        arr = np.zeros(self.shape, dtype=self.data.dtype)
        arr[
            self.corners[0]:self.corners[1], 
            self.corners[2]:self.corners[3]
        ] = self.data
        return arr
    
    def intersect(self, other):
        if np.isscalar(other):
            out = nzarray2d(self.full())
            other_data = other
        assert self.shape == other.shape, "Can't divide nzarray of different shape"
        out = nzarray2d()
        
        out.shape = self.shape[:]
        out.corners = [min(self.corners[0], other.corners[0]),
                       max(self.corners[1], other.corners[1]),
                       min(self.corners[2], other.corners[2]),
                       max(self.corners[3], other.corners[3])]
        
        out.data = np.zeros((out.corners[1] - out.corners[0],
                         out.corners[3] - out.corners[2]))
        
        other_data = np.zeros_like(out.data)
        
        r0, r1, c0, c1 = out._shift_index(self.corners)
        
        out.data[r0:r1,c0:c1] = self.data
        
        r0, r1, c0, c1 = out._shift_index(other.corners)
        
        other_data[r0:r1,c0:c1] = other.data
        
        return out, other_data
    
    def __getitem__(self, key):
        if type(key) == tuple:
            slc = []
            full = []
            for i, val in enumerate(key):
                if isinstance(val, slice):
                    f, s = self._shift_slice(val, i)
                    slc.append(s)
                    full.append(f)
                elif type(key) == int:
                    idx = self._get_idx(val, i)
                    if self.corners[i*2] <= idx < self.corners[i*2 + 1]:
                        slc.append(idx - self.corners[i*2])
                        full.append(False)
                    else:
                        slc.append(val)
                        full.append(True)
                else:
                    slc.append(val)
                    full.append(True)
            if any(full):
                return self.full()[key]
            else:
                return self.data[tuple(slc)]
        else:
            return self.full()[key]