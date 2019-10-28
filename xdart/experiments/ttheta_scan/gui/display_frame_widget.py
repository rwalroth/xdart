# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os

# Other imports
import numpy as np

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt

# This module imports
from .displayFrameUI import * 
from .gui_utils import *

class displayFrameWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None, sphere=None):
        _translate = QtCore.QCoreApplication.translate
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.imageUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))
        self.ui.plotUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))

        # Data object initialization
        self.sphere = None
        self.arch = None

        # State variable initialization
        self.auto_last = False

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.histogram = pg.HistogramLUTWidget(self.image_win)
        self.image_layout.addWidget(self.histogram)
        self.imageViewBox = RectViewBox()
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        self.image = pg.ImageItem()
        self.image_plot.addItem(self.image)
        self.histogram.setImageItem(self.image)

        # Image pane signal connections
        self.ui.imageIntRaw.activated.connect(self.update)
        self.ui.imageMethod.activated.connect(self.update)
        self.ui.imageUnit.activated.connect(self.update)
        self.ui.imageNRP.activated.connect(self.update)
        self.ui.imageMask.stateChanged.connect(self.update)
        self.ui.shareAxis.stateChanged.connect(self.update)

        self.plot_layout = Qt.QtWidgets.QVBoxLayout(self.ui.plotFrame)
        self.plot_win = pg.GraphicsLayoutWidget()
        self.plot_layout.addWidget(self.plot_win)
        vb = RectViewBox()
        self.plot = self.plot_win.addPlot(viewBox=vb)
        self.curve1 = self.plot.plot(pen=(50,100,255))
        self.curve2 = self.plot.plot(
            pen=(200,50,50,200), 
            symbolBrush=(200,50,50,200), 
            symbolPen=(0,0,0,0), 
            symbolSize=4
        )

        self.ui.plotMethod.activated.connect(self.update)
        self.ui.plotUnit.activated.connect(self.update)
        self.ui.plotNRP.activated.connect(self.update)
        self.ui.plotOverlay.stateChanged.connect(self.update)

        self.update()
    
    def update(self):
        """Updates image and plot frames based on toolbar options
        """
        # Sets title text
        if self.sphere is not None:
            if self.arch is None:
                self.ui.labelCurrent.setText(self.sphere.name)
            else:
                self.ui.labelCurrent.setText("Image " + str(self.arch))

        if self.ui.shareAxis.isChecked():
            self.ui.plotUnit.setCurrentIndex(self.ui.imageUnit.currentIndex())
            self.ui.plotUnit.setEnabled(False)
            self.plot.setXLink(self.image_plot)
        
        else:
            self.plot.setXLink(None)
            self.ui.plotUnit.setEnabled(True)
        
        if self.auto_last and self.sphere is not None:
            self.arch = self.sphere.arches.iloc[-1].idx
            # TODO This is breaking link to parent arch, need to revisit
        
        self.update_image(self.sphere, self.arch)
        self.update_plot(self.sphere, self.arch)
    
    def update_image(self, sphere, arch):
        """Updates image plotted in image frame
        """
        if sphere is None:
            data = np.arange(100).reshape(10,10)
            rect = Qt.QtCore.QRect(1,1,1,1)
        
        elif arch is not None:
            data, rect = self.get_arch_data_2d(sphere, arch)
        
        else:
            data, rect = self.get_sphere_data_2d(sphere)
        
        self.image.setImage(data)
        self.image.setRect(rect)
        
        return data

    def get_arch_data_2d(self, sphere, arch):
        """Returns data and QRect for data in arch
        """
        arc = sphere.arches[arch]
        int_data = arc.int_2d
        
        rect = get_rect(
            self.get_xdata(self.ui.imageUnit, int_data), 
            int_data.chi
        )
        
        if self.ui.imageIntRaw.currentIndex() == 0:
            data = self.read_NRP(self.ui.imageNRP, int_data)
        
        elif self.ui.imageIntRaw.currentIndex() == 1:
            if self.ui.imageNRP.currentIndex() == 0:
                data = arc.map_norm.copy()
            else:
                data = arc.map_raw.copy()
            if self.ui.imageMask.isChecked():
                data *= np.where(arc.mask==1, 0, np.ones_like(arc.mask))
        
        return data, rect

    def get_sphere_data_2d(self, sphere):
        """Returns data and QRect for data in sphere
        """
        if self.ui.imageMethod.currentIndex() == 0:
            int_data = sphere.mgi_2d
            if type(int_data.ttheta) == int:
                self.ui.imageMethod.setCurrentIndex(1)
                int_data = sphere.bai_2d
        elif self.ui.imageMethod.currentIndex() == 1:
            int_data = sphere.bai_2d
        
        rect = get_rect(
            self.get_xdata(self.ui.imageUnit, int_data), 
            int_data.chi
        )
        
        data = self.read_NRP(self.ui.imageNRP, int_data)
        
        return data, rect
    
    def update_plot(self, sphere, arch):
        """Updates data in plot frame
        """
        if sphere is None:
            data = (np.arange(100), np.arange(100))
            self.curve1.setData(data[0], data[1])
            self.curve2.setData(data[0], data[1])
            return data
        
        else:
            if self.ui.plotMethod.currentIndex() == 0:
                sphere_int_data = sphere.mgi_1d
                if type(sphere_int_data.ttheta) == int:
                    self.ui.plotMethod.setCurrentIndex(1)
                    sphere_int_data = sphere.bai_1d
            elif self.ui.plotMethod.currentIndex() == 1:
                sphere_int_data = sphere.bai_1d
            
            s_ydata = self.read_NRP(self.ui.plotNRP, sphere_int_data)
            xdata = self.get_xdata(self.ui.plotUnit, sphere_int_data)

            if arch is not None:
                arc_int_data = sphere.arches[arch].int_1d

                if self.ui.plotOverlay.isChecked():
                    self.curve1.setData(*return_no_zero(xdata, s_ydata))
                else:
                    self.curve1.clear()
                
                a_ydata = self.read_NRP(self.ui.plotNRP, arc_int_data)
                self.curve2.setData(*return_no_zero(xdata, a_ydata))

                return return_no_zero(xdata, a_ydata)
            
            else:
                self.curve1.setData(*return_no_zero(xdata, s_ydata))
                self.curve2.clear()

                return return_no_zero(xdata, s_ydata)

    def read_NRP(self, box, int_data):
        """Reads the norm, raw, pcount option box and returns
        appropriate ydata
        """
        if box.currentIndex() == 0:
            data = int_data.norm[()].T
        elif box.currentIndex() == 1:
            data = int_data.raw[()].T
        elif box.currentIndex() == 2:
            data = int_data.pcount[()].T
        return data

    def get_xdata(self, box, int_data):
        """Reads the unit box and returns appropriate xdata
        """
        if box.currentIndex() == 0:
            xdata = int_data.ttheta
        elif box.currentIndex() == 1:
            xdata = int_data.q
        return xdata


