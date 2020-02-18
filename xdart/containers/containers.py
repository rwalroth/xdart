from collections import namedtuple
from dataclasses import dataclass, field
import copy
import tempfile

import numpy as np
import pandas as pd
from pyFAI import units
import h5py

from .nzarrays import nzarray1d, nzarray2d
from .. import utils


class NoZeroArray():
    def __get__(self, instance, owner):
        if self.data is None:
            return None
        else:
            arr = np.zeros(self.shape)
            arr[
                self.corners[0]:self.corners[1], 
                self.corners[2]:self.corners[3]
            ] = self.data
            return arr[()]
    
    def __set__(self, instance, value):
        if value is None:
            self.shape = None
            self.corners = None
            self.data = None
        else:
            self.shape = value.shape
            r = np.nonzero(np.sum(value, axis=0))[0]
            c = np.nonzero(np.sum(value, axis=1))[0]
            self.corners = (r[0], r[-1], c[0], c[-1])
            self.data = value[r[0]:r[-1], c[0]:c[-1]]


class h5dict():
    def __init__(self, grp, dict={}):
        self.keys = set()
        if grp is None:
            self._file = tempfile.TemporaryFile()
            self._hfile = h5py.File(self._file, 'a')
            self._grp = self._hfile.create_group('null')
        else:
            self._grp = grp
        for key in self._grp:
            self.keys.add(key)
        for key, val in dict.items():
            if key not in self.keys:
                utils.data_to_h5(val, self._grp, key)
                self.keys.add(key)
                
