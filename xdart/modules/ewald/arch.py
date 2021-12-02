# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 14:21:58 2019

@author: walroth
"""
import copy
from threading import Condition

from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from pyFAI.containers import Integrate1dResult, Integrate2dResult
from pyFAI import units
import numpy as np

from xdart import utils
from xdart.utils.containers import PONI, int_1d_data, int_2d_data, create_ai_from_dict
from xdart.utils.containers import int_1d_data_static, int_2d_data_static

# from icecream import ic; ic.configureOutput(prefix='', includeContext=True)


class EwaldArch():
    """Class for storing area detector data collected in
    X-ray diffraction experiments.

    Attributes:
        ai_args: dict, arguments passed to AzimuthalIntegrator
        arch_lock: Condition, threading lock used to ensure only one
            process can access data at a time
        file_lock: Condition, lock to ensure only one writer to
            data file
        idx: int, integer name of arch
        int_1d: int_1d_data/_static object from containers (for scanning/static detectors)
        int_2d: int_2d_data/_static object from containers (for scanning/static detectors)
        integrator: AzimuthalIntegrator object from pyFAI
        map_raw: numpy 2d array of the unprocessed image data
        bg_raw: numpy 2d array of the unprocessed image data for BG
        map_norm: float, normalization constant
        mask: numpy array of indeces to be masked in array.
        poni: poni data for integration
        poni_dict: poni_file information saved in dictionary
        scan_info: dict, information from any relevant motors and
            sensors
        static: bool, flag to specify if detector is static
        gi: bool, flag to specify if scattering geometry is grazing incidence
        th_mtr: str, the motor that controls sample rotation in gi mode
        tilt_angle: float, chi offset in gi geometry

    Methods:
        copy: create copy of arch
        get_mask: return mask array to feed into integrate1d
        integrate_1d: integrate the image data, results stored in
            int_1d_data
        integrate_2d: integrate the image data, results stored in
            int_2d_data
        load_from_h5: load data from hdf5 file
        save_to_h5: save data to hdf5 file
        set_integrator: set new integrator
        set_map_raw: replace raw data
        set_mask: replace mask data
        set_poni: replace poni object
        set_scan_info: replace scan_info
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, idx=None, map_raw=None, poni=None, mask=None,
                 scan_info={}, ai_args={}, file_lock=Condition(),
                 static=False, poni_dict=None, bg_raw=0,
                 gi=False, th_mtr='th', tilt_angle=0
                 ):
        # pylint: disable=too-many-arguments
        """idx: int, name of the arch.
        map_raw: numpy array, raw image data
        bg_raw: numpy array, raw image data for BG
        poni: PONI object, calibration data
        mask: None or numpy array, indices of pixels to mask
        scan_info: dict, metadata about scan
        ai_args: dict, args to be fed to azimuthalIntegrator constructor
        file_lock: Condition, lock for file access.
        """
        super(EwaldArch, self).__init__()
        self.idx = idx
        self.map_raw = map_raw
        self.bg_raw = bg_raw
        if poni is None:
            self.poni = PONI()
        else:
            self.poni = poni
        self.poni_dict = poni_dict
        if mask is None and map_raw is not None:
            self.mask = np.arange(map_raw.size)[map_raw.flatten() < 0]
        else:
            self.mask = mask
        self.scan_info = scan_info
        self.ai_args = ai_args
        self.file_lock = file_lock

        self.static = static
        self.gi = gi
        self.th_mtr = th_mtr
        self.tilt_angle = tilt_angle

        self.integrator = self.setup_integrator()

        self.arch_lock = Condition()
        self.map_norm = 1

        if self.static:
            self.int_1d = int_1d_data_static()
            self.int_2d = int_2d_data_static()
        else:
            self.int_1d = int_1d_data()
            self.int_2d = int_2d_data()

    def setup_integrator(self):
        """Sets up integrator object"""
        if self.poni_dict is not None:
            integrator = create_ai_from_dict(self.poni_dict, self.gi)
        else:
            integrator = AzimuthalIntegrator(
                dist=self.poni.dist,
                poni1=self.poni.poni1,
                poni2=self.poni.poni2,
                rot1=self.poni.rot1,
                rot2=self.poni.rot2,
                rot3=self.poni.rot3,
                wavelength=self.poni.wavelength,
                detector=self.poni.detector,
                **self.ai_args
            )
        return integrator

    def reset(self):
        """Clears all data, resets to a default EwaldArch.
        """
        self.idx = None
        self.map_raw = None
        self.bg_raw = None
        self.poni = PONI()
        self.poni_dict = None
        self.mask = None
        self.scan_info = {}
        self.integrator = self.setup_integrator()
        self.map_norm = 1
        if self.static:
            self.int_1d = int_1d_data_static()
            self.int_2d = int_2d_data_static()
        else:
            self.int_1d = int_1d_data()
            self.int_2d = int_2d_data()
            
    def get_mask(self, global_mask=None):
        if global_mask is not None:
            mask_idx = np.unique(np.append(self.mask, global_mask))
            # mask_idx.sort()
        else:
            mask_idx = self.mask
        mask = np.zeros(self.map_raw.size, dtype=int)
        try:
            mask[mask_idx] = 1
            return mask.reshape(self.map_raw.shape)
        except IndexError:
            print('Mask File Shape Mismatch')
            return mask

    def integrate_1d(self, numpoints=10000, radial_range=None,
                     monitor=None, unit=units.TTH_DEG, global_mask=None, **kwargs):
        """Wrapper for integrate1d method of AzimuthalIntegrator from pyFAI.
        Returns result and also stores the data in the int_1d object.

        args:
            numpoints: int, number of points in final array
            radial_range: tuple or list, lower and upper end of integration
            monitor: str, keyword for normalization counter in scan_info
            unit: pyFAI unit for integration, units.TTH_DEG, units.Q_A,
                '2th_deg', or 'q_A^-1'
            kwargs: other keywords to be passed to integrate1d, see pyFAI docs.

        returns:
            result: integrate1d result from pyFAI.
        """
        if (not self.static) and (radial_range is None):
            radial_range = [0, 180]

        with self.arch_lock:
            if self.static:
                self.map_norm = 1
            elif monitor is not None:
                self.map_norm = self.scan_info[monitor]

            if self.mask is None:
                self.mask = np.arange(self.map_raw.size)[self.map_raw.flatten() < 0]

            if not self.gi:
                result = self.integrator.integrate1d(
                    # self.map_raw/self.map_norm, numpoints, unit=unit,
                    (self.map_raw-self.bg_raw)/self.map_norm, numpoints, unit=unit,
                    radial_range=radial_range, mask=self.get_mask(global_mask),
                    **kwargs
                )

                wavelength = self.poni.wavelength
                if self.static:
                    wavelength = self.integrator.wavelength
                self.int_1d.from_result(result, wavelength, unit=unit)
            else:
                pg_args = ['process', 'filename', 'correctSolidAngle', 'variance', 'error_model',
                           'dummy', 'delta_dummy', 'polarization_factor', 'dark', 'flat',
                           'method', 'safe', 'normalization_factor']
                pg_args = {k: v for (k, v) in kwargs.items() if k in pg_args}

                # incident angle in deg
                try:
                    self.integrator.incident_angle = self.scan_info[self.th_mtr]
                except KeyError:
                    pass
                # tilt angle of sample in deg (misalignment in "chi")
                self.integrator.tilt_angle = self.tilt_angle

                Intensity, qAxis = self.integrator.integrate_1d(
                        # self.map_raw/self.map_norm, numpoints, unit='q_A^-1',
                        (self.map_raw-self.bg_raw)/self.map_norm, numpoints, unit='q_A^-1',
                        p0_range=radial_range, p1_range=kwargs['azimuth_range'],
                        mask=self.get_mask(global_mask), **pg_args
                )
                result = Integrate1dResult(qAxis, Intensity)

                self.int_1d.from_result(result, self.integrator.wavelength, unit='q_A^-1')

        # q = result.radial
        # return result
      
    def integrate_2d(self, npt_rad=1000, npt_azim=1000, monitor=None,
                     radial_range=None, azimuth_range=None,
                     x_range=None, y_range=None,
                     unit=units.TTH_DEG, global_mask=None, **kwargs):
        """Wrapper for integrate2d method of AzimuthalIntegrator from pyFAI.
        Returns result and also stores the data in the int_2d object.

        args:
            npt_rad: int, number of points in radial dimension. If
                None, will take number from the shape of map_norm
            npt_azim: int, number of points in azimuthal dimension. If
                None, will take number from the shape of map_norm
            radial_range: tuple or list, lower and upper end of integration
            azimuth_range: tuple or list, lower and upper end of integration
                in azimuthal direction
            monitor: str, keyword for normalization counter in scan_info
            unit: pyFAI unit for integration, units.TTH_DEG, units.Q_A,
                '2th_deg', or 'q_A^-1'
            kwargs: other keywords to be passed to integrate2d, see pyFAI docs.

        returns:
            result: integrate2d result from pyFAI.
        """
        if (not self.static) and (radial_range is None):
            radial_range = [0, 180]
        if (not self.static) and (azimuth_range is None):
            azimuth_range = [-180, 180]

        with self.arch_lock:
            if monitor is not None:
                if self.static:
                    self.map_norm = 1
                else:
                    self.map_norm = self.scan_info[monitor]

            if self.mask is None:
                self.mask = np.arange(self.map_raw.size)[self.map_raw.flatten() < 0]
            
            if npt_rad is None:
                npt_rad = self.map_raw.shape[0]
            
            if npt_azim is None:
                npt_azim = self.map_raw.shape[1]

            if not self.gi:
                result = self.integrator.integrate2d(
                    # self.map_raw/self.map_norm, npt_rad, npt_azim, unit=unit,
                    (self.map_raw-self.bg_raw)/self.map_norm, npt_rad, npt_azim, unit=unit,
                    mask=self.get_mask(global_mask), radial_range=radial_range,
                    azimuth_range=azimuth_range, **kwargs
                )
                wavelength = self.poni.wavelength
                if self.static:
                    wavelength = self.integrator.wavelength
                self.int_2d.from_result(result, wavelength, unit=unit)
            else:
                pg_args = ['filename', 'correctSolidAngle', 'variance', 'error_model',
                           'dummy', 'delta_dummy', 'polarization_factor', 'dark', 'flat',
                           'method', 'safe', 'normalization_factor']
                pg_args = {k: v for (k, v) in kwargs.items() if k in pg_args}

                # incident angle in deg
                self.integrator.incident_angle = self.scan_info[self.th_mtr]
                # tilt angle of sample in deg (misalignment in "chi")
                self.integrator.tilt_angle = self.tilt_angle

                if unit == '2th_deg':
                    radial_range = self.convert_radial_range(radial_range, self.integrator.wavelength)

                # Transform to polar (Q-Chi) coordinates
                i_qchi, Q, Chi = self.integrator.transform_image(
                    self.map_raw-self.bg_raw, process='polar', npt=(npt_rad, npt_azim),
                    x_range=radial_range, y_range=azimuth_range, unit='q_A^-1',
                    mask=self.get_mask(global_mask), all=False, **pg_args)
                result = Integrate2dResult(i_qchi, Q, Chi)

                # Transform to reciprocal (Qz-Qxy) coordinates
                i_QxyQz, qxy, qz = self.integrator.transform_image(
                    self.map_raw-self.bg_raw, process='reciprocal', npt=(npt_rad, npt_azim),
                    x_range=x_range, y_range=y_range, unit='q_A^-1',
                    mask=self.get_mask(), all=False, **pg_args)

                self.int_2d.from_result(result, self.integrator.wavelength, unit=unit,
                                        i_QxyQz=np.flipud(i_QxyQz), qz=qz, qxy=qxy)

    def set_integrator(self, **args):
        """Sets AzimuthalIntegrator with new arguments.

        args:
            args: see pyFAI for acceptable arguments for the integrator
                constructor.

        returns:
            None
        """

        with self.arch_lock:
            self.ai_args = args
            self.integrator = self.setup_integrator()

    def set_map_raw(self, new_data):
        with self.arch_lock:
            self.map_raw = new_data
            if self.mask is None:
                self.mask = np.arange(new_data.size)[new_data.flatten() < 0]

    def set_poni(self, new_data):
        with self.arch_lock:
            self.poni = new_data

    def set_mask(self, new_data):
        with self.arch_lock:
            self.mask = new_data

    def set_scan_info(self, new_data):
        with self.arch_lock:
            self.scan_info = new_data

    @staticmethod
    def convert_radial_range(radial_range, wavelength):
        """Convert radial range from Q (AA-1) to 2Th (deg)"""
        if radial_range is None:
            return None

        radial_range = np.asarray(radial_range)
        radial_range = (4 * np.pi / (wavelength * 1e10)) *\
            np.sin(np.radians(radial_range / 2))

        return radial_range

    def save_to_h5(self, file, compression='lzf'):
        """Saves data to hdf5 file using h5py as backend.

        args:
            file: h5py group or file object.

        returns:
            None
        """
        if self.static:
            compression = None
        with self.file_lock:
            if str(self.idx) in file:
                grp = file[str(self.idx)]
            else:
                grp = file.create_group(str(self.idx))
            grp.attrs['type'] = 'EwaldArch'
            lst_attr = [
                "map_raw", "mask", "map_norm", "scan_info", "ai_args",
                "gi", "static", "poni_dict", "bg_raw"
            ]
            utils.attributes_to_h5(self, grp, lst_attr,
                                   compression=compression)
            if 'int_1d' not in grp:
                grp.create_group('int_1d')
            self.int_1d.to_hdf5(grp['int_1d'], compression)
            if 'int_2d' not in grp:
                grp.create_group('int_2d')
            self.int_2d.to_hdf5(grp['int_2d'], compression)
            if 'poni' not in grp:
                grp.create_group('poni')
            utils.dict_to_h5(self.poni.to_dict(), grp, 'poni')

    def load_from_h5(self, file, load_2d=True):
        """Loads data from hdf5 file and sets attributes.

        args:
            file: h5py file or group object
        """
        with self.file_lock:
            with self.arch_lock:
                if str(self.idx) not in file:
                    print("No data can be found")
                else:
                    grp = file[str(self.idx)]
                    if 'type' in grp.attrs:
                        if grp.attrs['type'] == 'EwaldArch':
                            lst_attr = [
                                "map_raw", "mask", "map_norm", "scan_info", "ai_args",
                                "gi", "static", "poni_dict", "bg_raw"
                            ]
                            utils.h5_to_attributes(self, grp, lst_attr)
                            self.int_1d.from_hdf5(grp['int_1d'])
                            if load_2d:
                                self.int_2d.from_hdf5(grp['int_2d'])
                            self.poni = PONI.from_yamdict(
                                utils.h5_to_dict(grp['poni'])
                            )

                            if self.poni_dict is not None:
                                self.integrator = create_ai_from_dict(self.poni_dict)
                            else:
                                self.integrator = AzimuthalIntegrator(
                                    dist=self.poni.dist,
                                    poni1=self.poni.poni1,
                                    poni2=self.poni.poni2,
                                    rot1=self.poni.rot1,
                                    rot2=self.poni.rot2,
                                    rot3=self.poni.rot3,
                                    wavelength=self.poni.wavelength,
                                    detector=self.poni.detector,
                                    **self.ai_args
                                )

    def copy(self, include_2d=True):
        """Returns a copy of self.
        """
        arch_copy = EwaldArch(
            copy.deepcopy(self.idx), None,
            copy.deepcopy(self.poni), None,
            copy.deepcopy(self.scan_info), copy.deepcopy(self.ai_args),
            self.file_lock, poni_dict=copy.deepcopy(self.poni_dict),
            static=copy.deepcopy(self.static), gi=copy.deepcopy(self.gi),
            th_mtr=copy.deepcopy(self.th_mtr)
        )
        arch_copy.integrator = copy.deepcopy(self.integrator)
        arch_copy.arch_lock = Condition()
        arch_copy.int_1d = copy.deepcopy(self.int_1d)
        if include_2d:
            arch_copy.map_raw = copy.deepcopy(self.map_raw)
            arch_copy.bg_raw = copy.deepcopy(self.bg_raw)
            arch_copy.mask = copy.deepcopy(self.mask),
            arch_copy.map_norm = copy.deepcopy(self.map_norm)
            arch_copy.int_2d = copy.deepcopy(self.int_2d)

        return arch_copy
