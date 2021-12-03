# -*- coding: utf-8 -*-
"""
@author: thampy
"""

# Standard library imports
import os
import time
import copy

# Other imports
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from pathlib import Path

# Qt imports
from PyQt5.QtCore import Qt as pyQt
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
import pyqtgraph.exporters
from pyqtgraph import ROI

# This module imports
from .ui.displayFrameUI import Ui_Form
from ...gui_utils import RectViewBox, get_rect
import xdart.utils as ut
from ...widgets import pgImageWidget, pmeshImageWidget
from xdart.utils import split_file_name

from icecream import ic; ic.configureOutput(prefix='', includeContext=True)

QFileDialog = QtWidgets.QFileDialog
QInputDialog = QtWidgets.QInputDialog
QCombo = QtWidgets.QComboBox
QDialog = QtWidgets.QDialog
_translate = Qt.QtCore.QCoreApplication.translate

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
        ui: Ui_Form from qtdesigner

    methods:
        get_arches_map_raw: Gets averaged 2D raw data from arches
        get_sphere_map_raw: Gets averaged (and normalized) 2D raw data for all images
        get_arches_int_2d: Gets averaged 2D rebinned data from arches
        get_sphere_int_2d: Gets overall 2D data for the sphere
        update: Updates the displayed image and plot
        update_image: Updates image data based on selections
        update_plot: Updates plot data based on selections
    """

    def __init__(self, sphere, arch, arch_ids, arches, data_1d, data_2d, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.ui.imageUnit.setItemText(0, _translate("Form", imageUnits[0]))
        self.ui.imageUnit.setItemText(1, _translate("Form", imageUnits[1]))
        self.ui.imageUnit.setItemText(2, _translate("Form", imageUnits[2]))

        self.ui.plotUnit.setItemText(0, _translate("Form", plotUnits[0]))
        self.ui.plotUnit.setItemText(1, _translate("Form", plotUnits[1]))
        self.ui.plotUnit.setItemText(2, _translate("Form", plotUnits[2]))

        self.ui.slice.setText(Chi)

        # Plotting parameters
        self.ui.cmap.clear()
        self.ui.cmap.addItems(['Default'] + plt.colormaps())
        self.ui.cmap.setCurrentIndex(0)
        self.cmap = self.ui.cmap.currentText()
        self.plotMethod = self.ui.plotMethod.currentText()
        self.scale = self.ui.scale.currentText()
        self.wf_yaxis = 'Frame #'
        self.wf_start = 0
        self.wf_step = 1

        # Data object initialization
        self.sphere = sphere
        self.arch = arch
        self.arch_ids = arch_ids
        self.arches = arches
        # self.idxs = sorted(list(self.arches.keys()))
        self.arch_names = []
        self.data_1d = data_1d
        self.data_2d = data_2d
        self.bkg_1d = 0.
        self.bkg_2d = 0.
        self.bkg_map_raw = 0.

        # Get Indices of selected arches
        self.idxs = []
        self.idxs_1d = []
        self.idxs_2d = []
        self.overall = False
        self.get_idxs()

        # Plotting Variables
        self.normChannel = None
        self.overlay = None

        # Image and Binned 2D Data
        self.image_data = (None, None)
        self.binned_data = (None, None)
        self.plot_data = [np.zeros(0), np.zeros(0)]
        self.plot_data_range = [[0, 0], [0, 0]]

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
        self.image_widget = pgImageWidget(lockAspect=1, raw=True)
        self.image_layout.addWidget(self.image_widget)

        # Regrouped Image pane setup
        self.binned_layout = Qt.QtWidgets.QHBoxLayout(self.ui.binnedFrame)
        self.binned_layout.setContentsMargins(0, 0, 0, 0)
        self.binned_layout.setSpacing(0)
        self.binned_widget = pgImageWidget()
        self.binned_layout.addWidget(self.binned_widget)

        # 1D/Waterfall Plot pane setup
        self.plot_layout = Qt.QtWidgets.QHBoxLayout(self.ui.plotFrame)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_layout.setSpacing(0)

        # 1D Plot pane setup
        self.plot_win = pg.GraphicsLayoutWidget()
        self.plot_layout.addWidget(self.plot_win)
        self.plot_viewBox = RectViewBox()
        self.plot = self.plot_win.addPlot(viewBox=self.plot_viewBox)
        self.curves = []
        self.legend = self.plot.addLegend()
        self.legend.setFlag(self.legend.ItemIgnoresTransformations, False)
        # self.legend.setLabelTextSize('10pt')

        self.pos_label = pg.LabelItem(justify='right')
        self.plot_win.addItem(self.pos_label)
        self.pos_label.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-20, 10))
        self.pos_label.setFixedWidth(1)
        self.trackMouse()

        # WF Plot pane setup
        self.wf_widget = pgImageWidget()
        # self.wf_widget = pmeshImageWidget()
        self.setup_wf_widget()
        self.plot_layout.addWidget(self.wf_widget)

        # Waterfall Plot setup
        if self.plotMethod == 'Waterfall':
            self.plot_win.setParent(None)
            self.plot_layout.addWidget(self.wf_widget)
        else:
            self.wf_widget.setParent(None)
            self.plot_layout.addWidget(self.plot_win)

        # All Windows Signal connections
        self.ui.normChannel.activated.connect(self.normUpdate)
        self.ui.setBkg.clicked.connect(self.setBkg)
        self.ui.scale.currentIndexChanged.connect(self.update_views)
        self.ui.cmap.currentIndexChanged.connect(self.update_views)
        self.ui.shareAxis.stateChanged.connect(self.update)
        self.ui.update2D.stateChanged.connect(self.enable_2D_buttons)

        # 2D Window Signal connections
        self.ui.imageUnit.activated.connect(self.update_binned)
        self.ui.imageUnit.activated.connect(self._update_slice_range)
        # self.ui.imageMask.stateChanged.connect(self.update_binned)

        # 1D Window Signal connections
        self.ui.plotMethod.currentIndexChanged.connect(self.update_plot_view)
        self.ui.yOffset.valueChanged.connect(self.update_plot_view)
        self.ui.plotUnit.activated.connect(self._set_slice_range)
        self.ui.plotUnit.activated.connect(self.update_plot)
        # self.ui.showLegend.stateChanged.connect(self.update_plot_view)
        self.ui.showLegend.stateChanged.connect(self.update_legend)
        self.ui.slice.stateChanged.connect(self.update_plot)
        self.ui.slice.stateChanged.connect(self._update_slice_range)
        self.ui.slice_center.valueChanged.connect(self.update_plot_range)
        self.ui.slice_width.valueChanged.connect(self.update_plot_range)
        self.ui.wf_options.clicked.connect(self.popup_wf_options)

        # Clear 1D Plot Buttons
        self.ui.clear_1D.clicked.connect(self.clear_1D)

        # Save Image/Data Buttons
        self.ui.save_2D.clicked.connect(self.save_image)
        self.ui.save_1D.clicked.connect(self.save_1D)

        # Initialize image units
        self.set_image_units()
        self._set_slice_range(initialize=True)

        # Setup Waterfall Options Popup
        self.wf_dialog = QDialog()
        self.wf_yaxis_widget = QCombo()
        self.wf_start_widget = QtWidgets.QDoubleSpinBox()
        self.wf_step_widget = QtWidgets.QDoubleSpinBox()
        self.wf_accept_button = QtWidgets.QPushButton('Okay')
        self.wf_cancel_button = QtWidgets.QPushButton('Cancel')

    def get_idxs(self):
        """ Return selected arch indices
        """
        # ic()
        self.idxs, self.idxs_1d, self.idxs_2d = [], [], []
        if len(self.arch_ids) == 0 or self.arch_ids[0] == 'No data':
            return

        # with self.sphere.sphere_lock:
        # if 'Overall' in self.arch_ids:
        if len(self.arch_ids) == len(self.sphere.arches.index) > 1:
            self.overall = True
            self.idxs = sorted(np.asarray(self.sphere.arches.index, dtype=int))
        else:
            self.overall = False
            self.idxs = sorted(self.arch_ids)

        try:
            self.idxs = list(np.asarray(self.idxs, dtype=int))
        except ValueError:
            return
        self.idxs_1d = [int(idx) for idx in self.idxs if idx in self.data_1d.keys()]
        self.idxs_2d = [int(idx) for idx in self.idxs if idx in self.data_2d.keys()]

    def update_plot_range(self):
        if self.ui.slice.isChecked():
            self.update_plot()

    def setup_1d_layout(self):
        """Setup the layout for 1D plot
        """
        self.wf_widget.setParent(None)
        self.plot_layout.addWidget(self.plot_win)

        self.ui.wf_options.setEnabled(False)
        if len(self.plot_data[1]) > 1:
            self.ui.wf_options.setEnabled(True)
            self.wf_yaxis_widget.setEnabled(False)

    def setup_wf_widget(self):
        self.plot_layout.addWidget(self.wf_widget)

        # Waterfall Plot setup
        if self.plotMethod == 'Waterfall':
            self.plot_win.setParent(None)
            self.plot_layout.addWidget(self.wf_widget)
        else:
            self.wf_widget.setParent(None)
            self.plot_layout.addWidget(self.plot_win)

    def setup_wf_layout(self):
        """Setup the layout for WF plot
        """
        self.plot_win.setParent(None)
        self.plot_layout.addWidget(self.wf_widget)

        self.ui.wf_options.setEnabled(True)
        self.wf_yaxis_widget.setEnabled(True)

    def popup_wf_options(self):
        """
        Popup Qt Window to select options for Waterfall Plot
        Options include Y-axis unit and number of points to skip
        """
        if self.wf_dialog.layout() is None:
            self.setup_wf_options_widget()

        self.wf_dialog.show()

    def setup_wf_options_widget(self):
        """
        Setup y-axis option for Waterfall plot
        Setup first image and step size for wf and overlay plots
        """
        layout = QtWidgets.QGridLayout()
        self.wf_dialog.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Y-Axis'), 0, 0)
        layout.addWidget(QtWidgets.QLabel('Start'), 0, 1)
        layout.addWidget(QtWidgets.QLabel('Step'), 0, 2)

        layout.addWidget(self.wf_yaxis_widget, 1, 0)
        layout.addWidget(self.wf_start_widget, 1, 1)
        layout.addWidget(self.wf_step_widget, 1, 2)

        layout.addWidget(self.wf_accept_button, 2, 1)
        layout.addWidget(self.wf_cancel_button, 2, 2)

        arch = self.data_1d[self.idxs_1d[0]]
        counters = list(arch.scan_info.keys())
        counters = ['Frame #', 'Time (s)', 'Time (minutes)'] + counters
        self.wf_yaxis_widget.addItems(counters)

        self.wf_start_widget.setDecimals(0)
        self.wf_start_widget.setRange(1, 1000)

        self.wf_step_widget.setDecimals(0)
        self.wf_step_widget.setRange(1, 100)

        self.wf_accept_button.clicked.connect(self.get_wf_option)
        self.wf_cancel_button.clicked.connect(self.close_wf_popup)

    def get_wf_option(self):
        self.wf_yaxis = self.wf_yaxis_widget.currentText()

        self.wf_start = int(self.wf_start_widget.value()) - 1
        self.wf_step = int(self.wf_step_widget.value())

        self.close_wf_popup()
        self.update_plot_view()

    def close_wf_popup(self):
        self.wf_dialog.close()

    def enable_2D_buttons(self):
        """Disable buttons if update 2D is unchecked"""
        pass

    def set_image_units(self):
        """Disable/Enable Qz-Qxy option if we are/are not in GI mode"""
        if self.sphere.gi:
            if self.ui.imageUnit.count() == 2:
                self.ui.imageUnit.addItem(_translate("Form", imageUnits[2]))
        else:
            if self.ui.imageUnit.count() == 3:
                self.ui.imageUnit.removeItem(2)

    def _updated(self):
        """Check if there is data to update
        """
        if (len(self.arch_ids) == 0) or (self.sphere.name == 'null_main'):
            return False
        if (len(self.data_1d) == 0) or (len(self.idxs_1d) == 0):
            return False
        # if self.ui.update2D.isChecked() and (len(self.idxs_2d) == 0) and (not self.overall):
        #     return False

        return True

    def update(self):
        """Updates image and plot frames based on toolbar options
        """
        # ic()
        self.get_idxs()

        if not self._updated():
            return True

        if self.ui.shareAxis.isChecked() and (self.ui.imageUnit.currentIndex() < 2):
            self.ui.plotUnit.setCurrentIndex(self.ui.imageUnit.currentIndex())
            self.ui.plotUnit.setEnabled(False)
            self.plot.setXLink(self.binned_widget.image_plot)
        else:
            self.plot.setXLink(None)
            self.ui.plotUnit.setEnabled(True)

        try:
            self.update_plot()
        except TypeError:
            return False

        if self.ui.update2D.isChecked():
            try:
                self.update_image()
            except TypeError:
                return False
            try:
                self.update_binned()
            except TypeError:
                return False

        # Apply label to 2D view
        if self.ui.update2D.isChecked():
            self.update_2d_label()

        return True

    def update_views(self):
        """Updates 2D (if flag is selected) and 1D views
        """
        if not self._updated():
            return True

        self.cmap = self.ui.cmap.currentText()
        self.plotMethod = self.ui.plotMethod.currentText()
        self.scale = self.ui.scale.currentText()

        if self.ui.update2D.isChecked():
            self.update_image_view()
            self.update_binned_view()
            self.update_2d_label()
        self.update_plot_view()

    def update_image(self):
        """Updates image plotted in image frame
        """
        mask = None
        if self.overall and len(self.arch_ids) > 1:
            data = self.get_sphere_map_raw()
        else:
            data = self.get_arches_map_raw()
            if data is None:
                return

            # Apply Mask
            arch_2d = self.data_2d[self.idxs_2d[0]]
            mask = arch_2d['mask']
        data = np.asarray(data, dtype=float)

        # Apply Mask
        global_mask = self.sphere.global_mask if self.sphere.global_mask is not None else []
        mask = mask if mask is not None else []
        mask = np.asarray(np.unique(np.append(mask, global_mask)), dtype=int)
        if len(mask) > 0:
            mask = np.unravel_index(mask, data.shape)
            data[mask] = np.nan

        # Subtract background
        data -= self.bkg_map_raw

        data = data.T[:, ::-1]

        # Get Bounding Rectangle
        rect = get_rect(np.arange(data.shape[0]), np.arange(data.shape[1]))

        self.image_data = (data, rect)
        self.update_image_view()

    def update_image_view(self):
        data, rect = self.image_data

        # self.image_widget.setImage(data.T[:, ::-1], scale=self.scale, cmap=self.cmap)
        self.image_widget.setImage(data, scale=self.scale, cmap=self.cmap)
        self.image_widget.setRect(rect)

        self.image_widget.image_plot.setLabel("bottom", 'x (Pixels)')
        self.image_widget.image_plot.setLabel("left", 'y (Pixels)')

    def update_binned(self):
        """Updates image plotted in image frame
        """
        if self.ui.shareAxis.isChecked() and (self.ui.imageUnit.currentIndex() < 2):
            self.ui.plotUnit.setCurrentIndex(self.ui.imageUnit.currentIndex())
            self.update_plot()

        # if 'Overall' in self.arch_ids:
        if self.overall and len(self.arch_ids) > 1:
            intensity, xdata, ydata = self.get_sphere_int_2d()
        else:
            intensity, xdata, ydata = self.get_arches_int_2d()

        if intensity is None:
            return

        # Subtract background
        intensity -= self.bkg_2d

        rect = get_rect(xdata, ydata)
        self.binned_data = (intensity, rect)
        self.update_binned_view()

        return

    def update_binned_view(self):
        data, rect = self.binned_data

        self.binned_widget.setImage(data.T[:, ::-1], scale=self.scale, cmap=self.cmap)
        self.binned_widget.setRect(rect)

        imageUnit = self.ui.imageUnit.currentIndex()
        self.binned_widget.image_plot.setLabel(
            "bottom", x_labels_2D[imageUnit], units=x_units_2D[imageUnit]
        )
        self.binned_widget.image_plot.setLabel(
            "left", y_labels_2D[imageUnit], units=y_units_2D[imageUnit]
        )

        self.show_slice_overlay()
        return data

    def update_2d_label(self):
        """Updates 2D Label
        """
        # Sets title text
        label = self.sphere.name
        if len(label) > 40:
            label = f'{label[:10]}.....{label[-30:]}'

        if (self.overall or self.sphere.single_img) and (len(self.arch_ids) > 1):
            self.ui.labelCurrent.setText(label)
        elif len(self.arch_ids) > 1:
            self.ui.labelCurrent.setText(f'{label} [Average]')
        else:
            self.ui.labelCurrent.setText(f'{label}_{self.arch_ids[0]}')

    def update_plot(self):
        """Updates data in plot frame
        """
        if (self.sphere.name == 'null_main') or (len(self.arch_ids) == 0):
            data = (np.arange(100), np.arange(100))
            return data

        # Get 1D data for all arches
        ydata, xdata = self.get_arches_int_1d()
        arch_names = [f'{self.sphere.name}_{i}' for i in self.idxs]

        # Subtract background
        ydata -= self.bkg_1d
        if ydata.ndim == 1:
            ydata = ydata[np.newaxis, :]

        if ((self.plot_data[0].shape == xdata.shape) and
                (self.plotMethod in ['Overlay', 'Waterfall'])):
            for (arch_name, data) in zip(arch_names, ydata):
                if arch_name not in self.arch_names:
                    self.plot_data[1] = np.vstack((self.plot_data[1], data))
                    self.arch_names.append(arch_name)
        else:
            self.plot_data = [xdata, ydata]
            self.arch_names.clear()
            self.arch_names = arch_names

        xdata, ydata = self.plot_data
        self.plot_data_range = [[xdata.min(), xdata.max()], [ydata.min(), ydata.max()]]
        self.update_plot_view()

        # self.save_1D(auto=True)

    def update_plot_view(self):
        """Updates 1D view of data in plot frame
        """
        if (len(self.arch_ids) == 0) or len(self.data_1d) == 0:
            return

        # Clear curves
        [curve.clear() for curve in self.curves]
        self.curves.clear()

        self.plotMethod = self.ui.plotMethod.currentText()
        self.ui.yOffset.setEnabled(False)
        if (self.plotMethod in ['Overlay', 'Single']) and (len(self.arch_names) > 1):
            self.ui.yOffset.setEnabled(True)

        # Only switch to WF plot if more than three curves. Definitely switch if more than 15!
        if (self.plotMethod == 'Waterfall' and len(self.plot_data[1]) > 3) or len(self.plot_data[1]) > 15:
            self.update_wf()
        else:
            self.update_1d_view()

    def update_1d_view(self):
        """Updates data in 1D plot Frame
        """
        self.setup_1d_layout()
        xdata_, ydata_ = self.plot_data
        s_xdata, ydata = xdata_.copy(), ydata_.copy()

        int_label = 'I'
        if self.normChannel:
            int_label = f'I / {self.normChannel}'

        self.plot.getAxis("left").setLogMode(False)
        ylabel = f'{int_label} (a.u.)'
        if self.scale == 'Log':
            if ydata.min() < 1:
                ydata -= (ydata.min() - 1.)
            ydata = np.log10(ydata)
            self.plot.getAxis("left").setLogMode(True)
            ylabel = f'Log {int_label}(a.u.)'
        elif self.scale == 'Sqrt':
            if ydata.min() < 0.:
                ydata_ = np.sqrt(np.abs(ydata))
                ydata_[ydata < 0] *= -1
                ydata = ydata_
            else:
                ydata = np.sqrt(ydata)
            ylabel = f'<math>&radic;</math>{int_label} (a.u.)'

        if ((self.plotMethod in ['Overlay', 'Waterfall']) or
                ((self.plotMethod == 'Single') and (ydata.shape[0] > 1))):
            ydata = ydata[self.wf_start::self.wf_step]
            self.setup_curves()

            offset = self.ui.yOffset.value()
            y_offset = offset / 100 * (self.plot_data_range[1][1] - self.plot_data_range[1][0])
            for nn, (curve, s_ydata) in enumerate(zip(self.curves, ydata)):
                curve.setData(s_xdata, s_ydata + y_offset*nn)

        else:
            self.setup_curves()
            s_ydata = ydata
            if self.plotMethod == 'Average':
                s_ydata = np.nanmean(s_ydata, 0)
            elif self.plotMethod == 'Sum':
                s_ydata = np.nansum(s_ydata, 0)

            self.curves[0].setData(s_xdata, s_ydata.squeeze())

        # Apply labels to plot
        plotUnit = self.ui.plotUnit.currentIndex()
        self.plot.setLabel("bottom", x_labels_1D[plotUnit], units=x_units_1D[plotUnit])
        self.plot.setLabel("left", ylabel)

        return s_xdata, s_ydata

    def update_wf(self):
        """Updates data in 1D plot Frame
        """
        self.setup_wf_layout()

        xdata_, data_ = self.plot_data
        s_xdata, data = xdata_.copy(), data_.copy()
        data = data[self.wf_start::self.wf_step, :]

        # Set YAxis Unit
        if self.wf_yaxis == 'Frame #':
            s_ydata = np.asarray(np.arange(data.shape[0]) + self.wf_start + 1, dtype=float)
        else:
            # TODO: Fix below for more WF options
            try:
                if self.wf_yaxis == 'Time (s)':
                    s_ydata = np.asarray([self.data_1d[idx].scan_info['epoch'] for idx in self.idxs])
                    s_ydata -= s_ydata.min()
                elif self.wf_yaxis == 'Time (minutes)':
                    s_ydata = np.asarray([self.data_1d[idx].scan_info['epoch'] for idx in self.idxs])/60.
                    s_ydata -= s_ydata.min()
                else:
                    s_ydata = np.asarray([self.data_1d[idx].scan_info[self.wf_yaxis] for idx in self.idxs])

                s_ydata = s_ydata[self.wf_start::self.wf_step]
            except KeyError:
                print('Counter not present in metadata')

        # rect = get_rect(s_xdata, np.arange(data.shape[0]))
        rect = get_rect(s_xdata, s_ydata)

        self.wf_widget.setImage(data.T, scale=self.scale, cmap=self.cmap)
        self.wf_widget.setRect(rect)

        plotUnit = self.ui.plotUnit.currentIndex()
        self.wf_widget.image_plot.setLabel("bottom", x_labels_1D[plotUnit],
                                           units=x_units_1D[plotUnit])
        self.wf_widget.image_plot.setLabel("left", self.wf_yaxis)

    def get_arches_map_raw(self, idxs=None):
        """Return 2D arch data for multiple arches (averaged)"""
        if idxs is None:
            # idxs = self.idxs
            idxs = self.idxs_2d

        intensity, ctr = 0., 0
        for nn, idx in enumerate(idxs):
            # arch = self.arches[int(idx)]
            arch_1d = self.data_1d[int(idx)]
            arch_2d = self.data_2d[int(idx)]
            for kk in range(3):
                try:
                    intensity += self.normalize(arch_2d['map_raw']-arch_2d['bg_raw'],
                                                arch_1d.scan_info)
                    ctr += 1
                    break
                except ValueError:
                    time.sleep(0.5)

        if ctr > 0:
            intensity /= ctr
        else:
            return None

        return np.asarray(intensity, dtype=float)

    def get_sphere_map_raw(self):
        """Returns data and QRect for data in sphere
        """
        with self.sphere.sphere_lock:
            map_raw = np.asarray(self.sphere.overall_raw, dtype=float)
            if map_raw.ndim < 2:
                self.sphere.load_from_h5(data_only=True)
                map_raw = np.asarray(self.sphere.overall_raw, dtype=float)

            norm_fac = len(self.sphere.arches.index)
            if self.normChannel:
                norm = self.sphere.scan_data[self.normChannel].sum()
                if norm > 0:
                    norm_fac = norm

            return map_raw/norm_fac

    def get_arches_int_2d(self, idxs=None):
        """Return 2D arch data for multiple arches (averaged)"""
        if idxs is None:
            idxs = self.idxs_2d

        if len(idxs) > 1:
            intensity = self.get_int_2d(self.arches['sum_int_2d'])
            xdata, ydata = self.get_xydata(self.arches['sum_int_2d'])
            return intensity, xdata, ydata

        # intensity, n_arches = 0., 0
        # for nn, idx in enumerate(idxs):
        idx = idxs[0]
        arch_1d = self.data_1d[int(idx)]
        arch_2d = self.data_2d[int(idx)]
        # arch_intensity = self.get_int_2d(arch_2d['int_2d'], arch_1d)
        intensity = self.get_int_2d(arch_2d['int_2d'], arch_1d)
        # if (arch_intensity.ndim > 1) and (arch_intensity.shape[0] != 0):
        #     intensity += arch_intensity
        #     arch_xy = arch_2d
        #     n_arches += 1

        # if n_arches == 0:
        if intensity.ndim != 2:
            return None, None, None

        # intensity /= n_arches

        # xdata, ydata = self.get_xydata(arch_xy['int_2d'])
        xdata, ydata = self.get_xydata(arch_2d['int_2d'])
        return np.asarray(intensity, dtype=float), xdata, ydata

    def get_sphere_int_2d(self):
        """Returns data and QRect for data in sphere
        """
        with self.sphere.sphere_lock:
            int_2d = self.sphere.bai_2d

        intensity = self.get_int_2d(int_2d, normalize=True)

        xdata, ydata = self.get_xydata(int_2d)
        return intensity, xdata, ydata

    def get_arches_int_1d(self, idxs=None, rv='all'):
        """Return 1D data for multiple arches"""
        if idxs is None:
            idxs = self.idxs_1d

        ydata = 0.
        for nn, idx in enumerate(idxs):
            arch_1d = self.data_1d[int(idx)]
            arch_2d = self.data_2d.get(int(idx), None)
            xdata, s_ydata = self.get_int_1d(arch_1d, arch_2d, idx)
            if nn == 0:
                ydata = s_ydata
            else:
                ydata = np.vstack((ydata, s_ydata))

        if ydata.ndim == 2:
            if rv == 'average':
                ydata = np.nanmean(ydata, 0)
            elif rv == 'sum':
                ydata = np.nansum(ydata, 0)

        return ydata, xdata

    def get_int_2d(self, int_2d, arch_1d=None, normalize=True):
        """Returns the appropriate 2D data depending on the chosen axes
        I(Q, Chi) or I(Qz, Qxy)
        """
        if self.ui.imageUnit.currentIndex() == 0:
            intensity_2d = int_2d.i_qChi
        elif self.ui.imageUnit.currentIndex() == 1:
            intensity_2d = int_2d.i_tthChi
        else:
            intensity_2d = int_2d.i_QxyQz
        intensity = np.asarray(intensity_2d.copy(), dtype=float)

        if normalize:
            if arch_1d is not None:
                intensity = self.normalize(intensity, arch_1d.scan_info)
            else:
                norm_fac = len(self.sphere.arches.index)
                if self.normChannel:
                    norm = self.sphere.scan_data[self.normChannel].sum()
                    if norm > 0:
                        norm_fac = norm
                intensity /= norm_fac

        return intensity

    def get_int_1d(self, arch, arch_2d, idx):
        """Returns 1D integrated data for arch. If range is specified,
        it returns integrated data over that range
        """
        if self.ui.plotUnit.currentIndex() != 2:
            if not self.ui.slice.isChecked():
                int_1d = arch.int_1d
                intensity = int_1d.norm
                ydata = self.normalize(intensity, arch.scan_info)
                xdata = self.get_xdata(int_1d)
                return xdata, ydata

        if arch_2d is None:
            return None, None

        # If a particular Chi Range is chosen...
        intensity = self.get_int_2d(arch_2d['int_2d'], arch, normalize=False)
        q, tth, chi = arch_2d['int_2d'].q, arch_2d['int_2d'].ttheta, arch_2d['int_2d'].chi

        xdata_list = [q, tth, chi]
        xdata = xdata_list[self.ui.plotUnit.currentIndex()]

        center = self.ui.slice_center.value()
        width = self.ui.slice_width.value()
        _range = [center - width, center + width]

        _inds = np.s_[:]
        if self.ui.plotUnit.currentIndex() < 2:
            slice_axis = Chi
            if self.ui.slice.isChecked():
                _inds = (_range[0] <= chi) & (chi <= _range[1])
            ydata = np.nanmean(intensity[_inds, :], axis=0)
        else:
            if self.ui.imageUnit.currentIndex() != 1:
                slice_axis = 'Q'
                if self.ui.slice.isChecked():
                    _inds = (_range[0] <= q) & (q <= _range[1])
            else:
                slice_axis = f'2{Th}'
                if self.ui.slice.isChecked():
                    _inds = (_range[0] <= tth) & (tth <= _range[1])
            ydata = np.nanmean(intensity[:, _inds], axis=1)

        self.ui.slice.setText(f'{slice_axis} Range')
        self.show_slice_overlay()

        ydata = self.normalize(ydata, arch.scan_info)
        return xdata, ydata

    def get_xydata(self, int_2d):
        """Reads the unit box and returns appropriate xdata

        args:
            box: QComboBox, list of options
            int_data: int_nd_data object, data to parse

        returns:
            xdata: numpy array, x axis data for plot.
        """
        imageUnit = self.ui.imageUnit.currentIndex()
        if imageUnit == 0:  # Q-Chi
            xdata, ydata = int_2d.q, int_2d.chi
        elif imageUnit == 1:  # 2Th-Chi
            xdata, ydata = int_2d.ttheta, int_2d.chi
        else:  # Qzx-Qz
            xdata, ydata = int_2d.qxy, int_2d.qz

        return xdata, ydata

    def get_xdata(self, int_data):
        """Reads the unit box and returns appropriate xdata

        args:
            box: QComboBox, list of options
            int_data: int_nd_data object, data to parse

        returns:
            xdata: numpy array, x axis data for plot.
        """
        unit = self.ui.plotUnit.currentIndex()
        if unit == 0:
            xdata = int_data.q
        elif unit == 1:
            xdata = int_data.ttheta
        else:
            xdata = self.get_chi_1d()
        return xdata

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
        try:
            intensity = np.asarray(int_data.copy(), dtype=float)
        except AttributeError:
            return np.zeros((10, 10))

        # normChannel = self.ui.normChannel.currentText()
        # if normChannel in scan_info.keys():
        #     self.normChannel = normChannel
        # elif normChannel.upper() in scan_info.keys():
        #     self.normChannel = normChannel.upper()
        # elif normChannel.lower() in scan_info.keys():
        #     self.normChannel = normChannel.lower()
        # else:
        #     self.normChannel = None

        normChannel = self.get_normChannel(scan_data_keys=scan_info.keys())
        if normChannel and (scan_info[normChannel] > 0):
            intensity /= scan_info[normChannel]

        return intensity

    def get_normChannel(self, scan_data_keys=None):
        """Check to see if normalization channel exists in metadata and return name"""
        normChannel = self.ui.normChannel.currentText()
        if normChannel == 'sec':
            normChannel = {'sec', 'seconds', 'Seconds', 'Sec', 'SECONDS', 'SEC'}
        else:
            normChannel = {normChannel, normChannel.lower(), normChannel.upper()}
        if scan_data_keys is None:
            scan_data_keys = self.sphere.scan_data.columns
        normChannel = normChannel.intersection(scan_data_keys)
        return normChannel.pop() if len(normChannel) > 0 else None

    def normUpdate(self):
        """Update plots if norm channel exists"""
        self.normChannel = self.get_normChannel()
        if self.normChannel and (self.sphere.scan_data[self.normChannel].sum() == 0.):
            self.normChannel = None
        self.update()

    def setBkg(self):
        """Sets selected points as background.
        If background is already selected, it unsets it"""
        if (len(self.arch_ids) == 0) or (len(self.idxs) == 0):
            return

        if self.ui.setBkg.text() == 'Set Bkg':
            idxs = self.arch_ids
            # if 'Overall' in self.arch_ids:
            if self.overall:
                idxs = sorted(list(self.sphere.arches.index))

            self.bkg_1d, _ = self.get_arches_int_1d(idxs, rv='average')
            self.bkg_2d, _, _ = self.get_arches_int_2d(idxs)
            self.bkg_map_raw = self.get_arches_map_raw(idxs)
            if self.bkg_map_raw is None:
                self.bkg_map_raw = 0.
            self.ui.setBkg.setText('Clear Bkg')
        else:
            self.bkg_1d = 0.
            self.bkg_2d = 0.
            self.bkg_map_raw = 0.
            self.ui.setBkg.setText('Set Bkg')

        self.update()
        return

    def setup_curves(self):
        """Initialize curves for line plots
        """
        self.curves.clear()
        self.legend.clear()

        arch_ids = self.arch_names[self.wf_start::self.wf_step]
        if (self.plotMethod in ['Sum', 'Average']) and (len(self.arch_names) > 1):
            arch_ids = f'{self.plotMethod} [{self.arch_names[0]}'
            for arch_name in self.arch_names[1:]:
                arch_ids += f', {arch_name}'
            arch_ids = [arch_ids + ']']

        colors = self.get_colors()
        self.curves = [self.plot.plot(
            pen=color,
            symbolBrush=color,
            symbolPen=color,
            symbolSize=4,
            name=arch_id,
        ) for (color, arch_id) in zip(colors, arch_ids)]

        if not self.ui.showLegend.isChecked():
            self.legend.clear()

    def clear_1D(self):
        """Initialize curves for line plots
        """
        self.arch_names.clear()
        self.arch_ids.clear()
        self.plot_data = [np.zeros(0), np.zeros(0)]
        self.setup_1d_layout()
        self.plot.clear()

    def update_legend(self):
        if not self.ui.showLegend.isChecked():
            self.legend.hide()
        else:
            self.legend.show()

    def _set_slice_range(self, _=None, initialize=False):
        if self.ui.plotUnit.currentIndex() == 2:
            if self.ui.imageUnit.currentIndex() != 1:
                self.ui.slice.setText('Q Range')
                self.ui.slice_center.setRange(0, 25)
                self.ui.slice_width.setRange(0, 30)
                self.ui.slice_center.setSingleStep(0.1)
                self.ui.slice_width.setSingleStep(0.1)
                if initialize:
                    self.ui.slice_center.setValue(2)
                    self.ui.slice_width.setValue(0.5)
            else:
                self.ui.slice.setText(f'2{Th} Range')
                self.ui.slice_center.setRange(-180, 180)
                self.ui.slice_width.setRange(0, 180)
                self.ui.slice_center.setValue(10)
                self.ui.slice_width.setValue(5)
                self.ui.slice_center.setSingleStep(1)
                self.ui.slice_width.setSingleStep(1)
                if initialize:
                    self.ui.slice_center.setValue(10)
                    self.ui.slice_width.setValue(5)
        else:
            self.ui.slice.setText(f'{Chi} Range')
            self.ui.slice_center.setMinimum(-180)
            self.ui.slice_center.setMaximum(180)
            self.ui.slice_width.setMinimum(0)
            self.ui.slice_width.setMaximum(270)
            self.ui.slice_center.setSingleStep(1)
            self.ui.slice_width.setSingleStep(1)
            if initialize:
                self.ui.slice_center.setProperty("value", 0)
                self.ui.slice_width.setProperty("value", 10)

    def _update_slice_range(self):

        if not self.ui.slice.isChecked():
            self.clear_slice_overlay()
            return

        imageUnit = self.ui.imageUnit.currentIndex()
        plotUnit = self.ui.plotUnit.currentIndex()
        if (plotUnit != 2) or (imageUnit == 2):
            self.update_plot()
            return

        cen = self.ui.slice_center.value()
        wid = self.ui.slice_width.value()
        _range = np.array([cen - wid, cen + wid])
        wavelength = self.data_1d[self.idxs_1d[0]].integrator.wavelength

        if imageUnit == 0:
            if self.ui.slice.text() == f'2{Th} Range':
                self.ui.slice.setText('Q Range')
                _range = ((4 * np.pi / (wavelength * 1e10)) * np.sin(np.radians(_range / 2)))
                # cen = ((4 * np.pi / (wavelength * 1e10)) * np.sin(np.radians(cen / 2)))
                # wid = ((4 * np.pi / (wavelength * 1e10)) * np.sin(np.radians(wid / 2)))
        else:
            if self.ui.slice.text() == f'Q Range':
                self.ui.slice.setText(f'2{Th} Range')
                _range = (2 * np.degrees(np.arcsin(_range * (wavelength * 1e10) / (4 * np.pi))))
                # cen = (2 * np.degrees(np.arcsin(cen * (wavelength * 1e10) / (4 * np.pi))))
                # wid = (2 * np.degrees(np.arcsin(wid * (wavelength * 1e10) / (4 * np.pi))))

        cen = (_range[-1] + _range[0]) / 2.
        wid = (_range[-1] - _range[0]) / 2.
        self.ui.slice_center.setValue(cen)
        self.ui.slice_width.setValue(wid)
        self._set_slice_range()

        self.show_slice_overlay()

    def show_slice_overlay(self):
        """
        Shows the slice integration region on 2D Binned plot
        """
        self.clear_slice_overlay()

        if (not self.ui.slice.isChecked()) or (self.ui.imageUnit.currentIndex() == 2):
            return

        center = self.ui.slice_center.value()
        width = self.ui.slice_width.value()
        _range = [center-width, center+width]

        binned_data, rect = self.binned_data

        if self.ui.plotUnit.currentIndex() < 2:
            _range = [max(rect.top(), _range[0]), min(rect.top() + rect.height(), _range[1])]
            width = (_range[1] - _range[0])/2.
            self.overlay = ROI(
                [rect.left(), _range[0]], [rect.width(), 2*width],
                pen=(255, 255, 255),
                maxBounds=rect
            )
        else:
            _range = [max(rect.left(), _range[0]), min(rect.left() + rect.width(), _range[1])]
            width = (_range[1] - _range[0])/2.
            self.overlay = ROI(
                [_range[0], rect.top()], [2*width, rect.height()],
                pen=(255, 255, 255),
                maxBounds=rect
            )

        self.binned_widget.imageViewBox.addItem(self.overlay, ignoreBounds=True)

    def clear_slice_overlay(self):
        """Clear the overlay that shows integration slice"""
        if self.overlay is not None:
            self.binned_widget.imageViewBox.removeItem(self.overlay)
            self.overlay = None

    def save_image(self):
        """Saves currently displayed image. Formats are automatically
        grabbed from Qt. Also implements tiff saving.
        """
        ext_filter = "Images ("
        for f in formats:
            ext_filter += "*." + f + " "

        dialog = QFileDialog()
        fname, _ = dialog.getSaveFileName(
            dialog,
            filter=ext_filter,
            caption='Save as...',
            options=QFileDialog.DontUseNativeDialog
        )
        if fname == '':
            return

        # Save as image
        data, rect = self.binned_data
        scene = self.binned_widget.imageViewBox.scene()
        exporter = pyqtgraph.exporters.ImageExporter(scene)
        h = exporter.params.param('height').value()
        w = exporter.params.param('width').value()
        h_new = 2000
        w_new = int(np.round(w/h * h_new, 0))
        exporter.params.param('height').setValue(h_new)
        exporter.params.param('width').setValue(w_new)
        exporter.export(fname)

        # Save as Numpy array as well
        directory, base_name, ext = split_file_name(fname)
        save_fname = os.path.join(directory, base_name)
        np.save(f'{save_fname}.npy', data)

    def save_1D(self, auto=False):
        """Saves currently displayed data. Currently supports .xye
        and .csv.
        """
        fname = f'{self.sphere.name}'
        if not auto:
            path = QFileDialog().getExistingDirectory(
                caption='Choose Save Directory',
                directory='',
                options=(QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog)
            )

            inp_dialog = QtWidgets.QInputDialog()
            suffix, ok = inp_dialog.getText(inp_dialog, 'Enter Suffix to be added to File Name', 'Suffix', text='')
            if not ok:
                return
            if suffix != '':
                fname += f'_{suffix}'
        else:
            path = os.path.dirname(self.sphere.data_file)
            path = os.path.join(path, self.sphere.name)
            Path(path).mkdir(parents=True, exist_ok=True)

        fname = os.path.join(path, fname)

        xdata, ydata = self.plot_data
        if self.plotMethod in ['Average', 'Sum']:
            if self.plotMethod == 'Average':
                s_ydata = np.nanmean(ydata, 0)
            else:
                s_ydata = np.nansum(ydata, 0)

            # Write to xye
            xye_fname = f'{fname}.xye'
            ut.write_xye(xye_fname, xdata, s_ydata)

            # Write to csv
            csv_fname = f'{fname}.csv'
            ut.write_csv(csv_fname, xdata, s_ydata)

        idxs = [arch.replace(f'{self.sphere.name}_', '') for arch in self.arch_names]
        for nn, (s_ydata, idx) in enumerate(zip(ydata, idxs)):
            # Write to xye
            xye_fname = f'{fname}_{str(idx).zfill(4)}.xye'
            ut.write_xye(xye_fname, xdata, s_ydata)

            # Write to csv
            csv_fname = f'{fname}_{str(idx).zfill(4)}.csv'
            ut.write_csv(csv_fname, xdata, s_ydata)

        if not auto:
            scene = self.plot_viewBox.scene()
            exporter = pyqtgraph.exporters.ImageExporter(scene)
            h = exporter.params.param('height').value()
            w = exporter.params.param('width').value()
            h_new = 600
            w_new = int(np.round(w/h * h_new, 0))
            exporter.params.param('height').setValue(h_new)
            exporter.params.param('width').setValue(w_new)
            exporter.export(fname + '.png')

    def get_colors(self):
        # Define color tuples

        colors = (1, 1, 1)
        if self.cmap == 'Default':
            colors_tuples = [cm.get_cmap('tab10'), cm.get_cmap('Set3'), cm.get_cmap('tab20b', 5)]
            for nn, color_tuples in enumerate(colors_tuples):
                if nn == 0:
                    colors = np.asarray(color_tuples.colors)
                else:
                    colors = np.vstack((colors, np.asarray(color_tuples.colors)[:, 0:3]))

            colors_tuples = cm.get_cmap('jet')
            more_colors = colors_tuples(np.linspace(0, 1, len(self.arch_names)))
            colors = np.vstack((colors, more_colors[:, 0:3]))

        else:
            try:
                colors_tuples = cm.get_cmap(self.cmap)
            except ValueError:
                colors_tuples = cm.get_cmap('jet', 256)
            colors = colors_tuples(np.linspace(0, 1, len(self.arch_names)))[:, 0:3]

        # colors = np.round(colors * [255, 255, 255, 1]).astype(int)
        colors = np.round(colors * [255, 255, 255]).astype(int)
        colors = [tuple(color[:3]) for color in colors]

        return colors

    def get_profile_chi(self, arch):
        """
        Args:
            arch (EwaldArch Object):

        Returns:
            intensity (ndarray): Intensity integrated along Chi
                                 over a range of Q specified by UI
        """
        pass

    def get_chi_1d(self, arch):
        """
        Args:
            arch (EwaldArch Object):

        Returns:
            intensity (ndarray): Intensity integrated along Chi
                                 over a range of Q specified by UI
        """
        pass

    def trackMouse(self):
        """
        Sets up mouse trancking
        Returns: x, y (z) coordinates on screen

        """
        proxy = pg.SignalProxy(signal=self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        proxy.signal.connect(self.mouseMoved)

    def mouseMoved(self, pos):
        if len(self.curves) == 0:
            return

        if self.plot.sceneBoundingRect().contains(pos):
            vb = self.plot.vb
            self.plot_win.setCursor(pyQt.CrossCursor)
            mousePoint = vb.mapSceneToView(pos)
            self.pos_label.setText(f'x={mousePoint.x():.2f}, y={mousePoint.y():.2e}')
        else:
            self.pos_label.setText('')
            self.plot_win.setCursor(pyQt.ArrowCursor)

    def update_wf_pmesh(self):
        """Updates data in 1D plot Frame
        """
        self.setup_wf_layout()

        xdata_, data_ = self.plot_data
        s_xdata, data = xdata_.copy(), data_.copy()
        data = data[self.wf_start::self.wf_step, :]

        x_max, x_min = np.max(s_xdata), np.min(s_xdata)
        x_step = (x_max - x_min)/len(s_xdata)
        s_xdata = np.append(s_xdata, [x_max + x_step])
        s_xdata -= x_step/2
        s_xdata = np.tile(s_xdata, (data.shape[0]+1, 1)).T

        # Set YAxis Unit
        if self.wf_yaxis == 'Frame #':
            s_ydata = np.asarray(np.arange(data.shape[0]) + self.wf_start + 1, dtype=float)
        else:
            # TODO: Fix below for more WF options
            if self.wf_yaxis == 'Time (s)':
                s_ydata = np.asarray([self.data_1d[idx].scan_info['epoch'] for idx in self.idxs])
                s_ydata -= s_ydata.min()
            elif self.wf_yaxis == 'Time (minutes)':
                s_ydata = np.asarray([self.data_1d[idx].scan_info['epoch'] for idx in self.idxs])/60.
                s_ydata -= s_ydata.min()
            else:
                s_ydata = np.asarray([self.data_1d[idx].scan_info[self.wf_yaxis] for idx in self.idxs])

            s_ydata = s_ydata[self.wf_start::self.wf_step]

        y_max, y_min = np.max(s_ydata), np.min(s_ydata)
        y_step = (y_max - y_min)/len(s_ydata)
        s_ydata = np.append(s_ydata, [y_max + y_step])
        s_ydata -= y_step/2.
        s_ydata = np.tile(s_ydata, (data.shape[1]+1, 1))

        # self.wf_widget.setImage(data.T, scale=self.scale, cmap=self.cmap)
        levels = np.nanpercentile(data, (1, 98))
        self.wf_widget.imageItem.setLevels(levels)
        self.wf_widget.imageItem.setData(s_xdata, s_ydata, data.T)
        self.wf_widget.imageItem.informViewBoundsChanged()

        # rect = get_rect(s_xdata, np.arange(data.shape[0]))
        rect = get_rect(s_xdata[:, 0], s_ydata[0])
        self.wf_widget.setRect(rect)

        plotUnit = self.ui.plotUnit.currentIndex()
        self.wf_widget.image_plot.setLabel("bottom", x_labels_1D[plotUnit],
                                           units=x_units_1D[plotUnit])
        self.wf_widget.image_plot.setLabel("left", self.wf_yaxis)

        return data
