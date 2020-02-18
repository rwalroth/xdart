# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 14:21:58 2019

@author: walroth
"""
import copy
from threading import Condition
import tempfile

from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
from pyFAI import units
import numpy as np
import h5py

from ... import utils
from ...containers import PONI, int_1d_data, int_2d_data


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
        idx: integer name of arch
        map_raw: numpy 2d array of the unprocessed image data
        poni: poni data for integration
        mask: map of pixels to be masked out of integration
        scan_info: information from any relevant motors and sensors
        ai_args: arguments passed to AzimuthalIntegrator
        file_lock: lock to ensure only one writer to data file
        integrator: AzimuthalIntegrator object from pyFAI
        arch_lock: threading lock used to ensure only one process can
            access data at a time
        map_norm: normalized image data
        int_1d: int_1d_data object from containers
        int_2d: int_2d_data object from containers

    Methods:
        integrate_1d: integrate the image data to create I, 2theta, q,
            and normalization arrays
        integrate_2d: not implemented
        set_integrator: set new integrator
        set_map_raw: replace raw data
        set_poni: replace poni object
        set_mask: replace mask data
        set_scan_info: replace scan_info
        save_to_h5: save data to hdf5 file
        load_from_h5: load data from hdf5 file
        copy: create copy of arch
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, grp=None, idx=-1, map_raw=None, poni=PONI(), mask=None,
                 scan_info={}, ai_args={}, file_lock=Condition(),
                 compression='lzf'):
        # pylint: disable=too-many-arguments
        self.idx = idx
        self.compression = compression
        if grp is None:
            self._file = tempfile.TemporaryFile()
            self._h5py = h5py.File(self._file, mode='a')
            self._grp = self._h5py.create_group(str(self.idx))
        else:
            self._grp = grp
        if self._grp.attrs.get('encoded', 'not_found') == 'ewald_arch':
            self.from_h5()
        else:
            self.map_raw = map_raw
            self.poni = poni
            if mask is None and map_raw is not None:
                self.mask = np.arange(map_raw.size)[map_raw.flatten() < 0]
            else:
                self.mask = mask
            self.scan_info = scan_info
            self.ai_args = ai_args
            self.map_norm = 1
            int_1d = self._grp.create_group('int_1d')
            self.int_1d = int_1d_data(grp=int_1d)
            int_2d = self._grp.create_group('int_2d')
            self.int_2d = int_2d_data(int_2d)
            self._grp.attrs['encoded'] = 'ewald_arch'
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
        self.arch_lock = Condition()
        self.file_lock = file_lock
    
    def from_h5(self):
        for name in ['map_raw', 'mask', 'map_norm']:
            self.__dict__[name] = self._grp[name]
        for name in ['ai_args', 'scan_info']:
            self.__dict__[name] = utils.h5_to_dict(self._grp[name])
        self.__dict__['poni'] = PONI.from_dict(
            utils.h5_to_dict(self._grp[name])
        )
        self.int_1d = int_1d_data(self._grp['int_1d'])
        self.int_2d = int_2d_data(self._grp['int_2d'])
    
    def __setattr__(self, name, value):
        if name == 'map_raw':
            self._setarray(name, value, 2)
        elif name == 'mask':
            self._setarray(name, value, 1)
        elif name == 'map_norm':
            utils.scalar_to_h5(value, self._grp, name)
            self.__dict__[name] = self._grp[name]
        elif name in ['ai_args', 'poni', 'scan_info']:
            self._setdict(name, value)
        else:
            self.__dict__[name] = value
    
    def _setarray(self, name, arr, dim):
        if arr is None:
            if dim == 1:
                arrn = np.array([0])
            elif dim == 2:
                arrn = np.array([[0],[0]])
        else:
            arrn = arr
        if name not in self._grp:
            self.__dict__[name] = self._grp.create_dataset(
                name, data=arrn, chunks=True, compression=self.compression,
                maxshape=tuple(None for x in range(dim))
            )
        else:
            self._grp[name].resize(arrn.shape)
            self._grp[name][()] = arrn[()]
            self.__dict__[name] = self._grp[name]
    
    def _setdict(self, name, data):
        if name == 'poni':
            data_dict = data.to_dict()
        else:
            data_dict = data
        utils.dict_to_h5(data_dict, self._grp, name,
                         compression=self.compression)
        self.__dict__[name] = copy.deepcopy(data)
    
    def __getattribute__(self, name):
        if name in ['map_raw', 'mask', 'map_norm']:
            return self._grp[name][()]
        else:
            return object.__getattribute__(self, name)
    
    def get_mask(self):
        mask = np.zeros(self.map_raw.size, dtype=int)
        mask[self.mask] = 1
        return mask.reshape(self.map_raw.shape)

    def integrate_1d(self, numpoints=10000, radial_range=[0, 180],
                     monitor=None, unit=units.TTH_DEG, **kwargs):
        """Wrapper for integrate1d method of AzimuthalIntegrator from pyFAI.
        Sets 1d integration variables for object instance.

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
                self.map_raw/self.map_norm, numpoints, unit=unit, 
                radial_range=list(radial_range), mask=self.get_mask(), **kwargs
            )

            self.int_1d.from_result(result, self.poni.wavelength)
        return result

    def integrate_2d(self, npt_rad=1000, npt_azim=1000, monitor=None,
                     radial_range=[0,180], azimuth_range=[-180,180], 
                     unit=units.TTH_DEG, **kwargs):
        """Wrapper for integrate2d method of AzimuthalIntegrator from pyFAI.
        Sets 2d integration variables for object instance.

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
            result: integrate1d result from pyFAI.
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
                mask=self.get_mask(), radial_range=list(radial_range), 
                azimuth_range=list(azimuth_range), **kwargs
            )

            self.int_2d.from_result(result, self.poni.wavelength)
        return result
            

    def set_integrator(self, **args):
        """Sets AzimuthalIntegrator with new arguments and instances poni
        attribute.

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
            self._setarray('map_raw', new_data, 2)
            if self.mask is None:
                mask = np.arange(new_data.size)[new_data.flatten() < 0]
                self._setarray('mask', mask, 1)

    def set_poni(self, new_data):
        with self.arch_lock:
            self._setdict('poni', new_data)

    def set_mask(self, new_data):
        with self.arch_lock:
            self._setarray('mask', new_data, 1)

    def set_scan_info(self, new_data):
        with self.arch_lock:
            self._setdict('scan_info', new_data)

    def save_to_h5(self, file, compression='lzf'):
        """Saves data to hdf5 file using h5py as backend.

        args:
            file: h5py group or file object.

        returns:
            None
        """
        with self.file_lock:
            if str(self.idx) in file:
                del(file[str(self.idx)])
            grp = file.create_group(str(self.idx))
            grp.attrs['type'] = 'EwaldArch'
            lst_attr = [
                "map_raw", "mask", "map_norm", "scan_info", "ai_args"
            ]
            utils.attributes_to_h5(self, grp, lst_attr, 
                                       compression=compression)
            grp.create_group('int_1d')
            self.int_1d.to_hdf5(grp['int_1d'], compression)
            grp.create_group('int_2d')
            self.int_2d.to_hdf5(grp['int_2d'], compression)
            grp.create_group('poni')
            utils.dict_to_h5(self.poni.to_dict(), grp['poni'], 'poni')

    def load_from_h5(self, file):
        """Loads data from hdf5 file and sets attributes.

        args:
            file: h5py file or group object

        returns:
            None
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
        arch_copy = EwaldArch(
            None, copy.deepcopy(self.idx), copy.deepcopy(self.map_raw),
            copy.deepcopy(self.poni), copy.deepcopy(self.mask),
            copy.deepcopy(self.scan_info), copy.deepcopy(self.ai_args),
            self.file_lock
        )
        arch_copy.integrator = copy.deepcopy(self.integrator)
        arch_copy.arch_lock = Condition()
        arch_copy.map_norm = copy.deepcopy(self.map_norm)
        del(arch_copy._grp['int_1d'])
        del(arch_copy._grp['int_2d'])
        self.int_1d._grp.copy(self.int_1d._grp, arch_copy._grp)
        arch_copy.int_1d = int_1d_data(arch_copy._grp['int_1d'])
        self.int_2d._grp.copy(self.int_2d._grp, arch_copy._grp)
        arch_copy.int_2d = int_2d_data(arch_copy._grp['int_2d'])

        return arch_copy
