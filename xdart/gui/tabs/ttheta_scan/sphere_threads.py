# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from queue import Queue
from threading import Condition
import traceback
import time

# Other imports
from xdart.utils.containers import int_1d_data, int_2d_data

# Qt imports
from pyqtgraph import Qt

# This module imports
from xdart.utils import catch_h5py_file as catch
from xdart import utils as ut

# from icecream import ic; ic.configureOutput(prefix='', includeContext=True)


class integratorThread(Qt.QtCore.QThread):
    """Thread for handling integration. Frees main gui thread from
    intensive calculations.
    
    attributes:
        arch: int, idx of arch to integrate
        lock: Condition, lock to handle access to thread attributes
        method: str, which method to call in run
        mg_1d_args, mg_2d_args: dict, arguments for multigeometry
            integration
        sphere: EwaldSphere, object that does the integration.
    
    methods:
        bai_1d_all: Calls by arch integration 1D for all arches
        bai_1d_SI: Calls by arch integration 1D for specified arch
        bai_2d_all: Calls by arch integration 2D for all arches
        bai_2d_SI: Calls by arch integration 2D for specified arch
        load: Loads data 
        mg_1d: multigeometry 1d integration
        mg_2d: multigeometry 2d integration
        mg_setup: sets up multigeometry object
        run: main thread method.
        
    signals:
        update: empty, tells parent when new data is ready.
    """
    update = Qt.QtCore.Signal(int)
    def __init__(self, sphere, arch, file_lock, parent=None):
        super().__init__(parent)
        self.sphere = sphere
        self.arch = arch
        self.file_lock = file_lock
        self.method = None
        self.lock = Condition()
        self.mg_1d_args = {}
        self.mg_2d_args = {}
    
    def run(self):
        """Calls self.method. Catches exception where method does
        not match any attributes.
        """
        with self.lock:
            method = getattr(self, self.method)
            try:
                method()
            except KeyError:
                traceback.print_exc()

    def mg_2d(self):
        """Multigeometry integrate 2d.
        """
        self.sphere.multigeometry_integrate_2d(**self.mg_2d_args)

    def mg_1d(self):
        """Multigeometry integrate 1d.
        """
        self.sphere.multigeometry_integrate_1d(**self.mg_1d_args)

    def mg_setup(self):
        """Sets up multigeometry.
        """
        self.sphere.set_multi_geo()

    def bai_2d_all(self):
        """Integrates all arches 2d. Note, does not call sphere method
        directly, handles same functions but broken up for updates
        after each image.
        """
        with self.sphere.sphere_lock:
            self.sphere.bai_2d = int_2d_data()
        for arch in self.sphere.arches:
            arch.integrate_2d(**self.sphere.bai_2d_args, global_mask=self.sphere.global_mask)
            # self.sphere.arches[arch.idx] = arch
            self.sphere._update_bai_2d(arch)
            self.update.emit(arch.idx)
        with self.file_lock:
            with catch(self.sphere.data_file, 'a') as file:
                ut.dict_to_h5(self.sphere.bai_2d_args, file, 'bai_2d_args')

    def bai_2d_SI(self):
        """Integrate the current arch, 2d
        """
        self.arch.integrate_2d(**self.sphere.bai_2d_args, global_mask=self.sphere.global_mask)

    def bai_1d_all(self):
        """Integrates all arches 1d. Note, does not call sphere method
        directly, handles same functions but broken up for updates
        after each image.
        """
        with self.sphere.sphere_lock:
            self.sphere.bai_1d = int_1d_data()
        for arch in self.sphere.arches:
            arch.integrate_1d(**self.sphere.bai_1d_args, global_mask=self.sphere.global_mask)
            # self.sphere.arches[arch.idx] = arch
            self.sphere._update_bai_1d(arch)
            self.update.emit(arch.idx)
        with self.file_lock:
            with catch(self.sphere.data_file, 'a') as file:
                ut.dict_to_h5(self.sphere.bai_1d_args, file, 'bai_1d_args')

    def bai_1d_SI(self):
        """Integrate the current arch, 1d.
        """
        self.arch.integrate_1d(**self.sphere.bai_1d_args, global_mask=self.sphere.global_mask)
    
    def load(self):
        """Load data.
        """
        self.sphere.load_from_h5()


class fileHandlerThread(Qt.QtCore.QThread):
    """Thread class for loading data. Handles locks and waiting for
    locks to be released.
    """
    sigNewFile = Qt.QtCore.Signal(str)
    sigUpdate = Qt.QtCore.Signal()
    sigTaskStarted = Qt.QtCore.Signal()
    sigTaskDone = Qt.QtCore.Signal(str)
    
    def __init__(self, sphere, arch, file_lock, parent=None):
        """
        Parameters
        ----------
        file_lock : multiprocessing.Condition
        arch : xdart.modules.ewald.EwaldArch
        sphere : xdart.modules.ewald.EwaldSphere
        """
        super().__init__(parent)
        self.sphere = sphere
        self.arch = arch
        self.file_lock = file_lock
        self.queue = Queue()
        self.fname = sphere.data_file
        self.new_fname = None
        self.lock = Condition()
        self.running = False
        
    def run(self):
        while True:
            method_name = self.queue.get()
            try:
                self.running = True
                self.sigTaskStarted.emit()
                method = getattr(self, method_name)
                method()
            except KeyError:
                traceback.print_exc()
            self.running = False
            self.sigTaskDone.emit(method_name)
    
    def set_datafile(self):
        with self.file_lock:
            self.sphere.set_datafile(
                self.fname, save_args={'compression': 'lzf'}
            )
        self.sigNewFile.emit(self.fname)
        self.sigUpdate.emit()
    
    def update_sphere(self):
        with self.file_lock:
            self.sphere.load_from_h5(replace=False, data_only=True,
                                     set_mg=False)
    
    def load_arch(self):
        with self.file_lock:
            with catch(self.sphere.data_file, 'r') as file:
                self.arch.load_from_h5(file['arches'])
        self.sigUpdate.emit()
    
    def save_data_as(self):
        if self.new_fname is not None and self.new_fname != "":
            with self.file_lock:
                with catch(self.sphere.data_file, 'r') as f1:
                    with catch(self.new_fname, 'w') as f2:
                        for key in f1:
                            f1.copy(key, f2)
                        for attr in f1.attrs:
                            f2.attrs[attr] = f1.attrs[attr]
        self.new_fname = None
