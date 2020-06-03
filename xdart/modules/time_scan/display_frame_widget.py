# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import traceback

# Other imports
import numpy as np

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt

# This module imports
from .displayFrameUI import Ui_Form
from xdart.gui.gui_utils import RectViewBox, get_rect

class displayFrameWidget(Qt.QtWidgets.QWidget):
    """Widget for displaying 2D image data and 1D plots from EwaldSphere
    objects. 
    
    attributes:
        auto_last: bool, whether to automatically select latest arch
        curve1: pyqtgraph pen, overall data line
        curve2: pyqtgraph pen, individual arch data line
        histogram: pyqtgraph HistogramLUTWidget, used for adjusting min
            and max level for image
        image: pyqtgraph ImageItem, displays the 2D data
        image_plot: pyqtgraph plot, for 2D data
        image_win: pyqtgraph GraphicsLayoutWidget, layout for the 2D
            data
        imageViewBox: RectViewBox, used to set behavior of the image
            plot
        plot: pyqtgraph plot, for 1D data
        plot_layout: QVBoxLayout, for holding the 1D plotting widgets
        plot_win: pyqtgraph GraphicsLayoutWidget, layout for the 1D
            data
        sphere: EwaldSphere, unused.
        ui: Ui_Form from qtdeisgner
    
    methods:
        get_arch_data_2d: Gets 2D data from an arch object
        get_sphere_data_2d: Gets overall 2D data for the sphere
        update: Updates the displayed image and plot
        update_image: Updates image data based on selections
        update_plot: Updates plot data based on selections
    """
    def __init__(self, parent=None, sphere=None):
        _translate = Qt.QtCore.QCoreApplication.translate
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.imageUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))
        self.ui.plotUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))

        # Data object initialization

        # State variable initialization
        self.auto_last = False

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
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
        #self.ui.imageMethod.setCurrentIndex(1)
        #self.ui.imageMethod.setEnabled(False)

        # Binned Image pane setup
        self.binned_layout = Qt.QtWidgets.QHBoxLayout(self.ui.binnedFrame)
        self.binned_layout.setContentsMargins(0, 0, 0, 0)
        self.binned_layout.setSpacing(0)
        self.binned_win = pg.GraphicsLayoutWidget()
        self.binned_layout.addWidget(self.binned_win)
        self.histogram = pg.HistogramLUTWidget(self.binned_win)
        self.binned_layout.addWidget(self.histogram)
        self.binnedViewBox = RectViewBox()
        self.binned_plot = self.binned_win.addPlot(viewBox=self.binnedViewBox)
        self.binned = pg.ImageItem()
        self.binned_plot.addItem(self.binned)
        self.histogram.setImageItem(self.binned)

        # Image pane signal connections
        #self.ui.imageMethod.setCurrentIndex(1)
        #self.ui.imageMethod.setEnabled(False)


        self.plot_layout = Qt.QtWidgets.QVBoxLayout(self.ui.plotFrame)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
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

        # Waterfall Pane Setup
        self.wf_layout = Qt.QtWidgets.QVBoxLayout(self.ui.wfFrame)
        self.wf_layout.setContentsMargins(0, 0, 0, 0)
        self.wf_win = pg.GraphicsLayoutWidget()
        self.wf_layout.addWidget(self.wf_win)
        vb = RectViewBox()
        self.plot = self.wf_win.addPlot(viewBox=vb)
        self.curve1 = self.plot.plot(pen=(50,100,255))
        self.curve2 = self.plot.plot(
            pen=(200,50,50,200), 
            symbolBrush=(200,50,50,200), 
            symbolPen=(0,0,0,0), 
            symbolSize=4
        )
        
        self.ui.plotMethod.setCurrentIndex(1)
        self.ui.plotMethod.setEnabled(False)

        #self.update()
    
    def update(self, sphere, arch=None):
        """Updates image and plot frames based on toolbar options
        """
        # Sets title text
        # if sphere is not None:
            # if arch is None:
            #     self.ui.labelCurrent.setText(sphere.name)
            # else:
            #     self.ui.labelCurrent.setText("Image " + str(arch))

        # if self.ui.shareAxis.isChecked():
        #     self.ui.plotUnit.setCurrentIndex(self.ui.imageUnit.currentIndex())
        #     self.ui.plotUnit.setEnabled(False)
        #     self.plot.setXLink(self.image_plot)
        
        # else:
        self.plot.setXLink(None)
        self.ui.plotUnit.setEnabled(True)
        
        if self.auto_last and sphere is not None:
            arch = sphere.arches.iloc(-1).idx
            # TODO This is breaking link to parent arch, need to revisit
        
        try:
            self.update_image(sphere, arch)
        except Exception as e:
            print(traceback.print_exc())
        try:
            self.update_plot(sphere, arch)
        except Exception as e:
            print(traceback.print_exc())
    
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
        with arc.arch_lock:
            int_data = arc.int_2d
        
        self.ui.imageNRP = 'Normalized'
        if self.ui.imageNorm.currentIndex() == 0:
            data, corners = read_NRP(self.ui.imageNRP, int_data)
            
            rect = get_rect(
                get_xdata(self.ui.imageUnit, int_data)[corners[2]:corners[3]], 
                int_data.chi[corners[0]:corners[1]]
            )
        
        elif self.ui.imageNorm.currentIndex() == 1:
            with arc.arch_lock:
                if self.ui.imageNRP.currentIndex() == 0:
                    if arc.map_norm is None or arc.map_norm == 0:
                        data = arc.map_raw.copy()
                    else:
                        data = arc.map_raw.copy()/arc.map_norm
                else:
                    data = arc.map_raw.copy()
                if self.ui.imageMask.isChecked():
                    data[arc.mask] = 0
            rect = get_rect(
                np.arange(data.shape[0]), 
                np.arange(data.shape[1]),
            )
        
        return data, rect

    def get_sphere_data_2d(self, sphere):
        """Returns data and QRect for data in sphere
        """
        with sphere.sphere_lock:
            int_data = sphere.bai_2d
            # if self.ui.imageMethod.currentIndex() == 0:
            #     int_data = sphere.mgi_2d
            #     if type(int_data.time) == int:
            #         self.ui.imageMethod.setCurrentIndex(1)
            #         int_data = sphere.bai_2d
            # elif self.ui.imageMethod.currentIndex() == 1:
            #     int_data = sphere.bai_2d
        
        self.ui.imageNRP = 'Normalized'
        data, corners = read_NRP(self.ui.imageNRP, int_data)
        
        rect = get_rect(
            get_xdata(self.ui.imageUnit, int_data)[corners[2]:corners[3]], 
            int_data.chi[corners[0]:corners[1]]
        )
        
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
            with sphere.sphere_lock:
                if self.ui.plotMethod.currentIndex() == 0:
                    sphere_int_data = sphere.mgi_1d
                    if type(sphere_int_data.time) == int:
                        self.ui.plotMethod.setCurrentIndex(1)
                        sphere_int_data = sphere.bai_1d
                elif self.ui.plotMethod.currentIndex() == 1:
                    sphere_int_data = sphere.bai_1d
            
            self.ui.plotNRP = 'Normalized'
            s_ydata, corners = read_NRP(self.ui.plotNRP, sphere_int_data)
            s_xdata = get_xdata(self.ui.plotUnit, sphere_int_data)[corners[0]:corners[1]]

            if arch is not None:
                with sphere.arches[arch].arch_lock:
                    arc_int_data = sphere.arches[arch].int_1d

                if self.ui.plotOverlay.isChecked():
                    self.curve1.setData(s_xdata, s_ydata)
                else:
                    self.curve1.clear()
                
                a_ydata, corners = read_NRP(self.ui.plotNRP, arc_int_data)
                a_xdata = get_xdata(self.ui.plotUnit, arc_int_data)[corners[0]:corners[1]]
                self.curve2.setData(a_xdata, a_ydata)

                return a_xdata, a_ydata
            
            else:
                self.curve1.setData(s_xdata, s_ydata)
                self.curve2.clear()

                return s_xdata, s_ydata


