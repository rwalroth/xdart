import os
from functools import partial

import h5py
from paws.plugins.ewald import EwaldSphere

from PyQt5.QtWidgets import QWidget, QSizePolicy, QFileDialog
from .tthetaUI import Ui_Form
from .h5viewer import H5Viewer
from .plot_frame_widget import plotFrameWidget

class tthetaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file = None
        self.fname = None
        self.sphere = None
        self.arch = None

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.h5viewer = H5Viewer(self.file, self.fname, self.ui.hdf5Frame)
        self.h5viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.h5viewer.toolbar.actionTriggered.connect(self.h5toolbar)
        self.ui.hdf5Frame.setLayout(self.h5viewer.layout)

        self.plotframe = plotFrameWidget(parent=self.ui.middleFrame)
        self.ui.middleFrame.setLayout(self.plotframe.ui.layout)

        self.h5viewer.tree.itemDoubleClicked.connect(self.load_and_set)
        self.h5viewer.tree.itemClicked.connect(self.set_data)

        self.show()
    
    def update_file(self, fname):
        self.fname = fname

        if self.file is None:
            try:
                self.file = h5py.File(self.fname, 'a')
            except Exception as e:
                print(e)
        else:
            try:
                self.file.close()
                self.file = h5py.File(self.fname, 'a')
            except Exception as e:
                print(e)
        self.h5viewer.fname = self.fname
        self.h5viewer.file = self.file
        self.h5viewer.tree_top.setText(0, os.path.basename(fname))
        self.h5viewer.update(self.file)
    
    def load_sphere(self, name):
        if self.sphere is None:
            self.sphere = EwaldSphere(name)
        
        elif self.sphere.name != name:
            self.sphere = EwaldSphere(name)
        
        self.sphere.load_from_h5(self.file)
        self.plotframe.sphere = self.sphere

    def set_data(self, q, col):
        if self.sphere is None:
            return
        
        elif type(q.data(col, 0)) == int:
            self.arch = q.data(col, 0)
            self.plotframe.arch = q.data(col, 0)
            if self.sphere.name == q.parent().data(0, 0):
                self.plotframe.update()
                self.plotframe.ui.imageIntRaw.setEnabled(True)
                self.plotframe.ui.imageMethod.setEnabled(False)
                self.plotframe.ui.imageMask.setEnabled(True)
        
        elif self.sphere.name == q.data(col, 0):
            self.arch = q.data(col, 0)
            self.plotframe.arch = None
            self.plotframe.update()
            self.plotframe.ui.imageIntRaw.setEnabled(False)
            self.plotframe.ui.imageMethod.setEnabled(True)
            self.plotframe.ui.imageMask.setEnabled(False)

    def load_and_set(self, q, col):
        if type(q.data(col, 0)) == int:
            if 'scan' in q.parent().data(0, 0):
                self.load_sphere(q.parent().data(0, 0))

        elif 'scan' in q.data(col, 0):
            self.load_sphere(q.data(col, 0))
        
        self.set_data(q, col)
    
    def close(self):
        if self.file is not None:
            self.file.close()
        del(self.sphere)
        del(self.plotframe.sphere)
        del(self.arch)
        del(self.plotframe.arch)
        super().close()
    
    def h5toolbar(self, q):
        if q.text() == 'Open':
            fname, _ = QFileDialog().getOpenFileName()
            self.update_file(fname)
    
        
