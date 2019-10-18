import os

import h5py

from PyQt5.QtWidgets import QWidget, QSizePolicy, QFileDialog
from .tthetaUI import Ui_Form
from .h5viewer import H5Viewer

class tthetaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file = None
        self.fname = None
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.h5viewer = H5Viewer(self.file, self.fname, self.ui.hdf5Frame)
        self.h5viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.h5viewer.toolbar.actionTriggered.connect(self.h5toolbar)
        self.ui.hdf5Frame.setLayout(self.h5viewer.layout)
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
        self.h5viewer.update_tree(self.file)
    
    def close(self):
        if self.file is not None:
            self.file.close()
    
    def h5toolbar(self, q):
        if q.text() == 'Open':
            fname, _ = QFileDialog().getOpenFileName()
            self.update_file(fname)
    
        
