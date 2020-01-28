# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from threading import Condition

# Other imports
from xdart.containers import int_1d_data, int_2d_data
from xdart.classes.ewald import EwaldArch, EwaldSphere
from xdart.containers import PONI

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt

# This module imports

class integratorThread(Qt.QtCore.QThread):
    update = Qt.QtCore.Signal()
    def __init__(self, sphere, arch, parent=None):
        super().__init__(parent)
        self.sphere = sphere
        self.arch = arch
        self.method = None
        self.lock = Condition()
        self.mg_1d_args = {}
        self.mg_2d_args = {}
    
    def run(self):
        with self.lock:
            method = getattr(self, self.method)
            try:
                method()
            except KeyError:
                pass

    def mg_2d(self):
        self.sphere.multigeometry_integrate_2d(**self.mg_2d_args)

    def mg_1d(self):
        self.sphere.multigeometry_integrate_1d(**self.mg_1d_args)

    def mg_setup(self):
        self.sphere.set_multi_geo()

    def bai_2d_all(self):
        with self.sphere.sphere_lock:
            self.sphere.bai_2d = int_2d_data()
        for arch in self.sphere.arches:
            arch.integrate_2d(**self.sphere.bai_2d_args)
            self.sphere._update_bai_2d(arch)
            self.update.emit()

    def bai_2d_SI(self):
        self.sphere.arches[self.arch].integrate_2d(**self.sphere.bai_2d_args)

    def bai_1d_all(self):
        with self.sphere.sphere_lock:
            self.sphere.bai_1d = int_1d_data()
        for arch in self.sphere.arches:
            arch.integrate_1d(**self.sphere.bai_1d_args)
            self.sphere._update_bai_1d(arch)
            self.update.emit()

    def bai_1d_SI(self):
        self.sphere.arches[self.arch].integrate_1d(**self.sphere.bai_1d_args)
    
    def load(self):
        self.sphere.load_from_h5()
