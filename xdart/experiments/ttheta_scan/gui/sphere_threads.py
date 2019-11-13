# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from threading import Condition

# Other imports
from paws.containers import int_1d_data, int_2d_data
from paws.plugins.ewald import EwaldArch, EwaldSphere
from paws.containers import PONI

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
            method()

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
                

class batchIntegrator(Qt.QtCore.QThread):
    update = Qt.QtCore.Signal()
    def __init__(self, sphere, wrangler, command_q, parent=None):
        super().__init__(parent)
        self.sphere = sphere
        self.command_q = command_q
        self.wrangler = wrangler

    def run(self):
        i = 0
        pause = False
        self.wrangler.cont = True
        while True:
            if not self.command_q.empty() or pause:
                command = self.command_q.get()
                if command == 'stop':
                    self.wrangler.cont = False
                    break
                elif command == 'continue':
                    pause = False
                elif command == 'pause':
                    pause = True
                    continue
            
            flag, data = self.wrangler.wrangle(i)

            if flag == 'image':
                idx, map_raw, scan_info, poni = data
                arch = EwaldArch(
                    idx, map_raw, PONI.from_yamdict(poni), scan_info=scan_info
                )
                self.sphere.add_arch(
                    arch=arch.copy(), calculate=True, update=True, get_sd=True, 
                    set_mg=False
                )
                self.update.emit()
                i += 1
            
            elif flag == 'TERMINATE' and data is None:
                break
