from collections import namedtuple
from dataclasses import dataclass, field
import copy

import numpy as np
from pyFAI import units
import h5py

from .. import _utils as utils


class nzarray1d():
    """Sparse matrix like object which stores minimal box to contain
    non-zero data. Only for 1D arrays.
    
    attributes:
        corners: tuple, edges of the region containing non-zero data
        data: numpy array, region with non-zero data. May also contain zeros.
        shape: tuple, shape of the full dataset
    
    methods:
        Reimplements all arithmetic functions (+, -, *, /, //)
        from_hdf5: Loads data from an hdf5 file
        full: returns the full dataset
        get_corners: Finds the edges of the non-zero region
        get_data: Cuts out the non-zero region
        get_shape: Gets the shape of the full dataset
        intersect: Finds the interesection between two nzarray1d
            objects
        to_hdf5: Saves the data to an hdf5 file
    """
    def __init__(self, arr=None, grp=None, lazy=False):
        """arr: numpy array, full dataset
        grp: h5py File or Group object, if used will load in data
        lazy: bool, if True the data attribute is a view of the
            h5py dataset called 'data' in grp
        """
        self.none_flag = False
        if isinstance(arr, self.__class__):
            if arr.data is None:
                self._none_array()
                self.none_flag = True
            else:
                self.data = np.empty_like(arr.data)
                self.data[()] = arr.data[()]
                self.shape = copy.deepcopy(arr.shape)
                self.corners = copy.deepcopy(arr.corners)
        elif grp is not None:
            if lazy:
                self.shape = grp['shape'][()]
                self.corners = grp['corners'][()]
                self.data = grp['data']
            else:
                self.shape = grp['shape'][()]
                self.corners = grp['corners'][()]
                self.data = grp['data'][()]
        elif arr is None:
            self.none_flag = True
            self._none_array()
        else:
            self.shape = self.get_shape(arr)
            self.corners = self.get_corners(arr)
            self.data = self.get_data(arr)
    
    def _none_array(self):
        arrn = np.array([0])
        self.shape = self.get_shape(arrn)
        self.corners = self.get_corners(arrn)
        self.data = self.get_data(arrn)
    
    def get_shape(self, arr):
        """Finds the shape of arr, enforces 1D arrays only. 
        
        args:
            arr: numpy array
        
        returns:
            shape: tuple, shape of the array
        """
        assert len(arr.shape) == 1, "Must be 1d array."
        return arr.shape
    
    def get_corners(self, arr):
        """Finds edges of non-zero region.
        
        args:
            arr: numpy array
        
        returns:
            corners: tuple, edges of the non-zero region
        """
        if (arr == 0).all():
            return [0,0]
        else:
            c = np.nonzero(arr)[0]
            return (c[0], c[-1] + 1)
    
    def get_data(self, arr):
        """Gets non-zero region of dataset.
        
        args:
            arr: numpy array
        
        returns:
            data: numpy array, non-zero region
        """
        data = arr[
            self.corners[0]:self.corners[1]
        ]
        return data
    
    def full(self):
        """Returns the full dataset.
        
        returns:
            full: numpy array, dataset with shape self.shape
        """
        if self.data is None:
            return None
        full = np.zeros(self.shape, dtype=self.data.dtype)
        full[self.corners[0]:self.corners[1]] = self.data
        return full

    def intersect(self, other):
        """Finds the intersection between two nzarrays. Returns a
        nzarray1d object with data region of a minimal size to include
        the full non-zero region from self and other.
        
        args:
            other: nzarray1d, object to compare against
        
        returns:
            out: nzarray1d, interection array
        """
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
        """Saves data to an hdf5 file.
        
        args:
            grp: h5py File or Group, where data will be saved
            compression: str, compression algorithm to use. See h5py
                docs.
        """
        grp.attrs['encoded'] = 'nzarray'
        for name in ['shape', 'corners']:
            data = getattr(self, name)
            if name in grp:
                grp[name][()] = np.array(data)[()]
            else:
                grp.create_dataset(name, data=data)
        if 'data' in grp:
            grp['data'].resize(self.data.shape)
            grp['data'][()] = self.data[()]
        else:
            grp.create_dataset(
                'data', data=self.data, compression=compression, chunks=True,
                maxshape=tuple(
                    None for x in self.data.shape
                ), dtype='float64'
            )
    
    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.
        
        args:
            grp: h5py File or Group, where to load data from.
        """
        for key in ['data', 'shape', 'corners']:
            self.__dict__[key] = np.empty_like(grp[key])
            self.__dict__[key] = grp[key][()]
        
    
    def _shift_index(self, idx, si=0):
        """Shifts index values for full dataset to query data from
        self.
        
        args:
            idx: iterable, indexes to shift
            si: int, starting index
        
        returns:
            out: list, new set of shifted indeces
        """
        out = []
        for i, val in enumerate(idx):
            j = i - i % 2 + si
            idx = self._get_idx(val, j)
            out.append(idx - self.corners[j])
        return out
    
    def _get_idx(self, x, i=0):
        """Handles negative indexing.
        
        args:
            x: int, index value
            i: int, which value in shape to use to handle negative
                indexes
        """
        if x >= 0:
            idx = x
        else:
            idx = self.shape[i] + x
        return idx
    
    def _shift_slice(self, key, i=0):
        """Shifts a slice object to allow data access without needing
        to call the full dataset.
        
        args:
            key: slice, desired slice of data
            i: int, dimension in shape to use
        
        returns:
            slice, bool: Either the original slice or shifted slice,
                depending on whether the slice is entirely contained in
                the dataset or not.
        """
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
            self._none_array()
        else:
            self.shape = self.get_shape(arr)
            self.corners = self.get_corners(arr)
            self.data = self.get_data(arr)
    
    def __add__(self, other):
        if isinstance(other, self.__class__):
            assert list(self.shape) == list(other.shape), "Cannot add arrays of different shape"
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
            assert list(self.shape) == list(other.shape), "Cannot subtract arrays of different shape"
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
            assert list(self.shape) == list(other.shape), "Cannot multiply arrays of different shape"
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
            assert list(self.shape) == list(other.shape), "Cannot divide arrays of different shape"
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
            assert list(self.shape) == list(other.shape), "Cannot divide arrays of different shape"
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
    """Sparse matrix like object which stores minimal box to contain
    non-zero data. Only for 2D arrays.
    
    attributes:
        corners: tuple, edges of the region containing non-zero data
        data: numpy array, region with non-zero data. May also contain zeros.
        shape: tuple, shape of the full dataset
    
    methods:
        Reimplements all arithmetic functions (+, -, *, /, //)
        from_hdf5: Loads data from an hdf5 file
        full: returns the full dataset
        get_corners: Finds the edges of the non-zero region
        get_data: Cuts out the non-zero region
        get_shape: Gets the shape of the full dataset
        intersect: Finds the interesection between two nzarray1d
            objects
        to_hdf5: Saves the data to an hdf5 file
    """
    def __init__(self, arr=None, grp=None, lazy=False):
        """arr: numpy array, full dataset
        grp: h5py File or Group object, if used will load in data
        lazy: bool, if True the data attribute is a view of the
            h5py dataset called 'data' in grp
        """
        super().__init__(arr, grp, lazy)
    
    def _none_array(self):
        arrn = np.array([[0],[0]])
        self.shape = self.get_shape(arrn)
        self.corners = self.get_corners(arrn)
        self.data = self.get_data(arrn)
    
    def get_shape(self, arr):
        """Finds the shape of arr, enforces 2D arrays only. 
        
        args:
            arr: numpy array
        
        returns:
            shape: tuple, shape of the array
        """
        assert len(arr.shape) == 2, 'Must be 2D array.'
        return arr.shape[:]
    
    def get_corners(self, arr):
        """Finds edges of non-zero region.
        
        args:
            arr: numpy array
        
        returns:
            corners: tuple, edges of the non-zero region
        """
        if (arr == 0).all():
            return [0,0,0,0]
        else:
            r = np.nonzero(arr)[0]
            c = np.nonzero(arr)[1]
            return (min(r), max(r) + 1, min(c), max(c) + 1)
    
    def get_data(self, arr):
        """Gets non-zero region of dataset.
        
        args:
            arr: numpy array
        
        returns:
            data: numpy array, non-zero region
        """
        data = arr[
            self.corners[0]:self.corners[1], 
            self.corners[2]:self.corners[3]
        ]
        return data
    
    def full(self):
        """Returns the full dataset.
        
        returns:
            full: numpy array, dataset with shape self.shape
        """
        if self.data is None:
            return None
        arr = np.zeros(self.shape, dtype=self.data.dtype)
        arr[
            self.corners[0]:self.corners[1], 
            self.corners[2]:self.corners[3]
        ] = self.data
        return arr
    
    def intersect(self, other):
        """Finds the intersection between two nzarrays. Returns a
        nzarray2d object with data region of a minimal size to include
        the full non-zero region from self and other.
        
        args:
            other: nzarray2d, object to compare against
        
        returns:
            out: nzarray2d, interection array
        """
        assert list(self.shape) == list(other.shape), "Can't cast nzarray of different shape"
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