from collections import namedtuple
from dataclasses import dataclass, field
import copy
import tempfile

import numpy as np
from pyFAI import units
import h5py

from .nzarrays import nzarray1d, nzarray2d
from .. import _utils as utils


def parse_unit(result, wavelength):
    """Helper function to take integrator result and return a two
    theta and q array regardless of the unit used for integration.

    args:
        result: result from 1dintegrator
        wavelength: wavelength for conversion in meters

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


class int_1d_data:
    """Container for 1-dimensional integration data returned by pyFAI,
    scanning detector version.
    
    attributes:
        raw: nzarray1d, raw integrated signal
        pcount: nzarray1d, how many pixels in each bin
        norm: nzarray1d, integrated signal normalized by number of
            pixels
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
    
    methods:
        from_hdf5: Loads in data from an hdf5 file
        from_result: Parses data in from result returned by pyFAI
        parse_unit: Ensures both q and ttheta data is held
        to_hdf5: Saves data to hdf5 file
    """
    def __init__(self, raw=None, pcount=None, norm=None, ttheta=0, q=0,
                 sigma=None, sigma_raw=None, monitor=1):
        """
        raw: nzarray1d, raw integrated signal
        pcount: nzarray1d, how many pixels in each bin
        norm: nzarray1d, integrated signal normalized by number of
            pixels
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
        """
        self.raw = raw
        self.pcount = pcount
        self.norm = norm
        self.ttheta = ttheta
        self.q = q
        self.sigma = sigma
        self.sigma_raw = sigma_raw

    def from_result(self, result, wavelength, monitor=1, unit=None):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.
        
        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        self.ttheta, self.q = self.parse_unit(
            result, wavelength, unit)

        self.pcount = result._count
        self.raw = result._sum_signal/monitor
        self.norm = self.raw/self.pcount
        if result.sigma is None:
            self.sigma = result._sum_signal
            self.sigma.data = np.sqrt(self.sigma.data)
            self.sigma /= (self.pcount * monitor)
            self.sigma_raw = result._sum_signal / (monitor**2)
        else:
            self.sigma = result.sigma / monitor
            self.sigma_raw = ((result._count * result.sigma)**2) / (monitor**2)
    
    def parse_unit(self, result, wavelength, unit=None):
        """Helper function to take integrator result and return a two
        theta and q array regardless of the unit used for integration.

        args:
            result: result from 1dintegrator
            wavelength: wavelength for conversion in meters

        returns:
            int_1d_2theta: two theta array
            int_1d_q: q array
        """
        if wavelength is None:
            return result.radial, None

        if unit is None:
            unit = result.unit

        if unit == units.TTH_DEG or str(unit) == '2th_deg':
            int_1d_2theta = result.radial
            int_1d_q = (
                (4 * np.pi / (wavelength*1e10)) *
                np.sin(np.radians(int_1d_2theta / 2))
            )
        elif unit == units.Q_A or str(unit) == 'q_A^-1':
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
        """Saves data to hdf5 file.
        
        args:
            grp: h5py Group or File, where the data will be saved
            compression: str, compression algorithm to use. See h5py
                documentation.
        """
        for key in ['raw', 'pcount', 'norm', 'sigma', 'sigma_raw']:
            attr = self.__getattribute__(key)
            if key in grp:
                if not utils.check_encoded(grp, 'nzarray'):
                    del grp[key]
                    sgrp = grp.create_group(key)
                else:
                    sgrp = grp[key]
            else:
                sgrp = grp.create_group(key)
            attr.to_hdf5(sgrp, compression)

        utils.attributes_to_h5(self, grp, ['ttheta', 'q'], compression=compression)
    
    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.
        
        args:
            grp: h5py Group or File, object to load data from.
        """
        self.raw.from_hdf5(grp['raw'])
        self.pcount.from_hdf5(grp['pcount'])
        self.norm.from_hdf5(grp['norm'])
        try:
            self.sigma.from_hdf5(grp['sigma'])
            self.sigma_raw.from_hdf5(grp['sigma_raw'])
        except KeyError:
            self.sigma = copy.deepcopy(self.norm)
            data = self.sigma.data
            if data[data > 0].size > 0:
                minval = data[data > 0].min()
                data[data > 0] = np.sqrt(data[data > 0]/minval) * minval
            self.sigma_raw = self.sigma * self.pcount
        utils.h5_to_attributes(self, grp, ['ttheta', 'q'])
    
    def __setattr__(self, name, value):
        """Ensures raw, norm, and pcount are nzarray1d objects.
        """
        if name in ['raw', 'norm', 'pcount', 'sigma', 'sigma_raw']:
            self.__dict__[name] = nzarray1d(value)
        else:
            super().__setattr__(name, value)
    
    def __add__(self, other):
        out = self.__class__()
        out.raw = self.raw + other.raw
        out.pcount = self.pcount + other.pcount
        out.sigma_raw = self.sigma_raw + other.sigma_raw

        #out.sigma = self.sigma*self.sigma + other.sigma*other.sigma
        #out.sigma.data = np.sqrt(out.sigma.data)
        out.sigma = copy.deepcopy(out.sigma_raw)
        out.sigma.data = np.sqrt(out.sigma_raw.data)
        out.sigma = out.sigma/out.pcount

        out.norm = out.raw/out.pcount
        out.ttheta = copy.deepcopy(self.ttheta)
        out.q = copy.deepcopy(self.q)
        try:
            out.chi = copy.deepcopy(self.chi)
        except AttributeError:
            pass
        return out

