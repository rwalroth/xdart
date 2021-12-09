import copy

import numpy as np
from pyFAI import units
from scipy.interpolate import RectBivariateSpline

from .. import _utils as utils

from icecream import ic; ic.configureOutput(prefix='', includeContext=True)


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
        return np.asarray(int_1d_2theta, dtype=np.float32), np.asarray(int_1d_q, dtype=np.float32)

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

    # def __init__(self, i_tthChi=np.zeros(0), i_qChi=np.zeros(0), ttheta=0, q=0, chi=0,
    def __init__(self, i_tthChi=0, i_qChi=0, ttheta=0, q=0, chi=0,
                 i_QxyQz=0, qz=0, qxy=0):
        """
        raw: nzarray2d, raw integrated signal
        pcount: nzarray2d, how many pixels in each bin
        norm: nzarray2d, integrated signal normalized by number of
            pixels
        ttheta: numpy array, two-theta angle
        q: numpy array, q values
        chi: numpy array, chi values
        """
        self.i_tthChi = i_tthChi
        self.i_qChi = i_qChi
        self.ttheta = ttheta
        self.q = q
        self.chi = chi
        self.i_QxyQz = i_QxyQz
        self.qz = qz
        self.qxy = qxy
        self.q_from_tth = True
        self.tth_from_q = True

    def from_result(self, result, wavelength, unit=None,
                    i_QxyQz=0, qz=0, qxy=0):
        """Parses out result obtained by pyFAI AzimuthalIntegrator.
        args:
            result: object returned by AzimuthalIntegrator
            wavelength: float, energy of the beam in meters
        """
        if unit is None:
            unit = result.unit

        self.parse_unit(result, wavelength, unit=unit)

        self.i_QxyQz = i_QxyQz
        self.qz = qz
        self.qxy = qxy

    def parse_unit(self, result, wavelength, unit=None):
        """Helper function to take integrator result and return a two
        theta and q array regardless of the unit used for integration.

        args:
            result: result from 1d integrator
            wavelength: wavelength for conversion in meters

        returns:
            int_1d_2theta: two theta array
            int_1d_q: q array
        """
        if wavelength is None:
            return result.radial, None

        if unit is None:
            unit = result.unit

        self.chi = chi = result.azimuthal

        if unit == units.TTH_DEG or str(unit) == '2th_deg':
            self.i_tthChi = result.intensity
            self.ttheta = tth = result.radial
            self.tth_from_q = False
            # if isinstance(self.i_qChi, int) or self.q_from_tth:
            if self.q_from_tth:
                tth_range = np.asarray([tth[0], tth[-1]])
                q_range = (4 * np.pi / (wavelength * 1e10)) * np.sin(np.radians(tth_range / 2))
                qtth = (4 * np.pi / (wavelength * 1e10)) * np.sin(np.radians(tth / 2))
                self.q = q = np.linspace(q_range[0], q_range[1], len(tth))

                spline = RectBivariateSpline(chi, qtth, result.intensity)
                self.i_qChi = spline(chi, q)
                # self.q_from_tth = True

        elif unit == units.Q_A or str(unit) == 'q_A^-1':
            self.i_qChi = result.intensity
            self.q = q = result.radial
            self.q_from_tth = False
            # if isinstance(self.i_tthChi, int) or self.tth_from_q:
            ic(self.tth_from_q)
            if self.tth_from_q:
                ic('converting to tth')
                q_range = np.array([q[0], q[-1]])
                tth_range = 2 * np.degrees(np.arcsin(q_range * (wavelength * 1e10) / (4 * np.pi)))
                tthq = 2 * np.degrees(np.arcsin(q * (wavelength * 1e10) / (4 * np.pi)))
                self.ttheta = tth = np.linspace(tth_range[0], tth_range[1], len(q))

                spline = RectBivariateSpline(chi, tthq, result.intensity)
                self.i_tthChi = spline(chi, tth)
                # self.tth_from_q = True

        # TODO: implement other unit options for unit

    def from_hdf5(self, grp):
        """Loads in data from hdf5 file.

        args:
            grp: h5py Group or File, object to load data from.
        """
        super().from_hdf5(grp)
        utils.h5_to_attributes(
            self, grp, ['chi', 'i_QxyQz', 'qz', 'qxy', 'q_from_tth', 'tth_from_q']
        )

    def to_hdf5(self, grp, compression=None):
        """Saves data to hdf5 file.

        args:
            grp: h5py Group or File, where the data will be saved
            compression: str, compression algorithm to use. See h5py
                documentation.
        """
        super().to_hdf5(grp, compression)
        utils.attributes_to_h5(
            self, grp, ['chi', 'i_QxyQz', 'qz', 'qxy', 'q_from_tth', 'tth_from_q'],
            compression=compression
        )

    def __setattr__(self, name, value):
        """Ensures all saved objects are np.ndarray objects.
        """
        self.__dict__[name] = np.asarray(value)

    def __add__(self, other):
        out = self.__class__()

        out.i_qChi = self.i_qChi + other.i_qChi
        out.i_tthChi = self.i_tthChi + other.i_tthChi
        out.i_QxyQz = self.i_QxyQz + other.i_QxyQz

        out.ttheta = copy.deepcopy(other.ttheta)
        out.q = copy.deepcopy(other.q)
        out.chi = copy.deepcopy(other.chi)
        out.qz = copy.deepcopy(other.qz)
        out.qxy = copy.deepcopy(other.qxy)

        return out

    def __sub__(self, other):
        out = self.__class__()

        out.i_qChi = self.i_qChi - other.i_qChi
        out.i_tthChi = self.i_tthChi - other.i_tthChi
        out.i_QxyQz = self.i_QxyQz - other.i_QxyQz

        out.ttheta = copy.deepcopy(other.ttheta)
        out.q = copy.deepcopy(other.q)
        out.chi = copy.deepcopy(other.chi)
        out.qz = copy.deepcopy(other.qz)
        out.qxy = copy.deepcopy(other.qxy)

        return out
