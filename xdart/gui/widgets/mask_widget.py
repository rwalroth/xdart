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
from PyQt5.QtCore import pyqtSignal

import pyqtgraph as pg

from xdart.utils.pgOverrides.ROI import XDEllipseROI, XDPolyLineROI
from xdart.modules.ewald import EwaldArch, EwaldSphere
from pyqtgraph import LineROI, ROI

from .image_widget import XDImageWidget
from .maskWidgetUI import Ui_Form


ADD_PEN = (0, 0, 255)
SUB_PEN = (0, 255, 0)


class MaskWidget(QtWidgets.QWidget):
    newMask = pyqtSignal(int, np.ndarray)
    requestMask = pyqtSignal(int)

    def __init__(self, parent=None, sphere=None, arch=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.image = XDImageWidget(self)
        self.ui.horizontalLayout.insertWidget(0, self.image, 2)
        self.resize(800, 400)

        self.ROIs = []

        self.ui.rectMaskButton.clicked.connect(self.add_rect_roi)
        self.ui.ellipseMaskButton.clicked.connect(self.add_ellipse_roi)
        self.ui.lineMaskButton.clicked.connect(self.add_line_roi)
        self.ui.polyMaskButton.clicked.connect(self.add_poly_roi)

        self.ui.xMinBox.valueChanged.connect(self.update_mask)
        self.ui.xMaxBox.valueChanged.connect(self.update_mask)
        self.ui.yMinBox.valueChanged.connect(self.update_mask)
        self.ui.yMaxBox.valueChanged.connect(self.update_mask)

        self.ui.clearButton.clicked.connect(self.clear_mask)

        self.mask = np.array([])
        self.base_mask = np.array([])
        self.data = np.array([])

        self.ui.archList.currentTextChanged.connect(self._request_data)
        self.ui.setGlobal.clicked.connect(self._send_global)
        self.ui.setCurrent.clicked.connect(self._send_local)

        self.show()

    def set_data(self, arr, base=None):
        self.data = arr.copy()
        if base is None or base.shape != self.data.shape:
            self.base_mask = np.zeros_like(self.data)
        else:
            self.base_mask = base.copy()
        self.ui.xMaxBox.setMaximum(self.data.shape[0])
        self.ui.yMaxBox.setMaximum(self.data.shape[1])

        self.ui.xMinBox.setMaximum(self.data.shape[0])
        self.ui.yMinBox.setMaximum(self.data.shape[1])

        self.ui.xMaxSlider.setMaximum(self.data.shape[0])
        self.ui.yMaxSlider.setMaximum(self.data.shape[1])

        self.ui.xMinSlider.setMaximum(self.data.shape[0])
        self.ui.yMinSlider.setMaximum(self.data.shape[1])

        self.ui.xMaxBox.setValue(self.data.shape[0])
        self.ui.yMaxBox.setValue(self.data.shape[1])

        self.image.raw_image = self.data.copy()
        self.image.update_image()

        self.update_mask()

    def _request_data(self, q=None):
        try:
            out = int(q)
        except ValueError:
            out = -1
        self.requestMask.emit(out)

    def _send_global(self, q=None):
        self._send_and_set(-1)

    def _send_local(self, q=None):
        if self.ui.archList.currentText().lower() == "global":
            self._send_global()
        else:
            try:
                index = int(self.ui.archList.currentText())
                self._send_and_set(index)
            except ValueError:
                print("Invalid index encountered while trying to emit local mask.")

    def _send_and_set(self, index):
        self.newMask.emit(index, self.mask)
        self.base_mask = self.mask.copy()
        self.clear_mask(clear_base=False)

    def add_rect_roi(self):
        x = int(self.data.shape[0]/2)
        y = int(self.data.shape[1]/2)
        w = int(self.data.shape[0]/10)
        h = int(self.data.shape[1]/10)
        pen, sign = self._get_pen_and_sign()
        new = ROI([x,y], [w,h], removable=True, pen=pen)
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

        self._append_roi(new, sign)

    def _get_pen_and_sign(self):
        if self.ui.addROI.isChecked():
            pen = ADD_PEN
            sign = 1
        elif self.ui.subtractROI.isChecked():
            pen = SUB_PEN
            sign = 0
        return pen, sign

    def add_ellipse_roi(self, q=None):
        pen, sign = self._get_pen_and_sign()
        x = int(self.data.shape[0]/2)
        y = int(self.data.shape[1]/2)
        w = int(self.data.shape[0]/10)
        h = int(self.data.shape[1]/10)
        new = XDEllipseROI([x, y], [w, h], removable=True, pen=pen)

        new.sigRegionChangeFinished.connect(self.update_mask)
        new.sigRemoveRequested.connect(self.remove_roi)

        self._append_roi(new, sign)

    def _append_roi(self, new, sign):
        self.ROIs.append((new, sign))
        self.image.imageViewBox.addItem(self.ROIs[-1][0])
        self.update_mask()

    def add_line_roi(self, q=None):
        pen, sign = self._get_pen_and_sign()
        x = int(self.data.shape[0]/2)
        y = int(self.data.shape[1]/2)
        w = int(self.data.shape[0]/10)
        h = int(self.data.shape[1]/10)
        new = LineROI([x, y], [x, y + h], width=w/4, removable=True,
                      pen=pen)

        new.sigRegionChangeFinished.connect(self.update_mask)
        new.sigRemoveRequested.connect(self.remove_roi)

        self._append_roi(new, sign)

    def add_poly_roi(self, q=None):
        pen, sign = self._get_pen_and_sign()
        x = int(self.data.shape[0]/2)
        y = int(self.data.shape[1]/2)
        w = int(self.data.shape[0]/10)
        h = int(self.data.shape[1]/10)
        new = XDPolyLineROI([[x, y], [x, y + h], [x + w, y]], closed=True,
                            removable=True, pen=pen)

        new.sigRegionChangeFinished.connect(self.update_mask)
        new.sigRemoveRequested.connect(self.remove_roi)

        self._append_roi(new, sign)

    def remove_roi(self, q):
        to_remove = []
        for i, roi in enumerate(self.ROIs):
            if roi[0] is q:
                to_remove.append(i)
                self.image.imageViewBox.removeItem(roi[0])
        for i in to_remove:
            del(self.ROIs[i])
        self.update_mask()

    def update_mask(self, q=None):
        self.mask = self.base_mask.copy()
        for roi in self.ROIs:
            self._apply_roi(roi[0], roi[1])

        self._apply_bounding_mask()

        self.image.raw_image = self.data.copy()
        self.image.raw_image[self.mask == 1] = self.image.raw_image.max()
        self.image.update_image()

    def _apply_bounding_mask(self):
        self.mask[:self.ui.xMinBox.value(), :] = 1
        self.mask[:, :self.ui.yMinBox.value()] = 1
        self.mask[self.ui.xMaxBox.value():, :] = 1
        self.mask[:, self.ui.yMaxBox.value():] = 1

    def _apply_roi(self, roi, val):
        _, coords = roi.getArrayRegion(np.ones_like(self.image.raw_image),
                                       self.image.imageItem, axes=(0, 1),
                                       returnMappedCoords=True)
        x = np.round(coords[0].ravel()).astype(int)
        y = np.round(coords[1].ravel()).astype(int)
        c, r = self.mask.shape
        valid = (x < c) & (x >= 0) & (y < r) & (y >= 0)
        self.mask[x[valid], y[valid]] = val

    def clear_mask(self, q=None, clear_base=True):
        if clear_base:
            self.base_mask = np.zeros_like(self.data)
        while len(self.ROIs) > 0:
            r = self.ROIs[0][0]
            self.image.imageViewBox.removeItem(r)
            del(self.ROIs[0])
        self.ui.yMinBox.setValue(0)
        self.ui.yMaxBox.setValue(self.ui.yMaxBox.maximum())
        self.ui.xMinBox.setValue(0)
        self.ui.xMaxBox.setValue(self.ui.xMaxBox.maximum())
        self.update_mask()


