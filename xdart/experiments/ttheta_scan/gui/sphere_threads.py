# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from threading import Condition

# Other imports
from paws.containers import int_1d_data, int_2d_data

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
    
    def run(self):
        print(self.sphere.bai_1d_args)
        with self.lock:
            if self.method == 'bai_1d_SI':
                self.sphere.arches[self.arch].integrate_1d(**self.sphere.bai_1d_args)
            
            elif self.method == 'bai_1d_all':
                with self.sphere.sphere_lock:
                    self.sphere.bai_1d = int_1d_data()
                for arch in self.sphere.arches:
                    arch.integrate_1d(**self.sphere.bai_1d_args)
                    self.sphere._update_bai_1d(arch)
                    self.update.emit()

            elif self.method == 'bai_2d_SI':
                self.sphere.arches[self.arch].integrate_2d(**self.sphere.bai_2d_args)
            
            elif self.method == 'bai_2d_all':
                with self.sphere.sphere_lock:
                    self.sphere.bai_2d = int_2d_data()
                for arch in self.sphere.arches:
                    arch.integrate_2d(**self.sphere.bai_2d_args)
                    self.sphere._update_bai_2d(arch)
                    self.update.emit()
                

