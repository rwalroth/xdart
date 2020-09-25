# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports
from pandas import Series

# Qt imports

# xdart imports
from xdart.utils import catch_h5py_file as catch

# This module imports
from .arch import EwaldArch


class ArchSeries():
    """Container for storing EwaldArch objects. Data is stored in an
    hdf5 file, rather than in memory. __getitem__ and __setitem__ have
    been overridden to write the information to a file, whose path is
    stored as an attribute.
    
    attributes:
        data_file: Path where hdf5 file is stored.
        file_lock: Thread safe lock which ensures only one thread
                   accesses data at a time.
        index: List of all arch id numbers.
    
    methods:
        append: Add a new arch at the end of the index.
        iloc: Retrieve an arch by its absolute location not its id.
        sort_index: Sort the index by arch id.
    """
    def __init__(self, data_file, file_lock, arches=[],
                 static=False, gi=False):
        """data_file: Path to hdf5 file for storing data.
        file_lock: Thread safe lock.
        arches: List of arches to initialize series with.
        """
        self.data_file = data_file
        self.file_lock = file_lock
        self.index = []
        self.static = static
        self.gi = gi
        if arches:
            for a in arches:
                self.__setitem__(a.idx, a)
        self._i = 0
        # invoke the lock to prevent conflicts
        with self.file_lock:
            # use catch to avoid oserrors which will resolve with time.
            with catch(self.data_file, 'a') as f:
                if 'arches' not in f:
                    f.create_group('arches')
                
    
    def __getitem__(self, idx):
        """Initializes a new EwaldArch object and loads data from file
        into it.
        """
        if idx in self.index:

            arch = EwaldArch(idx, static=self.static, gi=self.gi)
            # invoke the lock to prevent conflicts
            with self.file_lock:
                # use catch to avoid oserrors which will resolve with time.
                with catch(self.data_file, 'r') as f:
                    arch.load_from_h5(f['arches'])
            return arch
        else:
            raise KeyError(f"Arch not found with {idx} index")
    
    def iloc(self, idx):
        """Location based retrieval of arches instead of id based.
        Similar to .iloc in pandas Series but called by .iloc(i) not
        .iloc[i].
        """
        return self.__getitem__(self.index[idx])
    
    def __setitem__(self, idx, arch):
        """Sets the arch at location idx to be the new arch. If an arch
        is stored with the same idx, replaces the data with the new
        data.
        """
        # invoke the lock to prevent conflicts
        with self.file_lock:
            # use catch to avoid oserrors which will resolve with time.
            with catch(self.data_file, 'a') as f:
                if 'arches' not in f:
                    f.create_group('arches')
                if idx != arch.idx:
                    arch.idx = idx
                arch.save_to_h5(f['arches'])
                if arch.idx not in self.index:
                    self.index.append(arch.idx)
    
    def append(self, arch):
        """Adds a new arch to the end of the index, unless idx is
        already stored in which case the arch at that idx is replaced.
        """
        arches = ArchSeries(self.data_file, self.file_lock)
        arches.index = self.index[:]
        if isinstance(arch, Series):
            _arch = arch.iloc[0]
        else:
            _arch = arch
        arches.__setitem__(_arch.idx, _arch)
        return arches
    
    def sort_index(self, inplace=False):
        """Sorts the index by idx. If inplace is true, returns nothing.
        Else, returns a copy with the index sorted.
        """
        if inplace:
            self.index.sort()
        else:
            arches = ArchSeries(self.data_file, self.file_lock)
            arches.index = self.index[:]
            arches.index.sort()
            return arches
    
    def __next__(self):
        """Allows for iteration.
        """
        if self._i < len(self.index):
            arch = self.iloc(self._i)
            self._i += 1
            return arch
        else:
            raise StopIteration
    
    def __iter__(self):
        """Allows for iteration.
        """
        self._i = 0
        return self
                