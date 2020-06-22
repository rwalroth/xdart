# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imports
import sys
# Qt imports
import pyqtgraph as pg
from pyqtgraph import QtGui
from PyQt5 import QtWidgets

# This module imports


class RangeSliderItem(pg.GraphicsWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.gradient = pg.GradientEditorItem(orientation="right")
        self.axis = pg.AxisItem(orientation="left")
        self.layout.addItem(self.gradient, 0, 1)
        self.layout.addItem(self.axis, 0, 0)


class RangeSliderWidget(pg.GraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item = RangeSliderItem()
        self.setCentralItem(self.item)


class Test(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vlayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.vlayout)
        self.gradiant = RangeSliderWidget()
        self.vlayout.addWidget(self.gradiant)
        self.show()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    test = Test()
    test.show()
    print("at exec")
    app.exec_()

