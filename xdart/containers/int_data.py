from collections import namedtuple
from dataclasses import dataclass, field
import copy
import tempfile

import numpy as np
from pyFAI import units
import h5py

from .nzarrays import nzarray1d, nzarray2d
from .. import utils

class int_1d_data():
    def __init__(self, grp=None, raw=None, pcount=None, norm=None, ttheta=None,
                  q=None, compression='lzf'):
        """Creates data object which interfaces to an hdf5 object. If
        grp is None, creates a virtual object and loads in provided
        data. If grp is empty, it loads in provided data. 
        Otherwise will not load other data!
        """
        self.compression = compression
        if grp is None:
            self._file = tempfile.TemporaryFile()
            self._h5py = h5py.File(self._file, mode='a')
            self._grp = self._h5py.create_group('int_1d')
        else:
            self._file = None
            self._h5py = None
            self._grp = grp
        if self._grp.attrs.get('encoded', 'not_found') == 'int_data':
            self.from_hdf5()
        else:
            self.raw = raw
            self.pcount = pcount
            self.norm = norm
            self.ttheta = ttheta
            self.q = q
            self._grp.attrs['encoded'] = 'int_data'

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
    
    def from_hdf5(self):
        for key in ['raw', 'pcount', 'norm']:
            if key in self._grp:
                self._setnzarray(key, nzarray1d(grp=self._grp[key]))
            else:
                self._setnzarray(key, nzarray1d())
        
        for key in ['ttheta', 'q']:
            if key in self._grp:
                self._setarray(key, self._grp[key][()])
            else:
                self._setarray(key, None)
    
    def __setattr__(self, name, value):
        if name in ['raw', 'norm', 'pcount']:
            self._setnzarray(name, value)
        elif name in ['ttheta', 'q']:
            self._setarray(name, value)
        else:
            super().__setattr__(name, value)
    
    def _setnzarray(self, name, value):
        valuenz = nzarray1d(value)
        if name not in self._grp:
            grp = self._grp.create_group(name)
        else:
            grp = self._grp[name]
        valuenz.to_hdf5(grp, compression=self.compression)
        self.__dict__[name] = nzarray1d(grp=grp, lazy=True)
    
    def _setarray(self, name, value):
        if value is None:
            arr = np.array([0])
        else:
            arr = value
        if name not in self._grp:
            self._grp.create_dataset(name, data=arr, chunks=True,
                                     compression=self.compression,
                                     maxshape=(None,), dtype='float64')
        else:
            self._grp[name].resize(arr.shape)
            self._grp[name][()] = arr[()]
        self.__dict__[name] = self._grp[name]
        
    
    def __add__(self, other):
        out = self.__class__(None)
        out.raw = self.raw + other.raw
        out.pcount = self.pcount + other.pcount
        out.norm = out.raw/out.pcount
        out.ttheta = self.ttheta[()]
        out.q = self.q[()]
        return out
        
    
    def __iadd__(self, other):
        self.raw = self.raw + other.raw
        self.pcount = self.pcount + other.pcount
        self.norm = self.raw/self.pcount
        return self

class int_2d_data(int_1d_data):
    def __init__(self, grp=None, raw=None, pcount=None, norm=None, ttheta=None,
                  q=None, chi=None, compression='lzf'):
        super().__init__(grp, raw, pcount, norm, ttheta, q, compression)
        if 'chi' not in self.__dict__:
            self.chi = chi
        

    def from_result(self, result, wavelength):
        super(int_2d_data, self).from_result(result, wavelength)
        self.chi = result.azimuthal
    
    def from_hdf5(self):
        for key in ['raw', 'pcount', 'norm']:
            if key in self._grp:
                self._setnzarray(key, nzarray2d(grp=self._grp[key]))
            else:
                self._setnzarray(key, nzarray2d())
        
        for key in ['ttheta', 'q', 'chi']:
            if key in self._grp:
                self._setarray(key, self._grp[key][()])
            else:
                self._setarray(key, None)
    
    def __setattr__(self, name, value):
        if name in ['raw', 'norm', 'pcount']:
            self._setnzarray(name, value)
        elif name in ['ttheta', 'q', 'chi']:
            self._setarray(name, value)
        else:
            super().__setattr__(name, value)
    
    def _setnzarray(self, name, value):
        valuenz = nzarray2d(value)
        if name not in self._grp:
            grp = self._grp.create_group(name)
        else:
            grp = self._grp[name]
        valuenz.to_hdf5(grp, compression=self.compression)
        self.__dict__[name] = nzarray2d(grp=grp, lazy=True)
    
    # def _setarray(self, name, value):
    #     if value is None:
    #         arr = np.array([[0],[0]])
    #     else:
    #         arr = value
    #     if name not in self._grp:
    #         self._grp.create_dataset(name, data=arr, chunks=True,
    #                                  compression=self.compression,
    #                                  maxshape=(None,None))
    #     else:
    #         print(name)
    #         print(arr.shape)
    #         print(self._grp[name].shape)
    #         self._grp[name].resize(arr.shape)
    #         self._grp[name][()] = arr[()]
    #     self.__dict__[name] = self._grp[name]
    
    def __add__(self, other):
        out = super().__add__(other)
        out.chi = self.chi[()]
        return out