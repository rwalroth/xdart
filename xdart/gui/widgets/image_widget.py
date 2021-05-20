# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import traceback

# Other imports
import numpy as np
from matplotlib import cm

# This module imports
from ..gui_utils import RectViewBox
from ..widgets import RangeSliderWidget
import xdart.utils as ut
from .imageWidgetUI import Ui_Form
import pyqtgraph_extensions as pgx

# Qt imports
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
QFileDialog = QtWidgets.QFileDialog


class XDImageWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # Setup range slider
        #self.rangeSlider = RangeSlider(self)
        #self.sliderLayout = Qt.QtWidgets.QVBoxLayout(self.ui.sliderFrame)
        #self.sliderLayout.addWidget(self.rangeSlider)

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.histogram = pg.HistogramLUTWidget(self.image_win)
        self.ui.toolLayout.addWidget(self.histogram, 1, 0, 1, 2)
        self.imageViewBox = RectViewBox()
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        self.imageItem = pg.ImageItem(colormap=cm.get_cmap('viridis'))

        self.image_plot.addItem(self.imageItem)
        self.histogram.setImageItem(self.imageItem)
        self.histogram.vb.setMouseEnabled(x=False, y=False)
        self.raw_image = np.array(0)
        self.norm_image = np.array(0)
        self.displayed_image = np.array(0)
        starter = np.random.normal(50, 10, 256*256)
        starter.sort()
        self.setImage(starter.reshape((256, 256)))

        self.ui.logButton.toggled.connect(self.update_image)
        self.ui.cmapBox.currentIndexChanged.connect(self.set_cmap)
        self.set_cmap(0)

        self.show()

    def setImage(self, image, rect=None):
        self.raw_image = image[()]
        self.norm_image = normalize(self.raw_image)
        self.displayed_image = self.norm_image[()]
        self.update_image()
        if rect is not None:
            self.imageItem.setRect(rect)

    def setRect(self, rect):
        self.imageItem.setRect(rect)

    def update_image(self, q=None):
        self.displayed_image = np.copy(self.raw_image)
        if self.ui.logButton.isChecked():
            self.displayed_image[self.displayed_image < 0] = 0
            minval = self.displayed_image[self.displayed_image > 0].min()
            self.displayed_image = np.log10(self.displayed_image/minval + 1)
            self.imageItem.setImage(self.displayed_image)
            self.histogram.item.axis.setScale(self.raw_image.max() /
                                              self.displayed_image.max())
        else:
            self.imageItem.setImage(self.displayed_image)
            self.histogram.item.axis.setScale(None)

    def set_cmap(self, index):
        self.histogram.item.gradient.loadPreset(
            self.ui.cmapBox.itemText(index)
        )


class XDImageItem(pgx.ImageItem):
    def __init__(self, parent=None, raw=False):
        super().__init__(parent)

        self.pos_label = pg.LabelItem(justify='right')
        self.raw = raw

    def hoverEvent(self, ev):
        """Show the position, pixel, and value under the mouse cursor.
        """
        if ev.isExit():
            self.pos_label.setText('')
            return

        data = self.image
        pos = ev.pos()
        # i, j = pos.y(), pos.x()
        i, j = pos.x(), pos.y()
        i = int(np.clip(i, 0, data.shape[0] - 1))
        j = int(np.clip(j, 0, data.shape[1] - 1))
        val = data[i, j]
        ppos = self.mapToParent(pos)
        x, y = ppos.x(), ppos.y()
        if self.raw:
            self.pos_label.setText(f'{x:0.0f}, {y:0.0f} [{val:.2e}]')
        else:
            self.pos_label.setText(f'{x:0.2f}, {y:0.2f} [{val:.2e}]')


class pgxImageWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None, lockAspect=False, raw=False):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # Some options for Raw Images
        self.raw = raw

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)

        self.image_win = pgx.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.imageViewBox = RectViewBox(lockAspect=lockAspect)
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        # self.imageItem = pgx.ImageItem()
        self.imageItem = XDImageItem(raw=self.raw)
        self.image_plot.addItem(self.imageItem)

        # Make Label Item for showing position
        self.make_pos_label()

        self.histogram = self.image_win.addColorBar(image=self.imageItem)
        self.histogram.layout.setContentsMargins(0, 20, 0, 50)

        self.raw_image = np.zeros(0)
        self.displayed_image = np.zeros(0)
        self.show()

    def make_pos_label(self, itemPos=(1, 0), parentPos=(1, 1), offset=(0, -20)):
        self.image_win.addItem(self.imageItem.pos_label)
        self.imageItem.pos_label.anchor(itemPos=itemPos, parentPos=parentPos, offset=offset)
        self.imageItem.pos_label.setFixedWidth(1)

    def setImage(self, image, rect=None,
                 scale='Linear', cmap='viridis',
                 **kwargs):
        self.raw_image = image[()]
        self.update_image(scale, cmap, **kwargs)
        if rect is not None:
            self.imageItem.setRect(rect)

    def setRect(self, rect):
        self.imageItem.setRect(rect)

    def update_image(self, scale='Linear', cmap='viridis', **kwargs):
        self.displayed_image = np.asarray(np.copy(self.raw_image), dtype=float)
        if scale == 'Log':
            # self.displayed_image[self.displayed_image < 0] = 0
            # minval = self.displayed_image[self.displayed_image > 0].min()
            # self.displayed_image = np.log10(self.displayed_image/minval + 1)
            min_val = np.min(self.displayed_image)
            if min_val < 1:
                # self.displayed_image -= (np.min(self.displayed_image) - 1.)
                self.displayed_image -= (min_val - 1)
            self.displayed_image = np.log10(self.displayed_image)

            levels = np.nanpercentile(self.displayed_image, (0.1, 99.9))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            self.histogram.axis.setLogMode(True)
        elif scale == 'Sqrt':
            min_val = np.min(self.displayed_image)
            if min_val < 0:
                img = np.sqrt(np.abs(self.displayed_image))
                img[self.displayed_image < 0] *= -1
                self.displayed_image = img
                # self.displayed_image -= min_val
            else:
                self.displayed_image = np.sqrt(self.displayed_image)

            levels = np.nanpercentile(self.displayed_image, (0.5, 99.5))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            self.histogram.axis.setLogMode(False)
        else:
            levels = np.nanpercentile(self.displayed_image, (1, 99))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            self.histogram.axis.setLogMode(False)

        self.histogram.images[-1].levels = levels
        self.histogram.imageLevelsChanged(self.imageItem)
        self.set_cmap(cmap)

    def set_cmap(self, cmap):
        if cmap == 'Default':
            cmap = 'viridis'
        self.imageItem.setLookupTable(pgx.get_colormap_lut(cmap))


class XDPlotWidget(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.pos_label = pg.LabelItem(justify='right')
        self.plot_viewBox = RectViewBox()
        self.plot = self.plot_win.addPlot(viewBox=self.plot_viewBox)
        self.legend = self.plot.addLegend()
        self.curves = []

        self.make_pos_label()

    def make_pos_label(self):
        self.addItem(self.pos_label)
        self.pos_label.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-20, 10))
        self.pos_label.setFixedWidth(1)
        self.setup_crosshair()


def normalize(arr):
    """

    Parameters
    ----------
    arr : numpy.ndarray
    """
    minval = arr.min()
    maxval = arr.max()
    if maxval > minval:
        return (arr - minval) / (maxval - minval)
    else:
        return np.ones_like(arr)


def sliced(arr, ceiling):
    out = np.copy(arr)
    maxval = arr.max() * (ceiling/100)
    out[out > maxval] = maxval
    return out
