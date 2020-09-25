import copy

import numpy as np
from pyFAI import units

from .nzarrays import nzarray2d
from .. import _utils as utils


class int_1d_data_static:
    """Container for 1-dimensional integration data returned by pyFAI.

    attributes:
        norm: np.ndarray, integrated signal
        ttheta: numpy array, two-theta angle
        q: numpy array, q values

    methods:
        from_hdf5: Loads in data from an hdf5 file
        from_result: Parses data in from result returned by pyFAI
        parse_unit: Ensures both q and ttheta data is held
        to_hdf5: Saves data to hdf5 file
    """

    def __init__(self, norm=None, ttheta=0, q=0):
        """
        norm: np.ndarray, integrated signal
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
        """
        self.norm = norm
        self.ttheta = ttheta
        self.q = q

    def from_result(self, result, wavelength, unit=None):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.

        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        self.ttheta, self.q = self.parse_unit(
            result, wavelength, unit=unit)

        self.norm = result.intensity

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

        # if result.unit == units.TTH_DEG or str(result.unit) == '2th_deg':
        if unit == units.TTH_DEG or str(unit) == '2th_deg':
            int_1d_2theta = result.radial
            int_1d_q = (
                    (4 * np.pi / (wavelength * 1e10)) *
                    np.sin(np.radians(int_1d_2theta / 2))
            )
        # elif result.unit == units.Q_A or str(result.unit) == 'q_A^-1':
        elif unit == units.Q_A or str(unit) == 'q_A^-1':
            int_1d_q = result.radial
            int_1d_2theta = (
                2 * np.degrees(np.arcsin(
                    int_1d_q * (wavelength * 1e10) / (4 * np.pi)))
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
        keys = self.__dict__.keys()
        for key in keys:
            if key in grp:
                del grp[key]
        utils.attributes_to_h5(self, grp, keys, compression=compression)

    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.

        args:
            grp: h5py Group or File, object to load data from.
        """
        keys = self.__dict__.keys()
        utils.h5_to_attributes(self, grp, keys)

    def __setattr__(self, name, value):
        """Ensures raw, norm, and pcount are nzarray1d objects.
        """
        self.__dict__[name] = np.asarray(value)

    def __add__(self, other):
        out = self.__class__()
        out.norm = self.norm + other.norm
        out.ttheta = copy.deepcopy(self.ttheta)
        out.q = copy.deepcopy(self.q)
        return out


class int_2d_data_static(int_1d_data_static):
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

    def __init__(self, norm=None, ttheta=0, q=0, chi=0,
                 i_q=0, qz=0, qxy=0):
        """
        raw: nzarray2d, raw integrated signal
        pcount: nzarray2d, how many pixels in each bin
        norm: nzarray2d, integrated signal normalized by number of
            pixels
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
        chi: numpy array, chi values
        """
        self.norm = norm
        self.ttheta = ttheta
        self.q = q
        self.chi = chi
        self.i_q = i_q
        self.qz = qz
        self.qxy = qxy

    def from_result(self, result, wavelength, unit=None,
                    i_q=0, qz=0, qxy=0):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.

        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        if unit is None:
            unit = result.unit
        super(int_2d_data_static, self).from_result(result, wavelength, unit=unit)
        self.chi = result.azimuthal
        self.i_q = i_q
        self.qz = qz
        self.qxy = qxy

    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.

        args:
            grp: h5py Group or File, object to load data from.
        """
        super().from_hdf5(grp)
        utils.h5_to_attributes(self, grp, ['chi', 'i_q', 'qz', 'qxy'])

    def to_hdf5(self, grp, compression=None):
        """Saves data to hdf5 file.

        args:
            grp: h5py Group or File, where the data will be saved
            compression: str, compression algorithm to use. See h5py
                documentation.
        """
        super().to_hdf5(grp, compression)
        utils.attributes_to_h5(self, grp, ['chi', 'i_q', 'qz', 'qxy'],
                               compression=compression)

    def __setattr__(self, name, value):
        """Ensures all saved objects are np.ndarray objects.
        """
        self.__dict__[name] = np.asarray(value)
