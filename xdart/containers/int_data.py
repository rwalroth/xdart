from collections import namedtuple
from dataclasses import dataclass, field
import copy
import tempfile

import numpy as np
from pyFAI import units
import h5py

from .nzarrays import nzarray1d, nzarray2d
from .. import utils

class int_1d_data:
    def __init__(self, raw=None, pcount=None, norm=None, ttheta=0, q=0):
        self.raw = raw
        self.pcount = pcount
        self.norm = norm
        self.ttheta = ttheta
        self.q = q

    def from_result(self, result, wavelength):
        self.ttheta, self.q = self.parse_unit(
            result, wavelength)

        self.pcount = result._count
        self.raw = result._sum_signal
        self.norm = self.raw/self.pcount
    
    def parse_unit(self, result, wavelength):
        """Helper function to take integrator result and return a two theta
        and q array regardless of the unit used for integration.

        args:
            result: result from 1dintegrator
            wavelength: wavelength for conversion in Angstroms

        returns:
            int_1d_2theta: two theta array
            int_1d_q: q array
        """
        if wavelength is None:
            return result.radial, None

        if result.unit == units.TTH_DEG or str(result.unit) == '2th_deg':
            int_1d_2theta = result.radial
            int_1d_q = (
                (4 * np.pi / (wavelength*1e10)) *
                np.sin(np.radians(int_1d_2theta / 2))
            )
        elif result.unit == units.Q_A or str(result.unit) == 'q_A^-1':
            int_1d_q = result.radial
            int_1d_2theta = (
                2*np.degrees(
                    np.arcsin(
                        int_1d_q *
                        (wavelength * 1e10) /
                        (4 * np.pi)
                    )
                )
            )
        # TODO: implement other unit options for unit
        return int_1d_2theta, int_1d_q

    def to_hdf5(self, grp, compression=None):
        for key in ['raw', 'pcount', 'norm']:
            if key in grp:
                del grp[key]
        raw = grp.create_group('raw')
        self.raw.to_hdf5(raw, compression)
        pcount = grp.create_group('pcount')
        self.pcount.to_hdf5(pcount, compression)
        norm = grp.create_group('norm')
        self.norm.to_hdf5(norm, compression)
        utils.attributes_to_h5(self, grp, ['ttheta', 'q'], compression=compression)
    
    def from_hdf5(self, grp):
        self.raw.from_hdf5(grp['raw'])
        self.pcount.from_hdf5(grp['pcount'])
        self.norm.from_hdf5(grp['norm'])
        utils.h5_to_attributes(self, grp, ['ttheta', 'q'])
    
    def __setattr__(self, name, value):
        if name in ['raw', 'norm', 'pcount']:
            self.__dict__[name] = nzarray1d(value)
        else:
            super().__setattr__(name, value)
    
    def __add__(self, other):
        out = self.__class__()
        out.raw = self.raw + other.raw
        out.pcount = self.pcount + other.pcount
        out.norm = out.raw/out.pcount
        out.ttheta = copy.deepcopy(self.ttheta)
        out.q = copy.deepcopy(self.q)
        return out

class int_2d_data(int_1d_data):
    def __init__(self,  raw=None, pcount=None, norm=None, ttheta=0, q=0,
                 chi=0):
        self.raw = raw
        self.pcount = pcount
        self.norm = norm
        self.ttheta = ttheta
        self.q = q
        self.chi = chi

    def from_result(self, result, wavelength):
        super(int_2d_data, self).from_result(result, wavelength)
        self.chi = result.azimuthal
    
    def from_hdf5(self, grp):
        super().from_hdf5(grp)
        utils.h5_to_attributes(self, grp, ['chi'])
    
    def to_hdf5(self, grp, compression=None):
        super().to_hdf5(grp, compression)
        utils.attributes_to_h5(self, grp, ['chi'], compression=compression)
    
    def __setattr__(self, name, value):
        if name in ['raw', 'norm', 'pcount']:
            self.__dict__[name] = nzarray2d(value)
        else:
            super().__setattr__(name, value)