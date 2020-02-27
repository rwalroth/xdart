from collections import namedtuple
from dataclasses import dataclass, field
import copy

import numpy as np
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


