# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
from functools import partial
import time

# Other imports
import h5py
from matplotlib import pyplot as plt

# Qt imports
from pyqtgraph import Qt
from PyQt5.QtWidgets import QWidget, QSizePolicy, QFileDialog

# paws imports
from paws.plugins.ewald import EwaldSphere

# This module imports
from .... import utils as ut
from .tthetaUI import Ui_Form
from .h5viewer import H5Viewer
from .display_frame_widget import displayFrameWidget

formats = [
    str(f.data(), encoding='utf-8').lower() for f in
    Qt.QtGui.QImageReader.supportedImageFormats()
]


class tthetaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Data object initialization
        self.file = None
        self.fname = None
        self.sphere = None
        self.arch = None

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # H5Viewer setup
        self.h5viewer = H5Viewer(self.file, self.fname, self.ui.hdf5Frame)
        self.h5viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.hdf5Frame.setLayout(self.h5viewer.layout)
        self.h5viewer.ui.listData.addItem('No data')
        self.h5viewer.ui.listData.setCurrentRow(0)
        self.h5viewer.ui.listScans.addItem('No scans')

        # H5Viewer signal connections
        self.h5viewer.ui.listScans.itemDoubleClicked.connect(self.load_and_set)
        self.h5viewer.ui.listData.itemClicked.connect(self.set_data)
        self.h5viewer.actionOpen.triggered.connect(self.open_file)
        self.h5viewer.actionSaveImage.triggered.connect(self.save_image)
        self.h5viewer.actionSaveArray.triggered.connect(self.save_array)
        self.h5viewer.actionSaveData.triggered.connect(self.save_data)

        # DisplayFrame setup
        self.displayframe = displayFrameWidget(parent=self.ui.middleFrame)
        self.ui.middleFrame.setLayout(self.displayframe.ui.layout)

        # DisplayFrame signal connections
        self.displayframe.ui.pushRight.clicked.connect(self.next_arch)
        self.displayframe.ui.pushLeft.clicked.connect(self.prev_arch)
        self.displayframe.ui.pushRightLast.clicked.connect(self.last_arch)
        self.displayframe.ui.pushLeftLast.clicked.connect(self.first_arch)

        self.show()
    
    def open_file(self):
        """Reads hdf5 file, populates list of scans in h5viewer. 
        Creates persistent h5py file object.
        """
        fname, _ = QFileDialog().getOpenFileName()
        if fname == '':
            return
        
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
        self.h5viewer.update(self.file)
    
    def load_sphere(self, name):
        """Loads EwaldSphere object into memory
        """
        if not isinstance(self.sphere, EwaldSphere):
            self.sphere = EwaldSphere(name)
        
        elif self.sphere.name != name:
            self.sphere = EwaldSphere(name)
        
        self.sphere.load_from_h5(self.file)
        self.displayframe.sphere = self.sphere
        self.h5viewer.set_data(self.sphere)
        self.h5viewer.ui.listData.setCurrentRow(0)

    def set_data(self, q):
        """Updates data in displayframe
        """
        if q.data(0) != 'No data':
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)

            if not isinstance(self.sphere, EwaldSphere):
                return
            
            elif q.data(0) == 'Overall' or 'scan' in q.data(0):
                self.arch = None
                self.displayframe.arch = None
                self.displayframe.update()
                self.displayframe.ui.imageIntRaw.setEnabled(False)
                self.displayframe.ui.imageMethod.setEnabled(True)
                self.displayframe.ui.imageMask.setEnabled(False)
            
            else:
                self.arch = int(q.data(0))
                self.displayframe.arch = int(q.data(0))
                self.displayframe.update()
                self.displayframe.ui.imageIntRaw.setEnabled(True)
                self.displayframe.ui.imageMethod.setEnabled(False)
                self.displayframe.ui.imageMask.setEnabled(True)

    def load_and_set(self, q):
        """Combination of load and setting functions
        """
        if q.data(0) != 'No scans':
            self.h5viewer.ui.listData.clear()
            self.h5viewer.ui.listData.addItem('Loading...')
            Qt.QtGui.QApplication.processEvents()

            self.load_sphere(q.data(0))
            self.set_data(q)
    
    def save_image(self):
        """Saves currently displayed image. Formats are automatically
        grabbed from Qt. Also implements tiff saving.
        """
        filter = "Images ("
        for f in formats:
            filter += "*." + f + " "

        filter += "*.tiff)"

        fname, _ = QFileDialog.getSaveFileName(filter=filter)
        if fname == '':
            return

        name, ext = fname.split('.')
        if ext.lower() in formats:
            self.displayframe.image.save(fname)
        
        elif ext.lower() == 'tiff':
            data = self.displayframe.update_image(self.sphere, self.arch)
            plt.imsave(fname, data.T, cmap='gray')
    
    def save_array(self):
        """Saves currently displayed data. Currently supports .xye
        and .csv.
        """
        fname, _ = QFileDialog.getSaveFileName(
            filter="XRD Files (*.xye *.csv)"
        )
        if fname == '':
            return

        xdata, ydata = self.displayframe.update_plot(self.sphere, self.arch)

        name, ext = fname.split('.')
        if ext.lower() == 'xye':
            ut.write_xye(fname, xdata, ydata)
        
        elif ext.lower() == 'csv':
            ut.write_csv(fname, xdata, ydata)
    
    def save_data(self):
        """Saves all data to hdf5 file.
        """
        if isinstance(self.sphere, EwaldSphere):
            fname, _ = QFileDialog.getSaveFileName(
                filter="HDF5 Files (*.h5 *.hdf5)"
            )
            if fname == '':
                return

            if self.fname == fname:
                self.sphere.save_to_h5(self.file, replace=True)
                self.h5viewer.update(self.file)
            
            else:
                try:
                    with h5py.File(fname, 'a') as f:
                        self.sphere.save_to_h5(f, replace=True)
                except Exception as e:
                    print(e)
    
    def next_arch(self):
        """Advances to next arch in data list, updates displayframe
        """
        if self.arch == self.sphere.arches.iloc[-1].idx or self.arch is None:
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.currentRow() + 1
            )
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)
            self.set_data(self.h5viewer.ui.listData.currentItem())
    
    def prev_arch(self):
        """Goes back one arch in data list, updates displayframe
        """
        if self.arch == self.sphere.arches.iloc[0].idx or self.arch is None:
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.currentRow() - 1
            )
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)
            self.set_data(self.h5viewer.ui.listData.currentItem())
    
    def last_arch(self):
        """Advances to last arch in data list, updates displayframe, and
        set auto_last to True
        """
        if self.arch is None:
            pass

        else: 
            if self.arch == self.sphere.arches.iloc[-1].idx:
                pass

            else:
                self.h5viewer.ui.listData.setCurrentRow(
                    self.h5viewer.ui.listData.count() - 1
                )
                self.set_data(self.h5viewer.ui.listData.currentItem())
        
            self.displayframe.auto_last = True
            self.displayframe.ui.pushRightLast.setEnabled(False)

    def first_arch(self):
        """Goes to first arch in data list, updates displayframe
        """
        if self.arch == self.sphere.arches.iloc[0].idx or self.arch is None:
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(1)
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)
            self.set_data(self.h5viewer.ui.listData.currentItem())
    
    def close(self):
        """Tries a graceful close.
        """
        if self.file is not None:
            self.file.close()
        del(self.sphere)
        del(self.displayframe.sphere)
        del(self.arch)
        del(self.displayframe.arch)
        super().close()


