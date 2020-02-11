# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from threading import Condition

# Other imports

# Qt imports

# This module imports
from xdart.classes.ewald import EwaldArch


class Arches():
    def __init__(self, grp, compression='lzf'):
        self._grp = grp
        self.index = []
        self.arch_lock = Condition()
        self._i = 0
        self.compression = 'lzf'
        for key in grp.keys():
            if 'type' in grp[key].attrs:
                if grp[key].attrs['type'] == 'EwaldArch':
                        self.index.append(int(key))
        
    
    def __getitem__(self, index):
        arc = EwaldArch(index)
        arc.load_from_h5(self._grp)
    
    def __setitem__(self, index, value):
        self.index.append(value.idx)
        value.save_to_h5(self._grp, self.compression)
    
    def __next__(self):
        if self._i < len(self.index):
            arc = self.__getitem__(self._i)
            self._i += 1
            return arc
        else:
            raise StopIteration
    
    def __iter__(self):
        self._i = 0
        return self
    
    def sort_index(self):
        self.index.sort()
    
    def iloc(self, idx):
        return self.__getitem__(self.index[idx])