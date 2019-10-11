import os
import time
from copy import deepcopy

import h5py

from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

from paws.plugins.ewald import EwaldArch, EwaldSphere
from paws.pawstools import catch_h5py_file

if __name__ == '__main__':
    from visualizer import *
else:
    from .visualizer import *

class TThetaGUI(pg.GraphicsWindow):
    def __init__(self, data_file, scan_name):
        super().__init__()
        self.data_file = data_file
        self.scan_name = scan_name
        try:
            with h5py.File(self.data_file, 'r') as file:
                self.data = get_last_arch(file, self.scan_name)
                self.map_norm, self.tth, self.all_norm, self.arch_int_norm = self.data
        except (KeyError, ValueError, OSError, RuntimeError):
            self.data = (
                np.arange(100).reshape(10,10),
                np.arange(100),
                np.arange(100),
                np.arange(100)
            )
            self.map_norm, self.tth, self.all_norm, self.arch_int_norm = self.data
        self.p1 = self.addPlot(title="Integrated Data")
        self.curve = self.p1.plot(pen=(50,100,255))
        self.curve2 = self.p1.plot(
            pen=(200,50,50,200), 
            symbolBrush=(200,50,50,200), 
            symbolPen=(0,0,0,0), 
            symbolSize=4
        )

        self.nextRow()
        self.p2 = self.addPlot()
        self.img = pg.ImageItem()
        self.p2.addItem(self.img)

        self.ptr = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(100)

    def update(self):
        try:
            with h5py.File(self.data_file, 'r') as file:
                data = get_last_arch(file, self.scan_name)
            self.map_norm, self.tth, self.all_norm, self.arch_int_norm = deepcopy(data)
            self.data = deepcopy(data)
        except (KeyError, ValueError, OSError, RuntimeError):
            self.map_norm, self.tth, self.all_norm, self.arch_int_norm = self.data
        self.curve.setData(self.tth[self.all_norm > 0], self.all_norm[self.all_norm > 0])
        self.curve2.setData(self.tth[self.arch_int_norm > 0], self.arch_int_norm[self.arch_int_norm > 0])
        self.img.setImage(self.map_norm)
        if self.ptr == 0:
            self.p1.enableAutoRange('xy', False)
        self.ptr += 1
        

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    data_file = r"C:\Users\walroth\OneDrive - SLAC National Accelerator Laboratory\out_dir\test.h5"
    win = TThetaGUI(data_file, 'scan02')
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()