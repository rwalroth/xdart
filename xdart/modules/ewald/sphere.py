from threading import Condition, _PyRLock
import os
from pathlib import Path
import pandas as pd
import numpy as np
from pyFAI.multi_geometry import MultiGeometry

from .arch import EwaldArch
from .arch_series import ArchSeries
from xdart.utils.containers import int_1d_data, int_2d_data
from xdart.utils.containers import int_1d_data_static, int_2d_data_static
from xdart import utils

# from icecream import ic; ic.configureOutput(prefix='', includeContext=True)


class EwaldSphere:
    """Class for storing multiple arch objects, and stores a MultiGeometry
    integrator from pyFAI.

    Attributes:
        arches: ArchSeries, list of arches indexed by their idx value
        bai_1d: int_1d_data object, stores result of 1d integration
        bai_1d_args: dict, arguments for invidivual arch integrate1d
            method
        bai_2d: int_2d_data object, stores result of 2d integration
        bai_2d_args: dict, arguments for invidivual arch integrate2d
            method
        data_file: str, file to save data to
        file_lock: lock for ensuring one writer to hdf5 file
        mg_args: arguments for MultiGeometry constructor
        mgi_1d: int_1d_data object, stores result from multigeometry
            integrate1d method
        mgi_2d: int_2d_data object, stores result from multigeometry
            integrate2d method
        multi_geo: MultiGeometry instance
        name: str, name of the sphere
        scan_data: DataFrame, stores all scan metadata
        sphere_lock: lock for modifying data in sphere

    Methods:
        add_arch: adds new arch and optionally updates other data
        by_arch_integrate_1d: Runs 1 dimensional integration of each
            arch individually and sums the result, stored in bai_1d
        by_arch_integrate_2d: Runs 2 dimensional integration of each
            arch individually and sums the result, stored in bai_2d
        load_from_h5: loads data from hdf5 file
        set_multi_geo: sets the MultiGeometry instance
        multigeometry_integrate_1d: wrapper for MultiGeometry
            integrate1d method, result stored in mgi_1d
        multigeometry_integrate_2d: wrapper for MultiGeometry
            integrate2d method, result stored in mgi_2d
        save_bai_1d: Saves only bai_1d to the data_file
        save_bai_2d: Saves only bai_2d to the data_file
        save_to_h5: saves data to hdf5 file
        set_multi_geo: instatiates the multigeometry object, or
            overrides it if it already exists.
    """

    def __init__(self, name='scan0', arches=[], data_file=None,
                 scan_data=pd.DataFrame(), mg_args={'wavelength': 1e-10},
                 bai_1d_args={}, bai_2d_args={},
                 static=False, gi=False, th_mtr='th',
                 overall_raw=0, single_img=False,
                 global_mask=None, poni_dict={}
                 ):
        """name: string, name of sphere object.
        arches: list of EwaldArch object, data to intialize with
        data_file: str, path to hdf5 file where data is stored
        scan_data: DataFrame, scan metadata
        mg_args: dict, arguments for Multigeometry. Must include at
            least 'wavelength' attribute in Angstroems
        bai_1d_args: dict, arguments for the integrate1d method of pyFAI
            AzimuthalIntegrator
        bai_2d_args: dict, arguments for the integrate2d method of pyFAI
            AzimuthalIntegrator
        """
        super().__init__()
        self.file_lock = Condition()
        if name is None:
            self.name = os.path.split(data_file)[-1].split('.')[0]
        else:
            self.name = name
        if data_file is None:
            self.data_file = name + ".hdf5"
        else:
            self.data_file = data_file

        self.static = static
        self.gi = gi
        self.th_mtr = th_mtr
        self.single_img = single_img

        if arches:
            self.arches = ArchSeries(self.data_file, self.file_lock, arches,
                                     static=self.static, gi=self.gi)
        else:
            self.arches = ArchSeries(self.data_file, self.file_lock,
                                     static=self.static, gi=self.gi)
        self.scan_data = scan_data
        self.mg_args = mg_args
        self.multi_geo = MultiGeometry([a.integrator for a in arches], **mg_args)
        self.bai_1d_args = bai_1d_args
        self.bai_2d_args = bai_2d_args
        self.mgi_1d = int_1d_data()
        self.mgi_2d = int_2d_data()
        self.sphere_lock = Condition(_PyRLock())

        if self.static:
            self.bai_1d = int_1d_data_static()
            self.bai_2d = int_2d_data_static()
        else:
            self.bai_1d = int_1d_data()
            self.bai_2d = int_2d_data()

        self.overall_raw = overall_raw
        self.global_mask = global_mask
        self.poni_dict = poni_dict

    def reset(self):
        """Resets all held data objects to blank state, called when all
        new data is going to be loaded or when a sphere needs to be
        purged of old data.
        """
        with self.sphere_lock:
            self.scan_data = pd.DataFrame()
            self.mgi_1d = int_1d_data()
            self.mgi_2d = int_2d_data()
            self.arches = ArchSeries(self.data_file, self.file_lock,
                                     static=self.static, gi=self.gi)
            self.global_mask = None
            if self.static:
                self.bai_1d = int_1d_data_static()
                self.bai_2d = int_2d_data_static()
            else:
                self.bai_1d = int_1d_data()
                self.bai_2d = int_2d_data()
            self.overall_raw = 0

    def add_arch(self, arch=None, calculate=True, update=True, get_sd=True,
                 set_mg=True, **kwargs):
        """Adds new arch to sphere.

        args:
            arch: EwaldArch instance, arch to be added. Recommended to
                always pass a copy of an arch with the arch.copy method
                or intialize with kwargs
            calculate: whether to run the arch's calculate methods after
                adding
            update: bool, if True updates the bai_1d and bai_2d
                attributes
            get_sd: bool, if True tries to get scan data from arch
            set_mg: bool, if True sets the MultiGeometry attribute.
                Takes a long time, especially with longer lists.
                Recommended to run set_multi_geo method after all arches
                are loaded.
            kwargs: If arch is None, used to intialize the EwaldArch,
                see EwaldArch for arguments.

        returns None
        """
        with self.sphere_lock:
            if arch is None:
                arch = EwaldArch(**kwargs)
            if calculate:
                arch.integrate_1d(global_mask=self.global_mask, **self.bai_1d_args)
                arch.integrate_2d(global_mask=self.global_mask, **self.bai_2d_args)
            arch.file_lock = self.file_lock
            self.arches = self.arches.append(pd.Series(arch, index=[arch.idx]))
            self.arches.sort_index(inplace=True)

            if arch.scan_info and get_sd:
                ser = pd.Series(arch.scan_info, dtype='float64')
                if list(self.scan_data.columns):
                    try:
                        self.scan_data.loc[arch.idx] = ser
                    except ValueError:
                        print('Mismatched columns')
                else:
                    self.scan_data = pd.DataFrame(
                        arch.scan_info, index=[arch.idx], dtype='float64'
                    )
                self.scan_data.sort_index(inplace=True)
                with self.file_lock:
                    with utils.catch_h5py_file(self.data_file, 'a') as file:
                        compression = 'lzf'
                        if self.static:
                            compression = None
                        utils.dataframe_to_h5(self.scan_data, file,
                                              'scan_data', compression)
            if update:
                self._update_bai_1d(arch)
                self._update_bai_2d(arch)
            if set_mg:
                self.multi_geo = MultiGeometry(
                    [a.integrator for a in self.arches], **self.mg_args
                )

            self.overall_raw += (arch.map_raw - arch.bg_raw)

    def by_arch_integrate_1d(self, **args):
        """Integrates all arches individually, then sums the results for
        the overall integration result.

        args: see EwaldArch.integrate_1d. If any args are passed, the
            bai_1d_args dictionary is also updated with the new args.
            If no args are passed, uses bai_1d_args attribute.
        """
        if not args:
            args = self.bai_1d_args
        else:
            self.bai_1d_args = args.copy()
        with self.sphere_lock:
            if self.static:
                self.bai_1d = int_1d_data_static()
            else:
                self.bai_1d = int_1d_data()

            for arch in self.arches:
                arch.integrate_1d(global_mask=self.global_mask, **args)
                self.arches[arch.idx] = arch
                self._update_bai_1d(arch)

    def by_arch_integrate_2d(self, **args):
        """Integrates all arches individually, then sums the results for
        the overall integration result.

        args: see EwaldArch.integrate_2d. If any args are passed, the
            bai_2d_args dictionary is also updated with the new args.
            If no args are passed, uses bai_2d_args attribute.
        """
        if not args:
            args = self.bai_2d_args
        else:
            self.bai_2d_args = args.copy()
        with self.sphere_lock:
            if self.static:
                self.bai_2d = int_2d_data_static()
            else:
                self.bai_2d = int_2d_data()

            for arch in self.arches:
                arch.integrate_2d(global_mask=self.global_mask, **args)
                self.arches[arch.idx] = arch
                self._update_bai_2d(arch)

    def _update_bai_1d(self, arch):
        """helper function to update overall bai variables.
        """
        with self.sphere_lock:
            try:
                assert list(self.bai_1d.raw.shape) == list(arch.int_1d.raw.shape)
            except (AssertionError, AttributeError):
                if not self.static:
                    self.bai_1d.raw = np.zeros(arch.int_1d.raw.shape)
                    self.bai_1d.pcount = np.zeros(arch.int_1d.pcount.shape)
                self.bai_1d.norm = np.zeros(arch.int_1d.norm.shape)
                self.bai_1d.sigma = np.zeros(arch.int_1d.norm.shape)
                self.bai_1d.sigma_raw = np.zeros(arch.int_1d.norm.shape)
            try:
                self.bai_1d += arch.int_1d
                self.bai_1d.ttheta = arch.int_1d.ttheta
                self.bai_1d.q = arch.int_1d.q
            except AttributeError:
                pass
            self.save_bai_1d()

    def _update_bai_2d(self, arch):
        """helper function to update overall bai variables.
        """
        with self.sphere_lock:
            try:
                # assert self.bai_2d.raw.shape == arch.int_2d.raw.shape
                if self.static:
                    assert self.bai_2d.i_qChi.shape == arch.int_2d.i_qChi.shape
                else:
                    assert self.bai_2d.norm.shape == arch.int_2d.norm.shape
            except (AssertionError, AttributeError):
                if self.static:
                    self.bai_2d.i_qChi = np.zeros(arch.int_2d.i_qChi.shape)
                    self.bai_2d.i_tthChi = np.zeros(arch.int_2d.i_tthChi.shape)
                    self.bai_2d.i_QxyQz = np.zeros(arch.int_2d.i_QxyQz.shape)
                else:
                    self.bai_2d.norm = np.zeros(arch.int_2d.norm.shape)
                    self.bai_2d.raw = np.zeros(arch.int_2d.raw.shape)
                    self.bai_2d.pcount = np.zeros(arch.int_2d.pcount.shape)
                    self.bai_2d.sigma = np.zeros(arch.int_2d.norm.shape)
                    self.bai_2d.sigma_raw = np.zeros(arch.int_2d.norm.shape)
            try:
                self.bai_2d.ttheta = arch.int_2d.ttheta
                self.bai_2d.q = arch.int_2d.q
                self.bai_2d.chi = arch.int_2d.chi
                if not self.static:
                    self.bai_2d += arch.int_2d
                else:
                    self.bai_2d.i_qChi += arch.int_2d.i_qChi
                    self.bai_2d.i_tthChi += arch.int_2d.i_tthChi
                    self.bai_2d.i_QxyQz += arch.int_2d.i_QxyQz
                    self.bai_2d.qz = arch.int_2d.qz
                    self.bai_2d.qxy = arch.int_2d.qxy
            except AttributeError:
                pass
            self.save_bai_2d()

    def set_multi_geo(self, **args):
        """Sets the MultiGeometry instance stored in the arch.

        args: see pyFAI.multiple_geometry.MultiGeometry. If no args are
            passed, uses mg_args attribute. Otherwise, updates
            mg_args and uses passed arguments.
        """
        self.mg_args.update(args)
        with self.sphere_lock:
            self.multi_geo = MultiGeometry(
                [a.integrator for a in self.arches], **self.mg_args
            )

    def multigeometry_integrate_1d(self, monitor=None, **kwargs):
        """Wrapper for integrate1d method of MultiGeometry.

        args:
            monitor: channel with normalization value
            kwargs: see MultiGeometry.integrate1d

        returns:
            result: result from MultiGeometry.integrate1d
        """
        with self.sphere_lock:
            lst_mask = [a.get_mask() for a in self.arches]
            if monitor is None:
                try:
                    result = self.multi_geo.integrate1d(
                        [a.map_norm for a in self.arches], lst_mask=lst_mask,
                        **kwargs
                    )
                except Exception as e:
                    print(e)
                    print('Exception 1')
                    result = self.multi_geo.integrate1d(
                        [a.map_raw for a in self.arches], lst_mask=lst_mask,
                        **kwargs
                    )
            else:
                result = self.multi_geo.integrate1d(
                    [a.map_raw for a in self.arches], lst_mask=lst_mask,
                    normalization_factor=list(self.scan_data[monitor]),
                    **kwargs
                )

            self.mgi_1d.from_result(result, self.multi_geo.wavelength)
        return result

    def multigeometry_integrate_2d(self, monitor=None, **kwargs):
        """Wrapper for integrate1d method of MultiGeometry.

        args:
            monitor: channel with normalization value
            kwargs: see MultiGeometry.integrate1d

        returns:
            result: result from MultiGeometry.integrate1d
        """
        with self.sphere_lock:
            lst_mask = [a.get_mask() for a in self.arches]
            if monitor is None:
                try:
                    result = self.multi_geo.integrate2d(
                        [a.map_raw / a.map_norm for a in self.arches], lst_mask=lst_mask,
                        **kwargs
                    )
                except Exception as e:
                    print(e)
                    print('Exception 2')
                    result = self.multi_geo.integrate2d(
                        [a.map_raw for a in self.arches], lst_mask=lst_mask,
                        **kwargs
                    )
            else:
                result = self.multi_geo.integrate2d(
                    [a.map_raw for a in self.arches], lst_mask=lst_mask,
                    normalization_factor=list(self.scan_data[monitor]),
                    **kwargs
                )

            self.mgi_2d.from_result(result, self.multi_geo.wavelength)
        return result

    def save_to_h5(self, replace=False, *args, **kwargs):
        """Saves data to hdf5 file.

        args:
            replace: bool, if True file is truncated prior to writing
                data.
            arches: list, list of arch ids to save. Deprecated.
            data_onle: bool, if true only saves the scan_data attribute
                and does not save mg_args, bai_1d_args, or bai_2d_args.
            compression: str, what compression algorithm to pass to
                h5py. See h5py documentation for acceptable compression
                algorithms.
        """
        if replace:
            mode = 'w'
        else:
            mode = 'a'
        with self.file_lock:
            with utils.catch_h5py_file(self.data_file, mode) as file:
                self._save_to_h5(file, *args, **kwargs)

    def _save_to_h5(self, grp, arches=None, data_only=False,
                    compression='lzf'):
        """Actual function for saving data, run with the file open and
            holding the file_lock.
        """
        if self.static:
            compression = None
        with self.sphere_lock:
            grp.attrs['type'] = 'EwaldSphere'

            if data_only:
                lst_attr = [
                    "scan_data", "global_mask", "overall_raw",
                ]
            else:
                lst_attr = [
                    "scan_data", "global_mask", "mg_args", "bai_1d_args",
                    "bai_2d_args", "overall_raw",
                    "static", "gi", "th_mtr", "single_img", "poni_dict"
                ]
            utils.attributes_to_h5(self, grp, lst_attr,
                                   compression=compression)

            keys = ('bai_1d', 'bai_2d', 'mgi_1d', 'mgi_2d')
            if self.static:
                keys = ('bai_1d', 'bai_2d')
            for key in keys:
                if key not in grp:
                    grp.create_group(key)
            self.bai_1d.to_hdf5(grp['bai_1d'], compression)
            self.bai_2d.to_hdf5(grp['bai_2d'], compression)
            if not self.static:
                self.mgi_1d.to_hdf5(grp['mgi_1d'], compression)
                self.mgi_2d.to_hdf5(grp['mgi_2d'], compression)

    def load_from_h5(self, replace=True, mode='r', *args, **kwargs):
        """Loads data stored in hdf5 file.

        args:
            data_only: bool, if True only loads the scan_data attribute
                and does not load mg_args, bai_1d_args, or bai_2d_args.
            set_mg: bool, if True instantiates the Multigeometry
                object.
        """
        with self.file_lock:
            if replace:
                self.reset()
            with utils.catch_h5py_file(self.data_file, mode=mode) as file:
                self._load_from_h5(file, *args, **kwargs)

    def _load_from_h5(self, grp, data_only=False, set_mg=True):
        """Actual function for loading data, run with the file open and
            holding the file_lock.
        """
        with self.sphere_lock:
            if 'type' in grp.attrs:
                if grp.attrs['type'] == 'EwaldSphere':
                    for arch in grp['arches']:
                        if int(arch) not in self.arches.index:
                            self.arches.index.append(int(arch))

                    self.arches.sort_index(inplace=True)

                    if data_only:
                        lst_attr = [
                            "scan_data", "overall_raw",
                        ]
                        utils.h5_to_attributes(self, grp, lst_attr)
                    else:
                        lst_attr = [
                            "scan_data", "mg_args", "bai_1d_args",
                            "bai_2d_args", "overall_raw",
                            "static", "gi", "th_mtr", "single_img", "poni_dict"
                        ]
                        utils.h5_to_attributes(self, grp, lst_attr)
                        self._set_args(self.bai_1d_args)
                        self._set_args(self.bai_2d_args)

                        if not self.static:
                            self._set_args(self.mg_args)
                    if "global_mask" in grp:
                        utils.h5_to_attributes(self, grp, ["global_mask"])
                    else:
                        self.global_mask = None

                    self.bai_1d.from_hdf5(grp['bai_1d'])
                    self.bai_2d.from_hdf5(grp['bai_2d'])
                    if not self.static:
                        self.mgi_1d.from_hdf5(grp['mgi_1d'])
                        self.mgi_2d.from_hdf5(grp['mgi_2d'])
                        if set_mg:
                            self.set_multi_geo(**self.mg_args)

    def set_datafile(self, fname, name=None, keep_current_data=False,
                     save_args={}, load_args={}):
        """Sets the data_file. If file exists and has data, loads in the
        data. Otherwise, creates new file and resets self.

        args:
            fname: str, new data file
            name: str or None, new name. If None, name is obtained from
                fname.
            keep_current_data: bool, if True overwrites any existing
                data in the file. Otherwise, current data is either
                overwritten by data in file or deleted if no data
                exists, except any args dicts which are untouched.
            save_args: dict, arguments to be passed to save_to_h5
            load_args: dict, arguments to be passed to load_from_h5
        """
        with self.sphere_lock:
            self.data_file = fname
            if name is None:
                self.name = os.path.split(fname)[-1].split('.')[0]
            else:
                self.name = name
            if keep_current_data:
                self.save_to_h5(replace=True, **save_args)
            else:
                if os.path.exists(fname):
                    self.load_from_h5(replace=True, **load_args)
                else:
                    self.reset()
                    self.save_to_h5(replace=True, **save_args)

    def save_bai_1d(self, compression='lzf'):
        """Function to save only the bai_1d object.

        args:
            compression: str, what compression algorithm to pass to
                h5py. See h5py documentation for acceptable compression
                algorithms.
        """
        compression = None
        if self.static:
            compression = None
        with self.file_lock:
            with utils.catch_h5py_file(self.data_file, 'a') as file:
                self.bai_1d.to_hdf5(file['bai_1d'], compression=compression)

    def save_bai_2d(self, compression='lzf'):
        """Function to save only the bai_2d object.

        args:
            compression: str, what compression algorithm to pass to
                h5py. See h5py documentation for acceptable compression
                algorithms.
        """
        compression = None
        if self.static:
            compression = None
        with self.file_lock:
            with utils.catch_h5py_file(self.data_file, 'a') as file:
                self.bai_2d.to_hdf5(file['bai_2d'], compression=compression)

    def _set_args(self, args):
        """Ensures any range args are lists.
        """
        for arg in args:
            if 'range' in arg:
                if args[arg] is not None:
                    args[arg] = list(args[arg])


