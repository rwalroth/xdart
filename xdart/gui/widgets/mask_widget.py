# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import traceback

# Other imports
import numpy as np

#Qt Imports
from PyQt5 import QtWidgets

import pyqtgraph as pg

from .image_widget import XDImageWidget


class MaskWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.image = XDImageWidget(self)
        self.layout.addWidget(self.image)
        self.maskToolsFrame = QtWidgets.QFrame()
        self.maskToolsLayout = QtWidgets.QGridLayout()
        self.maskToolsFrame.setLayout(self.maskToolsLayout)

        self.rectMaskButton = QtWidgets.QPushButton("Rect")
        self.maskToolsLayout.addWidget(self.rectMaskButton)

        self.minXBox = QtWidgets.QSpinBox()
        self.minXBox.valueChanged.connect(self.update_mask)
        self.minXLabel = QtWidgets.QLabel("min. X")
        self.maxXBox = QtWidgets.QSpinBox()
        self.maxXBox.valueChanged.connect(self.update_mask)
        self.maxXLabel = QtWidgets.QLabel("max. X")
        self.maskToolsLayout.addWidget(self.minXLabel, 1, 0)
        self.maskToolsLayout.addWidget(self.maxXLabel, 1, 1)
        self.maskToolsLayout.addWidget(self.minXBox, 2, 0)
        self.maskToolsLayout.addWidget(self.maxXBox, 2, 1)

        self.minYBox = QtWidgets.QSpinBox()
        self.minYBox.valueChanged.connect(self.update_mask)
        self.minYLabel = QtWidgets.QLabel("min. Y")
        self.maxYBox = QtWidgets.QSpinBox()
        self.maxYBox.valueChanged.connect(self.update_mask)
        self.maxYLabel = QtWidgets.QLabel("max. Y")
        self.maskToolsLayout.addWidget(self.minYLabel, 3, 0)
        self.maskToolsLayout.addWidget(self.maxYLabel, 3, 1)
        self.maskToolsLayout.addWidget(self.minYBox, 4, 0)
        self.maskToolsLayout.addWidget(self.maxYBox, 4, 1)

        self.layout.addWidget(self.maskToolsFrame)

        self.ROIs = []
        self.rectMaskButton.clicked.connect(self.add_rect_roi)

        self.mask = np.array([])
        self.data = np.array([])

        self.show()

    def set_data(self, arr):
        self.data = arr.copy()
        self.maxXBox.setMaximum(self.data.shape[0])
        self.maxXBox.setValue(self.data.shape[0])
        self.maxYBox.setMaximum(self.data.shape[1])
        self.maxYBox.setValue(self.data.shape[1])
        self.image.raw_image = self.data.copy()
        self.image.update_image()

    def add_rect_roi(self):
        x = int(self.data.shape[0]/2)
        y = int(self.data.shape[1]/2)
        w = int(self.data.shape[0]/10)
        h = int(self.data.shape[1]/10)
        new = pg.ROI([x,y], [w,h], removable=True)
        new.addScaleHandle([1, 0.5], [0, 0.5])
        new.addScaleHandle([0, 0.5], [1, 0.5])

        new.addScaleHandle([0.5, 0], [0.5, 1])
        new.addScaleHandle([0.5, 1], [0.5, 0])

        new.addScaleHandle([0, 1], [1, 0])
        new.addScaleHandle([1, 0], [0, 1])
        new.addScaleHandle([1, 1], [0, 0])
        new.addScaleHandle([0, 0], [1, 1])
        new.sigRegionChangeFinished.connect(self.update_mask)
        new.sigRemoveRequested.connect(self.remove_roi)
        self.ROIs.append(new)
        self.image.imageViewBox.addItem(self.ROIs[-1])
        self.update_mask()

    def remove_roi(self, q):
        to_remove = []
        for i, roi in enumerate(self.ROIs):
            if roi is q:
                to_remove.append(i)
                self.image.imageViewBox.removeItem(roi)
        for i in to_remove:
            del(self.ROIs[i])
        self.update_mask()

    def update_mask(self, q=None):
        self.mask = np.zeros_like(self.data)
        for roi in self.ROIs:
            _, coords = roi.getArrayRegion(np.ones_like(self.image.raw_image),
                                             self.image.imageItem, axes=(0, 1),
                                             returnMappedCoords=True)
            x = np.round(coords[0].ravel()).astype(int)
            y = np.round(coords[1].ravel()).astype(int)
            c, r = self.mask.shape
            valid = (x < c) & (x >= 0) & (y < r) & (y >= 0)
            self.mask[x[valid], y[valid]] = 1

        self.mask[:self.minXBox.value(), :] = 1
        self.mask[:, :self.minYBox.value()] = 1
        self.mask[self.maxXBox.value():, :] = 1
        self.mask[:, self.maxYBox.value():] = 1

        self.image.raw_image = self.data.copy()
        self.image.raw_image[self.mask == 1] = self.image.raw_image.max()
        self.image.update_image()

