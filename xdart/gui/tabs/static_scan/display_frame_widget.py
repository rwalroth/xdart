# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import traceback

# Other imports
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import cm

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets

# This module imports
from .ui.displayFrameUI import Ui_Form
from ...gui_utils import RectViewBox, get_rect
import xdart.utils as ut

QFileDialog = QtWidgets.QFileDialog

formats = [
    str(f.data(), encoding='utf-8').lower() for f in
    Qt.QtGui.QImageReader.supportedImageFormats()
]

# Switch to using white background and black foreground
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# Define color tuples
viridis = cm.get_cmap('viridis', 256)
colors = viridis(np.linspace(0, 1, 5))

colors = np.round(colors * [255, 255, 255, 1]).astype(int)
colors = [tuple(color[:3]) for color in colors]


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

    def __init__(self, sphere, arch, arch_ids, arches, parent=None):
        _translate = Qt.QtCore.QCoreApplication.translate
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.imageUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))
        self.ui.plotUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))

        # Data object initialization
        self.sphere = sphere
        self.arch = arch
        self.arch_ids = arch_ids
        self.arches = arches

        # State variable initialization
        self.auto_last = True

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.imageViewBox = RectViewBox()
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        self.image = pg.ImageItem()
        self.image_plot.addItem(self.image)
        self.raw_histogram = pg.HistogramLUTWidget(self.image_win)
        self.image_layout.addWidget(self.raw_histogram)
        self.raw_histogram.setImageItem(self.image)

        # Regrouped Image pane setup
        self.binned_layout = Qt.QtWidgets.QHBoxLayout(self.ui.binnedFrame)
        self.binned_layout.setContentsMargins(0, 0, 0, 0)
        self.binned_layout.setSpacing(0)
        self.binned_win = pg.GraphicsLayoutWidget()
        self.binned_layout.addWidget(self.binned_win)
        self.binnedViewBox = RectViewBox()
        self.binned_plot = self.binned_win.addPlot(viewBox=self.binnedViewBox)
        self.binned = pg.ImageItem()
        self.binned_plot.addItem(self.binned)
        self.binned_histogram = pg.HistogramLUTWidget(self.binned_win)
        self.binned_layout.addWidget(self.binned_histogram)
        self.binned_histogram.setImageItem(self.binned)

        # 1D/Waterfall Plot pane setup
        self.plot_layout = Qt.QtWidgets.QVBoxLayout(self.ui.plotFrame)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_win = pg.GraphicsLayoutWidget()
        self.plot_layout.addWidget(self.plot_win)
        vb = RectViewBox()
        self.plot = self.plot_win.addPlot(viewBox=vb)
        self.curves = [self.plot.plot(
            pen=color,
            symbolBrush=color,
            symbolPen=color,
            symbolSize=3
        ) for color in colors]

        # self.ui.plotMethod.setCurrentIndex(1)
        # self.ui.plotMethod.setEnabled(False)

        # 2D Window Signal connections
        self.ui.normChannel.activated.connect(self.update)
        self.ui.imageUnit.activated.connect(self.update_image)
        self.ui.shareAxis.stateChanged.connect(self.update)
        self.ui.imageMask.stateChanged.connect(self.update_image)

        # 1D Window Signal connections
        self.ui.plotScale.currentIndexChanged.connect(self.update_plot)
        self.ui.plotMethod.currentIndexChanged.connect(self.update_plot)
        self.ui.yOffset.valueChanged.connect(self.update_plot)
        self.ui.plotUnit.activated.connect(self.update_plot)

        # self.update()

    def update(self):
        """Updates image and plot frames based on toolbar options
        """
        if len(self.arches) == 0:
            return True

        print(f'\ndisplay_frame_widget > update: self.arch.idx = {self.arch.idx}')
        print(f'display_frame_widget > update: self.arch_ids = {self.arch_ids}')
        # Sets title text
        if self.arch.idx is None:
            self.ui.labelCurrent.setText(self.sphere.name)
        else:
            self.ui.labelCurrent.setText("Image " + str(self.arch.idx))

        if self.ui.shareAxis.isChecked():
            self.ui.plotUnit.setCurrentIndex(self.ui.imageUnit.currentIndex())
            self.ui.plotUnit.setEnabled(False)
            self.plot.setXLink(self.image_plot)
        else:
            self.plot.setXLink(None)
            self.ui.plotUnit.setEnabled(True)

        try:
            self.update_image()
        except TypeError:
            return False
        try:
            self.update_binned()
        except TypeError:
            return False
        try:
            self.update_plot()
        except TypeError:
            return False
        return True

    def update_image(self):
        """Updates image plotted in image frame
        """
        if self.sphere.name == 'null_main':
            data = np.arange(100).reshape(10, 10)
            rect = Qt.QtCore.QRect(1, 1, 1, 1)
        else:
            try:
                if len(self.arch_ids) > 0:
                    for self.arch in self.arches:
                        data, rect = self.get_arch_data_2d('raw')

                elif self.arch.idx is not None:
                    print(f'display_frame_widget > update_image arch idx:  {self.arch.idx}')
                    data, rect = self.get_arch_data_2d('raw')

                else:
                    print('display_frame_widget > update image getting sphere')
                    data, rect = self.get_sphere_data_2d()
            except (TypeError, IndexError):
                data = np.arange(100).reshape(10, 10)
                rect = Qt.QtCore.QRect(1, 1, 1, 1)

        mn, mx = np.nanpercentile(data, (5, 99.5))
        self.image.setImage(data.T[:, ::-1], levels=(mn, mx))
        self.image.setRect(rect)
        apply_cmap(self.image, 'viridis')

        self.raw_histogram.setLevels(min=mn, max=mx)
        return data

    def update_binned(self):
        """Updates image plotted in image frame
        """
        if self.sphere.name == 'null_main':
            data = np.arange(100).reshape(10, 10)
            rect = Qt.QtCore.QRect(1, 1, 1, 1)
        else:
            try:
                if len(self.arch_ids) > 0:
                    print(f'display_frame_widget > update_binned: len(self.arches) = {len(self.arches)}')
                    for self.arch in self.arches:
                        print(f'display_frame_widget > update_binned: self.arch.idx = {self.arch.idx}')
                        data, rect = self.get_arch_data_2d('rebinned')

                elif self.arch.idx is not None:
                    data, rect = self.get_arch_data_2d('rebinned')

                else:
                    print('display_frame_widget > update binned getting sphere')
                    data, rect = self.get_sphere_data_2d()
            except (TypeError, IndexError):
                data = np.arange(100).reshape(10, 10)
                rect = Qt.QtCore.QRect(1, 1, 1, 1)

        mn, mx = np.nanpercentile(data, (5, 99.5))
        # self.binned.setImage(data.T[:, ::-1], levels=(mn, mx))
        self.binned.setImage(data[:, ::-1], levels=(mn, mx))
        self.binned.setRect(rect)
        apply_cmap(self.binned, 'viridis')

        self.binned_histogram.setLevels(min=mn, max=mx)
        return data

    def get_arch_data_2d(self, img_type='rebinned'):
        """Returns data and QRect for data in arch
        """
        with self.arch.arch_lock:
            int_data = self.arch.int_2d

        if img_type == 'rebinned':
            data, corners = read_NRP(self.ui.normChannel, int_data)

            rect = get_rect(
                get_xdata(self.ui.imageUnit, int_data)[corners[2]:corners[3]],
                int_data.chi[corners[0]:corners[1]]
            )

        # elif self.ui.imageIntRaw.currentIndex() == 1:
        elif img_type == 'raw':
            print('display_frame_widget > getting raw image')
            with self.arch.arch_lock:
                if self.ui.normChannel.currentIndex() == 0:
                    if self.arch.map_norm is None or self.arch.map_norm == 0:
                        data = self.arch.map_raw.copy()
                    else:
                        data = self.arch.map_raw.copy() / self.arch.map_norm
                else:
                    data = self.arch.map_raw.copy()
                if self.ui.imageMask.isChecked():
                    data[self.arch.mask] = 0
            rect = get_rect(
                np.arange(data.shape[0]),
                np.arange(data.shape[1]),
            )

        return data, rect

    def get_sphere_data_2d(self):
        """Returns data and QRect for data in sphere
        """
        with self.sphere.sphere_lock:
            int_data = self.sphere.bai_2d
            # if self.ui.imageMethod.currentIndex() == 0:
            #     int_data = self.sphere.mgi_2d
            #     if type(int_data.ttheta) == int:
            #         self.ui.imageMethod.setCurrentIndex(1)
            #         int_data = self.sphere.bai_2d
            # elif self.ui.imageMethod.currentIndex() == 1:
            #     int_data = self.sphere.bai_2d

        # self.ui.imageNRP = 'Normalized'
        data, corners = read_NRP(self.ui.normChannel, int_data)

        rect = get_rect(
            get_xdata(self.ui.imageUnit, int_data)[corners[2]:corners[3]],
            int_data.chi[corners[0]:corners[1]]
        )

        return data, rect

    def update_plot(self):
        """Updates data in plot frame
        """
        print('display_frame_widget > updating 1D plot')
        if self.sphere.name == 'null_main':
            data = (np.arange(100), np.arange(100))
            self.curves[0].setData(data[0], data[1])
            return data

        try:
            with self.sphere.sphere_lock:
                sphere_int_data = self.sphere.bai_1d
                # if self.ui.plotMethod.currentIndex() == 0:
                #     sphere_int_data = self.sphere.mgi_1d
                #     if type(sphere_int_data.ttheta) == int:
                #         self.ui.plotMethod.setCurrentIndex(1)
                #         sphere_int_data = self.sphere.bai_1d
                # elif self.ui.plotMethod.currentIndex() == 1:
                #     sphere_int_data = self.sphere.bai_1d

            # self.ui.plotNRP = 'Normalized'
            s_ydata, corners = read_NRP(self.ui.normChannel, sphere_int_data)
            s_xdata = get_xdata(self.ui.plotUnit, sphere_int_data)[corners[0]:corners[1]]

            print(f'display_frame_widget > update_plot: self.arch.idx: {self.arch.idx}')
            if self.arch.idx is not None:
                with self.arch.arch_lock:
                    arc_int_data = self.arch.int_1d

                # if self.ui.plotOverlay.isChecked():
                if self.ui.plotMethod.currentText() == 'Overlay':
                    # self.curve1.setData(s_xdata, s_ydata)
                    self.curves[0].setData(s_xdata, s_ydata)
                else:
                    self.curves[0].clear()

                # a_ydata, corners = read_NRP(self.ui.plotNRP, arc_int_data)
                a_ydata, corners = read_NRP(self.ui.normChannel, arc_int_data)
                a_xdata = get_xdata(self.ui.plotUnit, arc_int_data)[corners[0]:corners[1]]
                # self.curve2.setData(a_xdata, a_ydata)
                self.curves[0].setData(a_xdata, a_ydata)

                return a_xdata, a_ydata

            else:
                [curve.clear() for curve in self.curves]
                self.curves[0].setData(s_xdata, s_ydata)
                # self.curve2.clear()

                return s_xdata, s_ydata

        except (TypeError, IndexError):
            data = (np.arange(100), np.arange(100))
            # self.curve1.setData(data[0], data[1])
            # self.curve2.setData(data[0], data[1])
            self.curves[0].setData(data[0], data[1])
            return data

    def save_image(self):
        """Saves currently displayed image. Formats are automatically
        grabbed from Qt. Also implements tiff saving.
        """
        ext_filter = "Images ("
        for f in formats:
            ext_filter += "*." + f + " "

        ext_filter += "*.tiff)"

        fname, _ = QFileDialog.getSaveFileName(filter=ext_filter)
        if fname == '':
            return

        _, ext = fname.split('.')
        if ext.lower() in formats:
            self.image.save(fname)

        elif ext.lower() == 'tiff':
            data = self.update_image()
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

        xdata, ydata = self.update_plot()

        _, ext = fname.split('.')
        if ext.lower() == 'xye':
            ut.write_xye(fname, xdata, ydata)

        elif ext.lower() == 'csv':
            ut.write_csv(fname, xdata, ydata)


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
    if box.currentIndex() == 0:
        nzarr = int_data.raw
    elif box.currentIndex() == 1:
        nzarr = int_data.norm
    elif box.currentIndex() == 2:
        nzarr = int_data.pcount
    data = nzarr.data[()]
    if data.ndim > 1:
        data = data.T
    corners = nzarr.corners

    if data.size == 0:
        data = np.zeros(int_data.norm.shape)
        if len(corners) == 2:
            corners = [0, int_data.norm.shape[0]]
        if len(corners) == 4:
            corners = [0, int_data.norm.shape[0], 0, int_data.norm.shape[1]]
    return data, corners


def get_xdata(box, int_data):
    """Reads the unit box and returns appropriate xdata

    args:
        box: QComboBox, list of options
        int_data: int_nd_data object, data to parse

    returns:
        xdata: numpy array, x axis data for plot.
    """
    if box.currentIndex() == 0:
        xdata = int_data.ttheta
    elif box.currentIndex() == 1:
        xdata = int_data.q
    return xdata


def apply_cmap(img, cmap='viridis'):
    # Get the colormap
    colormap = cm.get_cmap(cmap)  # cm.get_cmap("CMRmap")
    colormap._init()
    lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt

    # Apply the colormap
    img.setLookupTable(lut)
