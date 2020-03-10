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

## This module imports
from .arch import EwaldArch

class ArchSeries():
    def __init__(self, data_file, file_lock, arches=[]):
        self.data_file = data_file
        self.file_lock = file_lock
        self.index = []
        if arches:
            for a in arches:
                self.__setitem__(a.idx, a)
        self._i = 0
        with self.file_lock:
            with catch(self.data_file, 'a') as f:
                if 'arches' not in f:
                    f.create_group('arches')
                
    
    def __getitem__(self, idx):
        if idx in self.index:
            arch = EwaldArch(idx)
            with self.file_lock:
                with catch(self.data_file, 'r') as f:
                    arch.load_from_h5(f['arches'])
            return arch
        else:
            raise KeyError(f"Arch not found with {idx} index")
    
    def iloc(self, idx):
        return self.__getitem__(self.index[idx])
    
    def __setitem__(self, idx, arch):
        with self.file_lock:
            with catch(self.data_file, 'a') as f:
                if 'arches' not in f:
                    f.create_group('arches')
                if idx != arch.idx:
                    arch.idx = idx
                arch.save_to_h5(f['arches'])
                if arch.idx not in self.index:
                    self.index.append(arch.idx)
    
    def append(self, arch):
        arches = ArchSeries(self.data_file, self.file_lock)
        arches.index = self.index[:]
        if isinstance(arch, Series):
            _arch = arch.iloc[0]
        else:
            _arch = arch
        arches.__setitem__(_arch.idx, _arch)
        return arches
    
    def sort_index(self, inplace=False):
        if inplace:
            self.index.sort()
        else:
            arches = ArchSeries(self.data_file, self.file_lock)
            arches.index = self.index[:]
            arches.index.sort()
            return arches
    
    def __next__(self):
        if self._i < len(self.index):
            arch = self.iloc(self._i)
            self._i += 1
            return arch
        else:
            raise StopIteration
    
    def __iter__(self):
        self._i = 0
        return self
                