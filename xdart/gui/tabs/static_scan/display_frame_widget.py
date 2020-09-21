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
Th = u'\u03B8'
Chi = u'\u03C7'
Deg = u'\u00B0'
Qxy = '<math>Q<sub>xy</sub></math>'
Qz = '<math>Q<sub>z</sub></math>'

plotUnits = [f"Q ({AA_inv})", f"2{Th} ({Deg})", f"{Chi} ({Deg})"]
imageUnits = [f"Q-{Chi}", f"2{Th}-{Chi}", f"Qxy-Qz"]

x_labels_1D = ('Q', f"2{Th}", Chi)
x_units_1D = (AA_inv, Deg, Deg)

x_labels_2D = ('Q', f"2{Th}", Qxy)
x_units_2D = (AA_inv, Deg, AA_inv)

y_labels_2D = (Chi, Chi, Qz)
y_units_2D = (Deg, Deg, AA_inv)

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
        get_arches_map_raw: Gets averaged 2D raw data from arches
        get_sphere_map_raw: Gets averaged (and normalized) 2D raw data for all images
        get_arches_data_2d: Gets averaged 2D rebinned data from arches
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

        self.ui.imageUnit.setItemText(0, _translate("Form", imageUnits[0]))
        self.ui.imageUnit.setItemText(1, _translate("Form", imageUnits[1]))
        self.ui.imageUnit.setItemText(2, _translate("Form", imageUnits[2]))

        self.ui.plotUnit.setItemText(0, _translate("Form", plotUnits[0]))
        self.ui.plotUnit.setItemText(1, _translate("Form", plotUnits[1]))
        self.ui.plotUnit.setItemText(2, _translate("Form", plotUnits[2]))

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
        self.bkg_map_raw = 0.

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

    def _updated(self):
        """Check if there is data to update
        """
        if (len(self.arch_ids) == 0) or (self.sphere.name == 'null_main'):
            return False

        if (len(self.sphere.arches.index) == 1) and (self.arch_ids[0] == 'Overall'):
            return False

        return True

    def update(self):
        """Updates image and plot frames based on toolbar options
        """
        print(f'display_frame_widget > update: static = {self.sphere.static}')
        print(f'display_frame_widget > update: gi = {self.sphere.gi}')
        if not self._updated():
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
        if not self._updated():
            return True

        self.cmap = self.ui.cmap.currentText()
        self.plotMethod = self.ui.plotMethod.currentText()
        self.scale = self.ui.scale.currentText()

        self.update_image_view()
        self.update_binned_view()
        self.update_plot_view()

    def update_image(self):
        """Updates image plotted in image frame
        """
        if not self._updated():
            return True

        print(f'display_frame_widget > update_image: data_2d.keys = {self.data_2d.keys()}')
        if 'Overall' in self.arch_ids:
            print(f'display_frame_widget > update_image: sphere.overall_raw = {self.sphere.overall_raw}')
            print('display_frame_widget > update_image: getting sphere')
            data = self.get_sphere_map_raw()
        else:
            print(f'display_frame_widget > update_image: arches = {self.arches.keys()}')
            data = self.get_arches_map_raw()

        data = np.asarray(data, dtype=np.float)
        print(f'display_frame_widget > update_image: Subtracting BG {self.bkg_map_raw}')
        # Subtract background
        data -= self.bkg_map_raw
        print(f'display_frame_widget > update_image: Subtracted BG, data.shape = {data.shape}')

        rect = get_rect(np.arange(data.shape[0]), np.arange(data.shape[1]))
        print(f'display_frame_widget > update_image: Subtracted BG')

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
        if not self._updated():
            return True

        if 'Overall' in self.arch_ids:
            print('display_frame_widget > update_binned: getting sphere')
            intensity, xdata, ydata = self.get_sphere_data_2d()
        else:
            intensity, xdata, ydata = self.get_arches_data_2d()

        # Subtract background
        intensity -= self.bkg_2d

        rect = get_rect(xdata, ydata)
        self.binned_data = (intensity, rect)
        self.update_binned_view()

        return

    def update_binned_view(self):
        data, rect = self.binned_data

        print(f'display_frame_widget > update_image: scale = {self.scale}')
        self.binned_widget.setImage(data.T[:, ::-1], scale=self.scale, cmap=self.cmap)
        self.binned_widget.setRect(rect)

        imageUnit = self.ui.imageUnit.currentIndex()
        self.binned_widget.image_plot.setLabel(
            "bottom", x_labels_2D[imageUnit], units=x_units_2D[imageUnit]
        )
        self.binned_widget.image_plot.setLabel(
            "left", y_labels_2D[imageUnit], units=y_units_2D[imageUnit]
        )

        return data

    def update_plot(self):
        """Updates data in plot frame
        """
        print('display_frame_widget > update_plot: updating 1D plot')
        if (self.sphere.name == 'null_main') or (len(self.arch_ids) == 0):
            data = (np.arange(100), np.arange(100))
            return data

        print(f'display_frame_widget > update_plot: updating 1D plot')
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

        self.plot.getAxis("left").setLogMode(False)
        if self.scale == 'Log':
            ydata -= (ydata.min() - 1.)
            ydata = np.log10(ydata)
            self.plot.getAxis("left").setLogMode(True)
            # [curve.axis.setLogMode(True) for curve in self.curves]
        elif self.scale == 'Sqrt':
            if ydata.min() < 0.:
                ydata -= ydata.min()
            ydata = np.sqrt(ydata)

        idxs = list(self.arches.keys())
        self.setup_curves(len(idxs))

        if self.plotMethod in ['Overlay', 'Waterfall']:
            offset = self.ui.yOffset.value()
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
        self.plot.setLabel("bottom", x_labels_1D[plotUnit], units=x_units_1D[plotUnit])
        self.plot.setLabel("left", 'Intensity')

        self.plot.getAxis("bottom").maxTickLength = 10
        self.plot.getAxis("left").maxTickLength = 10

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

    def get_arches_map_raw(self, idxs=None):
        """Return 2D arch data for multiple arches (averaged)"""
        if idxs is None:
            idxs = list(self.arches.keys())
        print(f'display_frame_widget > get_arches_map_raw: idxs: {idxs}')

        intensity = 0.
        for nn, idx in enumerate(idxs):
            print(f'display_frame_widget > get_arches_map_raw: idx, idxs: {idx} {idxs}')
            arch = self.arches[idx]
            map_raw = arch.map_raw
            intensity += self.normalize(map_raw, arch.scan_info)

        intensity /= (nn + 1)
        print(f'display_frame_widget > get_arches_data_2d: intensity.shapes, nn, idxs:'
              f' {intensity.shape}, {nn}, {idxs}')

        return np.asarray(intensity, dtype=np.float)

    def get_sphere_map_raw(self):
        """Returns data and QRect for data in sphere
        """
        print(f'display_frame_widget > get_sphere_map_raw: normChannel = {self.ui.normChannel.currentText()}')
        if self.ui.normChannel.currentText() != 'None':
            return self.get_arches_map_raw()

        with self.sphere.sphere_lock:
            return np.asarray(self.sphere.overall_raw, dtype=np.float)

    def get_arches_data_2d(self, idxs=None):
        """Return 2D arch data for multiple arches (averaged)"""
        if idxs is None:
            idxs = list(self.arches.keys())

        intensity = 0.
        for nn, idx in enumerate(idxs):
            print(f'display_frame_widget > get_arches_data_2d: idx, idxs: {idx} {idxs}')
            arch = self.arches[idx]
            int_data = arch.int_2d
            intensity += self.normalize(int_data.norm, arch.scan_info)

        intensity /= (nn + 1)
        print(f'display_frame_widget > get_arches_data_2d: intensity.shapes, nn, idxs:'
              f' {intensity.shape}, {nn}, {idxs}')

        xdata, ydata = self.get_xydata(arch)
        return np.asarray(intensity, dtype=np.float), xdata, ydata

    def get_sphere_data_2d(self):
        """Returns data and QRect for data in sphere
        """
        if self.ui.normChannel.currentText() != 'None':
            return self.get_arches_data_2d()

        with self.sphere.sphere_lock:
            int_data = self.sphere.bai_2d

        intensity = int_data.norm
        idxs = list(self.arches.keys())
        xdata, ydata = self.get_xydata(self.arches[idxs[0]])

        return np.asarray(intensity, dtype=np.float), xdata, ydata

    def get_arches_data_1d(self, idxs=None, rv='all'):
        """Return 1D data for multiple arches"""
        if idxs is None:
            idxs = list(self.arches.keys())

        ydata = 0.
        for nn, idx in enumerate(idxs):
            print(f'display_frame_widget > get_arches_data_1d: idx, idxs: {idx} {idxs}')
            int_data = self.arches[idx].int_1d
            s_ydata = self.normalize(int_data.norm, self.arches[idx].scan_info)
            if nn == 0:
                ydata = s_ydata
                xdata = get_xdata(self.ui.plotUnit, int_data)
            else:
                ydata = np.vstack((ydata, s_ydata))
            print(f'display_frame_widget > get_arches_data_1d: data, s_ydata.shapes: {ydata.shape} {s_ydata.shape}')

        if ydata.ndim == 2:
            if rv == 'average':
                ydata = np.mean(ydata, 0)
            elif rv == 'sum':
                ydata = np.sum(ydata, 0)

        print(f'display_frame_widget > get_arches_data_1d: data.shape: ({ydata.shape}, {xdata.shape})')

        return ydata, xdata

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
            self.bkg_2d, _, _ = self.get_arches_data_2d(idxs)
            self.bkg_map_raw = self.get_arches_map_raw(idxs)
            self.ui.setBkg.setText('Clear Bkg')
        else:
            self.bkg_1d = 0.
            self.bkg_2d = 0.
            self.bkg_map_raw = 0.
            self.ui.setBkg.setText('Set Bkg')
        # print(f'display_frame_widget > setBkg: {self.ui.setBkg.text()}')
        # print(f'display_frame_widget > setBkg: self.bkg_1d = {self.bkg_1d}')

        self.update()
        return

    def setup_curves(self, idxs=1):
        """Initialize curves for line plots
        """
        self.curves.clear()
        self.legend.clear()

        # print(f'display_frame_widget > setup_curves: plotMethod = {self.plotMethod}')
        arch_ids = list(self.arches.keys())
        # print(f'display_frame_widget > setup_curves: arch_ids = {arch_ids}')
        if self.plotMethod in ['Sum', 'Average']:
            arch_ids = [self.plotMethod]

        # print(f'display_frame_widget > setup_curves: arches.keys(), arch_ids =
        # {list(self.arches.keys())}, {arch_ids}')

        # Define color tuples
        try:
            colors_tuples = cm.get_cmap(self.cmap, 256)
        except ValueError:
            colors_tuples = cm.get_cmap('jet', 256)

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

    def normalize(self, int_data, scan_info):
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
        intensity = np.asarray(int_data.copy(), dtype=np.float)
        normChannel = self.ui.normChannel.currentText()
        if normChannel in scan_info.keys():
            intensity /= scan_info[normChannel]

        return intensity

    def read_NRP(self, int_data):
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
        nzarr = int_data.norm
        # if box.currentIndex() == 0:
        #     nzarr = int_data.norm
        #     # nzarr = int_data.raw
        # elif box.currentIndex() == 1:
        #     nzarr = int_data.norm
        # elif box.currentIndex() == 2:
        #     nzarr = int_data.pcount
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

    def get_xydata(self, arch):
        """Reads the unit box and returns appropriate xdata

        args:
            box: QComboBox, list of options
            int_data: int_nd_data object, data to parse

        returns:
            xdata: numpy array, x axis data for plot.
        """
        int_data = arch.int_2d
        imageUnit = self.ui.imageUnit.currentIndex()
        if imageUnit == 0:  # Q-Chi
            xdata, ydata = int_data.q, int_data.chi
        elif imageUnit == 1:  # 2Th-Chi
            xdata, ydata = int_data.ttheta, int_data.chi
        elif imageUnit == 2:  # Qzx-Qz
            xdata, ydata = int_data.qxy, int_data.qz

        return xdata, ydata


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


def read_NRP_(box, int_data):
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
