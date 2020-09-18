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
from ...widgets import pgxImageWidget

QFileDialog = QtWidgets.QFileDialog

formats = [
    str(f.data(), encoding='utf-8').lower() for f in
    Qt.QtGui.QImageReader.supportedImageFormats()
]

AA_inv = u'\u212B\u207B\u00B9'
x_labels = ('Q', u'2\u03B8', 'Qxy')
x_units = (AA_inv, 'deg', AA_inv)
y_labels = (u'\u03C7', u'\u03C7', 'Qz')
y_units = ('deg', 'deg', AA_inv)

# Switch to using white background and black foreground
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


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
        arch: EwaldArch, currently loaded arch object
        arch_ids: List of EwaldArch indices currently loaded
        arches: Dictionary of currently loaded EwaldArches
        data_1d: Dictionary object holding all 1D data in memory
        data_2d: Dictionary object holding all 2D data in memory
        ui: Ui_Form from qtdeisgner

    methods:
        get_arch_map_raw: Gets 2D raw data from an arch object
        get_arch_data_2d: Gets 2D rebinned data from an arch object
        get_sphere_data_2d: Gets overall 2D data for the sphere
        update: Updates the displayed image and plot
        update_image: Updates image data based on selections
        update_plot: Updates plot data based on selections
    """

    def __init__(self, sphere, arch, arch_ids, arches, data_1d, data_2d, parent=None):
        _translate = Qt.QtCore.QCoreApplication.translate
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.imageUnit.setItemText(0, _translate("Form", "Q" + "-" + "Chi"))
        self.ui.imageUnit.setItemText(1, _translate("Form", "2" + u"\u03B8" + "-" + "Chi"))
        self.ui.plotUnit.setItemText(1, _translate("Form", "2" + u"\u03B8"))

        # Plotting parameters
        self.cmap = self.ui.cmap.currentText()
        self.plotMethod = self.ui.plotMethod.currentText()
        self.scale = self.ui.scale.currentText()

        # Data object initialization
        self.sphere = sphere
        self.arch = arch
        self.arch_ids = arch_ids
        self.arches = arches
        self.data_1d = data_1d
        self.data_2d = data_2d
        self.bkg_1d = 0.
        self.bkg_2d = 0.

        # Image and Binned 2D Data
        self.image_data = (None, None)
        self.binned_data = (None, None)
        self.plot_data = (np.zeros(0), np.zeros(0))

        # State variable initialization
        self.auto_last = True

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
        self.image_widget = pgxImageWidget(lockAspect=1)
        self.image_layout.addWidget(self.image_widget)

        # Regrouped Image pane setup
        self.binned_layout = Qt.QtWidgets.QHBoxLayout(self.ui.binnedFrame)
        self.binned_layout.setContentsMargins(0, 0, 0, 0)
        self.binned_layout.setSpacing(0)
        self.binned_widget = pgxImageWidget()
        self.binned_layout.addWidget(self.binned_widget)

        # 1D/Waterfall Plot pane setup
        self.plot_layout = Qt.QtWidgets.QHBoxLayout(self.ui.plotFrame)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_layout.setSpacing(0)

        # 1D Plot pane setup
        self.plot_win = pg.GraphicsLayoutWidget()
        self.plot_layout.addWidget(self.plot_win)
        self.plot = self.plot_win.addPlot(viewBox=RectViewBox())
        self.legend = self.plot.addLegend()
        self.curves = []

        # WF Plot pane setup
        self.wf_widget = pgxImageWidget()
        self.plot_layout.addWidget(self.wf_widget)

        # Waterfall Plot setup
        if self.plotMethod == 'Waterfall':
            self.plot_win.setParent(None)
            self.plot_layout.addWidget(self.wf_widget)
        else:
            self.wf_widget.setParent(None)
            self.plot_layout.addWidget(self.plot_win)

        # All Windows Signal connections
        self.ui.normChannel.activated.connect(self.update)
        self.ui.setBkg.clicked.connect(self.setBkg)
        self.ui.scale.currentIndexChanged.connect(self.update_views)
        self.ui.cmap.currentIndexChanged.connect(self.update_views)
        self.ui.shareAxis.stateChanged.connect(self.update)

        # 2D Window Signal connections
        self.ui.imageUnit.activated.connect(self.update_image)
        self.ui.imageUnit.activated.connect(self.update_binned)
        self.ui.imageMask.stateChanged.connect(self.update_image)
        self.ui.imageMask.stateChanged.connect(self.update_binned)

        # 1D Window Signal connections
        self.ui.plotMethod.currentIndexChanged.connect(self.update_plot_view)
        self.ui.yOffset.valueChanged.connect(self.update_plot_view)
        self.ui.plotUnit.activated.connect(self.update_plot)
        self.ui.showLegend.stateChanged.connect(self.update_plot_view)

    def setup_1d_layout(self):
        """Setup the layout for 1D plot
        """
        self.wf_widget.setParent(None)
        self.plot_layout.addWidget(self.plot_win)

    def setup_wf_layout(self):
        """Setup the layout for WF plot
        """
        self.plot_win.setParent(None)
        self.plot_layout.addWidget(self.wf_widget)

    def update(self):
        """Updates image and plot frames based on toolbar options
        """
        if (len(self.arch_ids) == 0) or (self.sphere.name == 'null_main'):
            return True

        if (len(self.sphere.arches.index) == 1) and (self.arch_ids[0] == 'Overall'):
            return True

        print(f'display_frame_widget > update: self.arch_ids = {self.arch_ids}')
        # Sets title text
        if 'Overall' in self.arch_ids:
            self.ui.labelCurrent.setText(self.sphere.name)
        else:
            self.ui.labelCurrent.setText("Image " + (self.arch_ids[0]))

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

    def update_views(self):
        self.cmap = self.ui.cmap.currentText()
        self.plotMethod = self.ui.plotMethod.currentText()
        self.scale = self.ui.scale.currentText()

        self.update_image_view()
        self.update_binned_view()
        self.update_plot_view()

    def update_image(self):
        """Updates image plotted in image frame
        """
        # print(f'display_frame_widget > update_image: sphere.data_2d.keys = {self.sphere.data_2d.keys()}')
        print(f'display_frame_widget > update_image: data_2d.keys = {self.data_2d.keys()}')
        try:
            if 'Overall' in self.arch_ids:
                print(f'display_frame_widget > update_image: sphere.overall_raw = {self.sphere.overall_raw}')
                print('display_frame_widget > update_image: getting sphere')
                data, rect = self.get_sphere_map_raw()
            elif len(self.arches) > 0:
                data = 0
                for (arch_id, self.arch) in self.arches.items():
                    print(f'display_frame_widget > update_image: arch_id, arch.idx = {arch_id}, {self.arch.idx}')
                    data_, rect = self.get_arch_map_raw()
                    data += data_
        except (TypeError, IndexError, AttributeError):
            data = np.arange(100).reshape(10, 10)
            rect = Qt.QtCore.QRect(1, 1, 1, 1)

        self.image_data = (data, rect)
        self.update_image_view()

    def update_image_view(self):
        data, rect = self.image_data

        print(f'display_frame_widget > update_image: scale = {self.scale}')
        self.image_widget.setImage(data.T[:, ::-1], scale=self.scale, cmap=self.cmap)
        self.image_widget.setRect(rect)

        return data

    def update_binned(self):
        """Updates image plotted in image frame
        """
        try:
            if len(self.arches) > 0:
                print(f'display_frame_widget > update_binned: len(self.arches) = {len(self.arches)}')
                for (arch_id, self.arch) in self.arches.items():
                    print(f'display_frame_widget > update_binned: self.arch.idx = {self.arch.idx}')
                    data, rect = self.get_arch_data_2d()
            else:
                print('display_frame_widget > update_binned: getting sphere')
                data, rect = self.get_sphere_data_2d()
        except (TypeError, IndexError):
            data = np.arange(100).reshape(10, 10)
            rect = Qt.QtCore.QRect(1, 1, 1, 1)

        self.binned_data = (data, rect)
        self.update_binned_view()

    def update_binned_view(self):
        data, rect = self.binned_data

        print(f'display_frame_widget > update_image: scale = {self.scale}')
        self.binned_widget.setImage(data.T[:, ::-1], scale=self.scale, cmap=self.cmap)
        self.binned_widget.setRect(rect)
        return data

    def get_arch_data_2d(self):
        """Returns data and QRect for data in arch
        """
        with self.arch.arch_lock:
            int_data = self.arch.int_2d

        data, corners = read_NRP(self.ui.normChannel, int_data)

        rect = get_rect(
            get_xdata(self.ui.imageUnit, int_data)[corners[2]:corners[3]],
            int_data.chi[corners[0]:corners[1]]
        )

        return data, rect

    def get_sphere_data_2d(self):
        """Returns data and QRect for data in sphere
        """
        with self.sphere.sphere_lock:
            int_data = self.sphere.bai_2d

        data, corners = read_NRP(self.ui.normChannel, int_data)

        rect = get_rect(
            get_xdata(self.ui.imageUnit, int_data)[corners[2]:corners[3]],
            int_data.chi[corners[0]:corners[1]]
        )

        return data, rect

    def get_arches_data_2d(self, idxs=None, rv='all'):
        """Return 1D data for multiple arches"""
        if idxs is None:
            idxs = list(self.arches.keys())

        ydata = 0.
        for nn, idx in enumerate(idxs):
            print(f'display_frame_widget > get_arches_data_1d: idx, idxs: {idx} {idxs}')
            int_data = self.arches[idx].int_1d
            s_ydata, corners = read_NRP(self.ui.normChannel, int_data)
            if nn == 0:
                ydata = s_ydata
                xdata = get_xdata(self.ui.plotUnit, int_data)[corners[0]:corners[1]]
            else:
                ydata = np.vstack((ydata, s_ydata))
            print(f'display_frame_widget > get_arches_data_1d: data, s_ydata.shapes: {ydata.shape} {s_ydata.shape}')

        if ydata.ndim == 2:
            if rv == 'average':
                ydata = np.mean(ydata, 0)
            elif rv == 'sum':
                ydata = np.sum(ydata, 0)

        print(f'display_frame_widget > get_arches_data_1d: data.shape: ({ydata.shape}, {xdata.shape})')

        # rect = get_rect(
        #     get_xdata(self.ui.imageUnit, int_data)[corners[0]:corners[1]],
        #     np.arange(len(idxs))
        # )
        return ydata, xdata#, rect

    def get_arch_map_raw(self):
        """Returns data and QRect for data in arch
        """
        print('display_frame_widget > getting raw image')
        with self.arch.arch_lock:
            print(f'display_frame_widget > get_arch_map_raw: arch.map_norm = {self.arch.map_norm}')
            data = self.arch.map_raw.copy()
            # if self.ui.normChannel.currentIndex() == 0:
            #     if self.arch.map_norm is None or self.arch.map_norm == 0:
            #         data = self.arch.map_raw.copy()
            #     else:
            #         data = self.arch.map_raw.copy() / self.arch.map_norm
            # else:
            #     data = self.arch.map_raw.copy()
            if self.ui.imageMask.isChecked():
                data[self.arch.mask] = 0

        rect = get_rect(
            np.arange(data.shape[0]),
            np.arange(data.shape[1]),
        )

        return data, rect

    def get_sphere_map_raw(self):
        """Returns data and QRect for data in sphere
        """
        # data = self.sphere.overall_norm
        data = self.sphere.overall_raw
        rect = get_rect(
            np.arange(data.shape[0]),
            np.arange(data.shape[1]),
        )

        return data, rect

    def update_plot(self):
        """Updates data in plot frame
        """
        print('display_frame_widget > update_plot: updating 1D plot')
        if (self.sphere.name == 'null_main') or (len(self.arch_ids) == 0):
            data = (np.arange(100), np.arange(100))
            return data

        print(f'display_frame_widget > update_plot: updating 1D plot')
        # print(f'display_frame_widget > update_plot: sphere.data_1d.keys = {self.sphere.data_1d.keys()}')
        print(f'display_frame_widget > update_plot: data_1d.keys = {self.data_1d.keys()}')

        # Get 1D data for all arches
        ydata, xdata = self.get_arches_data_1d()

        # Subtract background
        ydata -= self.bkg_1d
        if ydata.ndim == 1:
            ydata = ydata[np.newaxis, :]

        self.plot_data = (ydata, xdata)
        self.update_plot_view()

    def update_plot_view(self):
        """Updates 1D view of data in plot frame
        """
        # Clear curves
        [curve.clear() for curve in self.curves]
        self.curves.clear()

        self.plotMethod = self.ui.plotMethod.currentText()
        print(f'display_frame_widget > update_plot: currentText = {self.plotMethod}')
        if (self.plotMethod == 'Waterfall') and (len(self.arches) > 3):
            self.update_wf()
        else:
            self.update_1d_view()

    def update_1d_view(self):
        """Updates data in 1D plot Frame
        """
        self.setup_1d_layout()
        ydata_, xdata_ = self.plot_data
        ydata, s_xdata = ydata_.copy(), xdata_.copy()

        if self.scale == 'Log':
            if ydata.min() <= 0.:
                ydata -= ydata.min() - 1.
            ydata = np.log(ydata)
        elif self.scale == 'Sqrt':
            if ydata.min() < 0.:
                ydata -= ydata.min()
            ydata = np.sqrt(ydata)

        idxs = list(self.arches.keys())
        self.setup_curves(len(idxs))

        # plotMethod = self.ui.plotMethod.currentText()
        if self.plotMethod in ['Overlay', 'Waterfall']:
            offset = self.ui.yOffset.value()
            print(f'offset: {offset}')
            y_offset = 0
            for nn, (curve, s_ydata, idx) in enumerate(zip(self.curves, ydata, idxs)):
                print(f'display_frame_widget > update_1d_view: arch.idx: {idx}')

                if nn == 0:
                    y_offset = offset / 100 * (s_ydata.max() - s_ydata.min())
                curve.setData(s_xdata, s_ydata + y_offset*nn)

        else:
            if self.plotMethod == 'Average':
                s_ydata = np.mean(ydata, 0)
            elif self.plotMethod == 'Sum':
                s_ydata = np.sum(ydata, 0)

            self.curves[0].setData(s_xdata, s_ydata)

        # Apply labels to plot
        plotUnit = self.ui.plotUnit.currentIndex()
        self.plot.setLabel("bottom", x_labels[plotUnit], units=x_units[plotUnit])
        self.plot.setLabel("left", 'Intensity')

        return s_xdata, s_ydata

    def update_wf(self):
        """Updates data in 1D plot Frame
        """
        print('display_frame_widget > update_wf: updating WF plot')
        self.setup_wf_layout()

        data_, xdata_ = self.plot_data
        data, s_xdata = data_.copy(), xdata_.copy()
        rect = get_rect(s_xdata, np.arange(data.shape[0]))

        print(f'display_frame_widget > update_wf: scale = {self.scale}')
        self.wf_widget.setImage(data.T, scale=self.scale, cmap=self.cmap)
        self.wf_widget.setRect(rect)

        return data

    def get_arches_data_1d(self, idxs=None, rv='all'):
        """Return 1D data for multiple arches"""
        if idxs is None:
            idxs = list(self.arches.keys())

        ydata = 0.
        for nn, idx in enumerate(idxs):
            print(f'display_frame_widget > get_arches_data_1d: idx, idxs: {idx} {idxs}')
            int_data = self.arches[idx].int_1d
            s_ydata, corners = read_NRP(self.ui.normChannel, int_data)
            if nn == 0:
                ydata = s_ydata
                xdata = get_xdata(self.ui.plotUnit, int_data)[corners[0]:corners[1]]
            else:
                ydata = np.vstack((ydata, s_ydata))
            print(f'display_frame_widget > get_arches_data_1d: data, s_ydata.shapes: {ydata.shape} {s_ydata.shape}')

        if ydata.ndim == 2:
            if rv == 'average':
                ydata = np.mean(ydata, 0)
            elif rv == 'sum':
                ydata = np.sum(ydata, 0)

        print(f'display_frame_widget > get_arches_data_1d: data.shape: ({ydata.shape}, {xdata.shape})')

        # rect = get_rect(
        #     get_xdata(self.ui.imageUnit, int_data)[corners[0]:corners[1]],
        #     np.arange(len(idxs))
        # )
        return ydata, xdata#, rect

    def setBkg(self):
        """Sets selected points as background.
        If background is already selected, it unsets it"""
        if (len(self.arch_ids) == 0) or (len(self.arches) == 0):
            return

        print(f'display_frame_widget > setBkg: {self.ui.setBkg.text()}')
        if self.ui.setBkg.text() == 'Set Bkg':
            idxs = self.arch_ids
            if 'Overall' in self.arch_ids:
                idxs = sorted(list(self.sphere.arches.index))

            self.bkg_1d, _ = self.get_arches_data_1d(idxs, rv='average')
            self.ui.setBkg.setText('Clear Bkg')
        else:
            self.bkg_1d = 0.
            self.ui.setBkg.setText('Set Bkg')
        print(f'display_frame_widget > setBkg: {self.ui.setBkg.text()}')
        print(f'display_frame_widget > setBkg: self.bkg_1d = {self.bkg_1d}')

        self.update()
        return

    def setup_curves(self, idxs=1):
        """Initialize curves for line plots
        """
        self.curves.clear()
        self.legend.clear()

        print(f'display_frame_widget > setup_curves: plotMethod = {self.plotMethod}')
        arch_ids = [self.plotMethod]
        print(f'display_frame_widget > setup_curves: arch_ids = {arch_ids}')
        if self.plotMethod in ['Overlay', 'WaterFall']:
            arch_ids = list(self.arches.keys())
        print(f'display_frame_widget > setup_curves: arches.keys(), arch_ids = {list(self.arches.keys())}, {arch_ids}')

        # Define color tuples
        try:
            colors_tuples = cm.get_cmap(self.cmap, 256)
        except ValueError:
            colors_tuples = cm.get_cmap('jet', 256) # nipy_spectral

        colors = colors_tuples(np.linspace(0, 1, idxs))
        colors = np.round(colors * [255, 255, 255, 1]).astype(int)
        colors = [tuple(color[:3]) for color in colors]

        self.curves = [self.plot.plot(
            pen=color,
            symbolBrush=color,
            symbolPen=color,
            symbolSize=3,
            name=arch_id,
        ) for (color, arch_id) in zip(colors, arch_ids)]

        if not self.ui.showLegend.isChecked():
            self.legend.clear()

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
        nzarr = int_data.norm
        # nzarr = int_data.raw
    elif box.currentIndex() == 1:
        nzarr = int_data.norm
    elif box.currentIndex() == 2:
        nzarr = int_data.pcount
    data_ = nzarr

    if not isinstance(nzarr, np.ndarray):
        data_ = nzarr.data[()]
    data = data_.copy()

    if not isinstance(nzarr, np.ndarray):
        corners = nzarr.corners
    else:
        if data.ndim > 1:
            corners = [0, data.shape[0], 0, data.shape[1]]
        else:
            corners = [0, data.shape[0]]

    print(f'*****display_frame_widget > read_NRP: corners, nzarr.shape = {corners} {nzarr.data.shape}')
    print(f'display_frame_widget > read_NRP: data.shape = {data.shape}')

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
        xdata = int_data.q
    elif box.currentIndex() == 1:
        xdata = int_data.ttheta
    return xdata


def apply_cmap(img, cmap='viridis'):
    # Get the colormap
    colormap = cm.get_cmap(cmap)  # cm.get_cmap("CMRmap")
    colormap._init()
    lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt

    # Apply the colormap
    img.setLookupTable(lut)


def update_1d(self):
    """Updates data in 1D plot Frame
    """
    self.setup_1D_layout()
    ydata, xdata = self.plot_data

    plotMethod = self.ui.plotMethod.currentText()
    if plotMethod in ['Overlay', 'Waterfall']:
        idxs = self.arch_ids
        if 'Overall' in self.arch_ids:
            idxs = sorted(list(self.sphere.arches.index))

        self.setup_curves(len(idxs))

        offset = self.ui.yOffset.value()
        print(f'offset: {offset}')
        y_offset = 0
        # for curve, (arch_id, arch) in zip(self.curves, self.arches.items()):
        for nn, (curve, idx) in enumerate(zip(self.curves, idxs)):
            print(f'display_frame_widget > update_plot: arch.idx: {idx}')
            int_data = self.arches[idx].int_1d
            s_ydata, corners = read_NRP(self.ui.normChannel, int_data)
            s_ydata -= self.bkg_1d
            s_xdata = get_xdata(self.ui.plotUnit, int_data)[corners[0]:corners[1]]

            if nn == 0:
                y_offset = offset / 100 * (s_ydata.max() - s_ydata.min())
            curve.setData(s_xdata, s_ydata + y_offset * nn)

    else:
        self.setup_curves()
        if 'Overall' in self.arch_ids:
            with self.sphere.sphere_lock:
                sphere_int_data = self.sphere.bai_1d

            s_ydata, corners = read_NRP(self.ui.normChannel, sphere_int_data)
            s_xdata = get_xdata(self.ui.plotUnit, sphere_int_data)[corners[0]:corners[1]]

            if self.ui.plotMethod.currentText() == 'Average':
                s_ydata /= len(self.sphere.arches.index)
                s_ydata -= self.bkg_1d
            else:
                s_ydata -= self.bkg_1d * len(self.sphere.arches.index)

            self.curves[0].setData(s_xdata, s_ydata)

        else:
            s_ydata = 0.
            for curve, (arch_id, arch) in zip(self.curves, self.arches.items()):
                int_data = arch.int_1d
                ydata, corners = read_NRP(self.ui.normChannel, int_data)
                ydata -= self.bkg_1d
                s_ydata += ydata
                print(f'display_frame_widget > update_1d: ydata, s_ydata.shape = {ydata.shape} {s_ydata.shape}')

            s_xdata = get_xdata(self.ui.plotUnit, int_data)[corners[0]:corners[1]]
            print(f'display_frame_widget > update_1d: s_xdata = {s_xdata.shape}')
            # s_xdata = get_xdata(self.ui.plotUnit, int_data)

            # TODO: put in average below
            # s_ydata, corners = read_NRP(self.ui.normChannel, y_data_all[-1])
            if self.ui.plotMethod.currentText() == 'Average':
                s_ydata /= len(self.arches)

            self.curves[0].setData(s_xdata, s_ydata)

    # Apply labels to plot
    plotUnit = self.ui.plotUnit.currentIndex()
    self.plot.setLabel("bottom", x_labels[plotUnit], units=x_units[plotUnit])
    self.plot.setLabel("left", 'Intensity')

    return s_xdata, s_ydata


def setup_1D_layout(self):
    """Setup the layout for 1D/WF plots
    """
    plotMethod = self.ui.plotMethod.currentText()
    print(f'display_frame_widget > setup_1D_layout: currentText = {plotMethod}')
    print(f'display_frame_widget > setup_1D_layout: lastText = {self.last_plotMethod}')
    if plotMethod == self.last_plotMethod:
        return
    elif (plotMethod != 'Waterfall') and (self.last_plotMethod != 'Waterfall'):
        return
    else:
        self.last_plotMethod = plotMethod

    if (plotMethod == 'Waterfall') and (len(self.arches) > 3):
        self.plot_win.setParent(None)
        self.plot_layout.addWidget(self.wf_widget)
    else:
        self.wf_widget.setParent(None)
        self.plot_layout.addWidget(self.plot_win)
        self.last_plotMethod = 'Overlay'