class int_2d_data(int_1d_data):
    """Container for 2-dimensional integration data returned by pyFAI.
    
    attributes:
        raw: nzarray2d, raw integrated signal
        pcount: nzarray2d, how many pixels in each bin
        norm: nzarray2d, integrated signal normalized by number of
            pixels
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
        chi: numpy array, chi values
    
    methods:
        from_hdf5: Loads in data from an hdf5 file
        from_result: Parses data in from result returned by pyFAI
        parse_unit: Ensures both q and ttheta data is held
        to_hdf5: Saves data to hdf5 file
    """
    def __init__(self,  raw=None, pcount=None, norm=None, ttheta=0, q=0,
                 chi=0, sigma=None, sigma_raw=None):
        """
        raw: nzarray2d, raw integrated signal
        pcount: nzarray2d, how many pixels in each bin
        norm: nzarray2d, integrated signal normalized by number of
            pixels
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
        chi: numpy array, chi values
        """
        self.raw = raw
        self.pcount = pcount
        self.norm = norm
        self.ttheta = ttheta
        self.q = q
        self.chi = chi
        self.sigma = sigma
        self.sigma_raw = sigma_raw

    def from_result(self, result, wavelength, monitor=1, unit=None):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.
        
        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        super(int_2d_data, self).from_result(result, wavelength, monitor, unit)
        self.chi = result.azimuthal
    
    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.
        
        args:
            grp: h5py Group or File, object to load data from.
        """
        super().from_hdf5(grp)
        utils.h5_to_attributes(self, grp, ['chi'])

    def to_hdf5(self, grp, compression=None):
        """Saves data to hdf5 file.
        
        args:
            grp: h5py Group or File, where the data will be saved
            compression: str, compression algorithm to use. See h5py
                documentation.
        """
        super().to_hdf5(grp, compression)
        utils.attributes_to_h5(self, grp, ['chi'], compression=compression)

    def __setattr__(self, name, value):
        """Ensures raw, norm, and pcount are nzarray2d objects.
        """
        if name in ['raw', 'norm', 'pcount', 'sigma', 'sigma_raw']:
            self.__dict__[name] = nzarray2d(value)
        else:
            super().__setattr__(name, value)