def read_NRP(box, int_data):
    """Reads the norm, raw, pcount option box and returns
    appropriate ydata.
    
    args:
        box: QComboBox, list of choices for picking data to return
        int_data: int_nd_data object, data to parse
    
    returns:
        data: numpy array, non-zero region from nzarray based on
            choices in box
        corners: tuple, the bounds of the non-zero region of the
            dataset
    """
    # if box.currentIndex() == 0:
    if box == 'Normalized':
        nzarr = int_data.norm
    elif box.currentIndex() == 1:
        nzarr = int_data.raw
    elif box.currentIndex() == 2:
        nzarr = int_data.pcount
    data = nzarr.data[()].T
    corners = nzarr.corners
    
    if data.size == 0:
        data = np.zeros(int_data.norm.shape)
        if len(corners) == 2:
            corners = [0,int_data.norm.shape[0]]
        if len(corners) == 4:
            corners = [0,int_data.norm.shape[0],0,int_data.norm.shape[1]]
    return data, corners


def get_xdata(box, int_data):
    """Reads the unit box and returns appropriate xdata
    
    args:
        box: QComboBox, list of options
        int_data: int_nd_data object, data to parse
    
    returns:
        xdata: numpy array, x axis data for plot.
    """
    xdata = int_data.q
    return xdata
    
    if box.currentIndex() == 0:
        xdata = int_data.time
    elif box.currentIndex() == 1:
        xdata = int_data.q
    return xdata


