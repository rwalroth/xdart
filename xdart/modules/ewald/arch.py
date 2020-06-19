# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 14:21:58 2019

@author: walroth
"""
import copy
from threading import Condition

from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from pyFAI import units
import numpy as np

from xdart import utils
from xdart.utils.containers import PONI, int_1d_data, int_2d_data


def parse_unit(result, wavelength):
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
        int_1d: int_1d_data object from containers
        int_2d: int_2d_data object from containers
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
                 scan_info={}, ai_args={}, file_lock=Condition()):
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
        if mask is None and map_raw is not None:
            self.mask = np.arange(map_raw.size)[map_raw.flatten() < 0]
        else:
            self.mask = mask
        self.scan_info = scan_info
        self.ai_args = ai_args
        self.file_lock = file_lock
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
        self.int_1d = int_1d_data()
        self.int_2d = int_2d_data()
    
    def reset(self):
        """Clears all data, resets to a default EwaldArch.
        """
        self.idx = None
        self.map_raw = None
        self.poni = PONI()
        self.mask = None
        self.scan_info = {}
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
        self.int_1d = int_1d_data()
        self.int_2d = int_2d_data()
    
    def get_mask(self):
        mask = np.zeros(self.map_raw.size, dtype=int)
        mask[self.mask] = 1
        return mask.reshape(self.map_raw.shape)

    def integrate_1d(self, numpoints=10000, radial_range=[0, 180],
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
        with self.arch_lock:
            if monitor is not None:
                self.map_norm = self.scan_info[monitor]
            if self.mask is None:
                self.mask = np.arange(self.map_raw.size)[self.map_raw.flatten() < 0]

            result = self.integrator.integrate1d(
                self.map_raw/self.map_norm, numpoints, unit=unit, radial_range=radial_range,
                mask=self.get_mask(), **kwargs
            )

            self.int_1d.from_result(result, self.poni.wavelength)
        return result

    def integrate_2d(self, npt_rad=1000, npt_azim=1000, monitor=None,
                     radial_range=[0,180], azimuth_range=[-180,180], 
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
        with self.arch_lock:
            if monitor is not None:
                self.map_norm = self.scan_info[monitor]
                
            if self.mask is None:
                self.mask = np.arange(self.map_raw.size)[self.map_raw.flatten() < 0]
            
            if npt_rad is None:
                npt_rad = self.map_raw.shape[0]
            
            if npt_azim is None:
                npt_azim = self.map_raw.shape[1]

            result = self.integrator.integrate2d(
                self.map_raw/self.map_norm, npt_rad, npt_azim, unit=unit, 
                mask=self.get_mask(), radial_range=radial_range, 
                azimuth_range=azimuth_range, **kwargs
            )

            self.int_2d.from_result(result, self.poni.wavelength)
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
                "map_raw", "mask", "map_norm", "scan_info", "ai_args"
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
                                "ai_args"
                            ]
                            utils.h5_to_attributes(self, grp, lst_attr)
                            self.int_1d.from_hdf5(grp['int_1d'])
                            self.int_2d.from_hdf5(grp['int_2d'])
                            self.poni = PONI.from_yamdict(
                                utils.h5_to_dict(grp['poni'])
                            )
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
            self.file_lock
        )
        arch_copy.integrator = copy.deepcopy(self.integrator)
        arch_copy.arch_lock = Condition()
        arch_copy.map_norm = copy.deepcopy(self.map_norm)
        arch_copy.int_1d = copy.deepcopy(self.int_1d)
        arch_copy.int_2d = copy.deepcopy(self.int_2d)

        return arch_copy
