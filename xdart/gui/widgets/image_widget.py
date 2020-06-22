# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import traceback

# Other imports
import numpy as np
from matplotlib import cm

# Qt imports
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
QFileDialog = QtWidgets.QFileDialog

# This module imports
from ..gui_utils import RectViewBox
from ..widgets import RangeSliderWidget
import xdart.utils as ut
from .imageWidgetUI import Ui_Form


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
        #self.rangeSlider.setValue(99)
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
            #self.histogram.item.axis.setLogMode(True)
        else:
            self.imageItem.setImage(self.displayed_image)
            self.histogram.item.axis.setScale(None)
            #self.histogram.item.axis.setLogMode(False)

    def set_cmap(self, index):
        self.histogram.item.gradient.loadPreset(
            self.ui.cmapBox.itemText(index)
        )


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