def get_1D_data(h5_file, arch_ids=None, static=True):
    """Loads 1D data from hdf5 file

    args:
        h5_file: hdf5 file with processed data
        arch_ids: arches whose 1D data is loaded
        static: scan type flag

    returns:
        df: Pandas dataframe with integrated 1D data
    """
    h5_file = Path(h5_file)
    scan_name = h5_file.stem
    sphere = EwaldSphere(scan_name, data_file=str(h5_file), static=static)
    sphere.load_from_h5(replace=False, mode='r')

    df1 = pd.DataFrame(columns=('idx', 'intensity', 'tth', 'q'))
    with utils.catch_h5py_file(sphere.data_file, 'r') as file:
        if arch_ids is None:
            arch_ids = sphere.arches.index

        for idx in arch_ids:
            try:
                arch = EwaldArch(idx=idx, static=sphere.static, gi=sphere.gi)
                if str(idx) not in file['arches']:
                    print("No data can be found")
                    continue
                grp = file['arches'][str(idx)]
                if 'type' in grp.attrs:
                    if grp.attrs['type'] == 'EwaldArch':
                        lst_attr = [
                            "scan_info", "ai_args",
                            "gi", "static", "poni_dict"
                        ]
                        utils.h5_to_attributes(arch, grp, lst_attr)
                        arch.int_1d.from_hdf5(grp['int_1d'])

                df1 = df1.append({
                    'idx': idx,
                    'intensity': list(arch.int_1d.norm),
                    'tth': list(arch.int_1d.ttheta),
                    'q': list(arch.int_1d.q)},
                    ignore_index=True
                )
            except KeyError:
                pass

    df1.set_index(df1['idx'], inplace=True)
    df2 = sphere.scan_data
    df2.rename_axis('idx')

    try:
        df = pd.concat([df1, df2.loc[df1.index]], axis=1, join='outer')
    except KeyError:
        df = df1
    return df.set_index(df['idx'])
