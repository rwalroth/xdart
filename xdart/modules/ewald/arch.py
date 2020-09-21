# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 14:21:58 2019

@author: walroth
"""
import copy
from threading import Condition

import pyFAI
import pygix
from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from pyFAI.containers import Integrate1dResult, Integrate2dResult
from pyFAI import units
import numpy as np

from xdart import utils
from xdart.utils.containers import PONI, int_1d_data, int_2d_data
from xdart.utils.containers import int_1d_data_static, int_2d_data_static


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
        map_norm: float, normalization constant
        mask: numpy array of indeces to be masked in array.
        poni: poni data for integration
        scan_info: dict, information from any relevant motors and
            sensors

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
                 poni_file=None, static=False, gi=False):
        # pylint: disable=too-many-arguments
        """idx: int, name of the arch.
        map_raw: numpy array, raw image data
        poni: PONI object, calibration data
        mask: None or numpy array, indeces of pixels to mask
        scan_info: dict, metadata about scan
        ai_args: dict, args to be fed to azimuthalIntegrator constructor
        file_lock: Condition, lock for file access.
        """
        super(EwaldArch, self).__init__()
        self.idx = idx
        self.map_raw = map_raw
        if poni is None:
            self.poni = PONI()
        else:
            self.poni = poni
        self.poni_file = poni_file
        if mask is None and map_raw is not None:
            self.mask = np.arange(map_raw.size)[map_raw.flatten() < 0]
        else:
            self.mask = mask
        self.scan_info = scan_info
        self.ai_args = ai_args
        self.file_lock = file_lock

        self.static = static
        self.gi = gi
        print(f'arch > __init__: self.static = {self.static}')
        print(f'arch > __init__: self.gi = {self.gi}')

        if self.poni_file is not None:
            if not self.gi:
                self.integrator = pyFAI.load(poni_file)
                self.integrator._rot3 -= np.deg2rad(90)
            else:
                pFAI = pyFAI.load(poni_file)
                calib_pars = dict(
                    dist=pFAI.dist, poni1=pFAI.poni1, poni2=pFAI.poni2,
                    rot1=pFAI.rot1, rot2=pFAI.rot2, rot3=pFAI.rot3,
                    wavelength=pFAI.wavelength, detector=pFAI.detector)
                self.integrator = pygix.Transform(**calib_pars)
                self.integrator.sample_orientation = 3  # 1 is horizontal, 2 is vertical
                self.integrator.incident_angle = 1  # incident angle in deg
                self.integrator.tilt_angle = 0  # tilt angle of sample in deg (misalignment in "chi")
                print(f'arch > EwaldArch: self.integrator = {self.integrator}')

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
                **ai_args
            )
        self.arch_lock = Condition()
        self.map_norm = 1

        if self.static:
            self.int_1d = int_1d_data_static()
            self.int_2d = int_2d_data_static()
        else:
            self.int_1d = int_1d_data()
            self.int_2d = int_2d_data()
    
    def reset(self):
        """Clears all data, resets to a default EwaldArch.
        """
        self.idx = None
        self.map_raw = None
        self.poni = PONI()
        self.poni_file = None
        self.mask = None
        self.scan_info = {}
        if self.poni_file is not None:
            if not self.gi:
                self.integrator = pyFAI.load(poni_file)
                self.integrator._rot3 -= np.deg2rad(90)
            else:
                pFAI = pyFAI.load(poni_file)
                calib_pars = dict(
                    dist=pFAI.dist, poni1=pFAI.poni1, poni2=pFAI.poni2,
                    rot1=pFAI.rot1, rot2=pFAI.rot2, rot3=pFAI.rot3,
                    wavelength=pFAI.wavelength, detector=pFAI.detector)
                self.integrator = pygix.Transform(**calib_pars)
                self.integrator.sample_orientation = 3  # 1 is horizontal, 2 is vertical
                self.integrator.incident_angle = 1  # incident angle in deg
                self.integrator.tilt_angle = 0  # tilt angle of sample in deg (misalignment in "chi")
                print(f'arch > EwaldArch: self.integrator = {self.integrator}')

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
        self.map_norm = 1
        if self.static:
            self.int_1d = int_1d_data_static()
            self.int_2d = int_2d_data_static()
        else:
            self.int_1d = int_1d_data()
            self.int_2d = int_2d_data()

    def get_mask(self):
        mask = np.zeros(self.map_raw.size, dtype=int)
        mask[self.mask] = 1
        return mask.reshape(self.map_raw.shape)

    # def integrate_1d(self, numpoints=10000, radial_range=[0, 180],
    def integrate_1d(self, numpoints=10000, radial_range=None,
                     monitor=None, unit=units.TTH_DEG, **kwargs):
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
        print(f'arch > integrate_1d: radial_range = {radial_range}')
        print(f'arch > integrate_1d: gi = {self.gi}')
        if (not self.static) and (radial_range is None):
            print(f'arch > integrate_1d > setting radial_range: {radial_range}')
            radial_range = [0, 180]

        with self.arch_lock:
            if monitor is not None:
                self.map_norm = self.scan_info[monitor]

            # TODO Take care of Monitor
            self.map_norm = 1
            print(f'arch > integrate_1d: monitor = {self.map_norm}')

            if self.mask is None:
                self.mask = np.arange(self.map_raw.size)[self.map_raw.flatten() < 0]

            if not self.gi:
                result = self.integrator.integrate1d(
                    self.map_raw/self.map_norm, numpoints, unit=unit, radial_range=radial_range,
                    mask=self.get_mask(), **kwargs
                )
                self.int_1d.from_result(result, self.poni.wavelength)
            else:
                print(f"\n##########arch > integrate_1d: pyGIX integration numpoints, radial_range, azim_range, kwargs"
                      f"{numpoints}, {radial_range}, {kwargs['azimuth_range']}, {kwargs}")
                pg_args = ['process', 'filename', 'correctSolidAngle', 'variance', 'error_model',
                           'mask', 'dummy', 'delta_dummy', 'polarization_factor', 'dark', 'flat',
                           # 'method', 'unit', 'safe', 'normalization_factor']
                           'method', 'safe', 'normalization_factor']
                pg_args = {k: v for (k, v) in kwargs.items() if k in pg_args}

                Intensity, qAxis = self.integrator.integrate_1d(
                    self.map_raw/self.map_norm, numpoints, unit='q_A^-1',
                    p0_range=radial_range, p1_range=kwargs['azimuth_range'],
                    mask=self.get_mask(), **pg_args
                )
                result = Integrate1dResult(qAxis, Intensity)
                print(f'arch > integrate1d: result = {result.__dict__.keys()}')
                print(f'arch > integrate1d: wavelength = {self.poni.wavelength}')

                self.int_1d.from_result(result, self.poni.wavelength, unit='q_A^-1')


        print(f'\n----------arch > integrate_1d: result.dict = {result.__dict__.keys()}')
        # intensity = result.intensity
        q = result.radial
        print(f'arch > integrate_1d: tth = {q.min()}, {q.max()}, {q.shape}')

        return result

    def integrate_2d(self, npt_rad=1000, npt_azim=1000, monitor=None,
                     # radial_range=[0,180], azimuth_range=[-180,180],
                     radial_range=None, azimuth_range=None,
                     unit=units.TTH_DEG, **kwargs):
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
        print(f'arch > integrate_2d: radial_range = {radial_range}')
        print(f'arch > integrate_2d: kwargs = {kwargs}')
        print(f'arch > integrate_2d: gi = {self.gi}')
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

            # TODO Take care of Monitor
            self.map_norm = 1
            print(f'arch > integrate_2d: monitor = {self.map_norm}')

            if self.mask is None:
                self.mask = np.arange(self.map_raw.size)[self.map_raw.flatten() < 0]
            
            if npt_rad is None:
                npt_rad = self.map_raw.shape[0]
            
            if npt_azim is None:
                npt_azim = self.map_raw.shape[1]

            if not self.gi:
                result = self.integrator.integrate2d(
                    self.map_raw/self.map_norm, npt_rad, npt_azim, unit=unit,
                    mask=self.get_mask(), radial_range=radial_range,
                    azimuth_range=azimuth_range, **kwargs
                )
            else:
                print(f"\n##########arch > integrate_2d: pyGIX integration npt_rad, npt_azim, radial_range, kwargs"
                      f"{npt_rad}, {npt_azim}, {radial_range}, {kwargs}")
                pg_args = ['process', 'filename', 'correctSolidAngle', 'variance', 'error_model',
                           'mask', 'dummy', 'delta_dummy', 'polarization_factor', 'dark', 'flat',
                           'method', 'unit', 'safe', 'normalization_factor']
                pg_args = {k: v for (k, v) in kwargs.items() if k in pg_args}

                Intensity, Q, Chi = self.integrator.transform_polar(
                    self.map_raw/self.map_norm, npt=(npt_rad, npt_azim), unit='A',
                    q_range=radial_range, chi_range=azimuth_range,
                    mask=self.get_mask(), **pg_args
                )
                result = Integrate2dResult(Intensity, Q, Chi)

            self.int_2d.from_result(result, self.poni.wavelength, unit=unit)

        print(f'arch > integrate_2d: result.dict = {result.__dict__.keys()}')
        # ii, ii1 = result.intensity, result._sum_signal
        ii = result.intensity
        lt0 = np.sum(ii < 0)
        q, chi = result.radial, result.azimuthal
        print(f'arch > integrate_2d: map_norm = {self.map_norm}')
        print(f'arch > integrate_2d: q = {q.min()}, {q.max()}, {q.shape}')
        print(f'arch > integrate_2d: chi = {chi.min()}, {chi.max()}, {chi.shape}')
        print(f'arch > integrate_2d: intensity = {ii.min()}, {ii.max()}, {ii.mean()}, {ii.shape}')
        # print(f'arch > integrate_2d: intensity = {ii1.min()}, {ii1.max()}, {ii1.mean()}, {ii1.shape}')
        print(f'arch > integrate_2d: less than 0 = {lt0}')

        return result

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

            if self.poni_file is not None:
                if not self.gi:
                    self.integrator = pyFAI.load(poni_file)
                    self.integrator._rot3 -= np.deg2rad(90)
                else:
                    pFAI = pyFAI.load(poni_file)
                    calib_pars = dict(
                        dist=pFAI.dist, poni1=pFAI.poni1, poni2=pFAI.poni2,
                        rot1=pFAI.rot1, rot2=pFAI.rot2, rot3=pFAI.rot3,
                        wavelength=pFAI.wavelength, detector=pFAI.detector)
                    self.integrator = pygix.Transform(**calib_pars)
                    self.integrator.sample_orientation = 3  # 1 is horizontal, 2 is vertical
                    self.integrator.incident_angle = 1  # incident angle in deg
                    self.integrator.tilt_angle = 0  # tilt angle of sample in deg (misalignment in "chi")
                    print(f'arch > EwaldArch: self.integrator = {self.integrator}')

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
                    **args
                )

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

    def save_to_h5(self, file, compression='lzf'):
        """Saves data to hdf5 file using h5py as backend.

        args:
            file: h5py group or file object.

        returns:
            None
        """
        with self.file_lock:
            if str(self.idx) in file:
                grp = file[str(self.idx)]
            else:
                grp = file.create_group(str(self.idx))
            grp.attrs['type'] = 'EwaldArch'
            lst_attr = [
                "map_raw", "mask", "map_norm", "scan_info", "ai_args",
                "gi", "static"
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

    def load_from_h5(self, file):
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
                                "map_raw", "mask", "map_norm", "scan_info", 
                                "ai_args", "gi", "static"
                            ]
                            utils.h5_to_attributes(self, grp, lst_attr)
                            self.int_1d.from_hdf5(grp['int_1d'])
                            self.int_2d.from_hdf5(grp['int_2d'])
                            self.poni = PONI.from_yamdict(
                                utils.h5_to_dict(grp['poni'])
                            )

                            if self.poni_file is not None:
                                if not self.gi:
                                    self.integrator = pyFAI.load(poni_file)
                                    self.integrator._rot3 -= np.deg2rad(90)
                                else:
                                    pFAI = pyFAI.load(poni_file)
                                    calib_pars = dict(
                                        dist=pFAI.dist, poni1=pFAI.poni1, poni2=pFAI.poni2,
                                        rot1=pFAI.rot1, rot2=pFAI.rot2, rot3=pFAI.rot3,
                                        wavelength=pFAI.wavelength, detector=pFAI.detector)
                                    self.integrator = pygix.Transform(**calib_pars)
                                    self.integrator.sample_orientation = 3  # 1 is horizontal, 2 is vertical
                                    self.integrator.incident_angle = 1  # incident angle in deg
                                    self.integrator.tilt_angle = 0  # tilt angle of sample in deg (misalignment in "chi")
                                    print(f'arch > EwaldArch: self.integrator = {self.integrator}')

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

    def copy(self):
        """Returns a copy of self.
        """
        arch_copy = EwaldArch(
            copy.deepcopy(self.idx), copy.deepcopy(self.map_raw),
            copy.deepcopy(self.poni), copy.deepcopy(self.mask),
            copy.deepcopy(self.scan_info), copy.deepcopy(self.ai_args),
            self.file_lock, copy.deepcopy(self.poni_file)
        )
        arch_copy.integrator = copy.deepcopy(self.integrator)
        arch_copy.arch_lock = Condition()
        arch_copy.map_norm = copy.deepcopy(self.map_norm)
        arch_copy.int_1d = copy.deepcopy(self.int_1d)
        arch_copy.int_2d = copy.deepcopy(self.int_2d)

        return arch_copy
