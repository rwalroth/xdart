# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports

# Qt imports
from pyqtgraph import Qt

# This module imports
from .rangeWidgetUI import Ui_Form

class rangeWidget(Qt.QtWidgets.QWidget):
    """Widget for storing range parameters. Contains high, low, number
    of points, and step size boxes. Modifying one will modify the others
    as expected. Also has optional unit box.
    
    attributes:
        ui: Ui_Form from qtdesigner
    
    methods:
        high_changed, low_changed, points_changed, step_changed: Ensure
            that other attributes change appropriately with each other
    
    signals:
        sigPointsChanged: int, sends out the new points value
        sigRangeChanged: int, int, sends out new low and high value
        sigUnitChanged: int, sends out index of new unit value
    """
    sigUnitChanged = Qt.QtCore.Signal(int)
    sigRangeChanged = Qt.QtCore.Signal(int, int)
    sigPointsChanged = Qt.QtCore.Signal(int)
    def __init__(self, title, unit, range_high, points_high, parent=None, 
                 range_low=0, points_low=2, defaults=None):
        """title: str, title of the range widget
        unit: list or str, if list adds items to unit box, if str sets
            the unit to be a static label
        range_high: float, maximum value for range
        points_high: int, maximum number of points
        range_low: float, minimum value of range
        points_low: int, minimum value of points
        defaults: list, values to initialize with, [low, high, points]
        """
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.titleLabel.setText(title)
        if type(unit) == list:
            self.ui.units.addItems(unit)
            self.ui.units.currentIndexChanged.connect(self.sigUnitChanged.emit)
        elif type(unit) == str:
            self.ui.horizontalLayout.removeWidget(self.ui.units)
            self.ui.units.hide()
            self.unit_label = Qt.QtWidgets.QLabel(self)
            self.unit_label.setText(unit)
            self.ui.horizontalLayout.insertWidget(-1, self.unit_label)
        
        self.ui.low.setMinimum(range_low)
        self.ui.low.setValue(range_low)
        self.ui.high.setMaximum(range_high)
        self.ui.high.setValue(range_high)
        self.ui.low.setMaximum(self.ui.high.value())
        self.ui.high.setMinimum(self.ui.low.value())
        
        self.ui.points.setMaximum(points_high)
        self.ui.points.setMinimum(points_low)
        self.ui.points.setValue(points_low)
        self.ui.step.setValue(
            (self.ui.high.value() - self.ui.low.value()) /
            (self.ui.points.value() - 1)
        )
        
        self.ui.low.valueChanged.connect(self.low_changed)
        self.ui.high.valueChanged.connect(self.high_changed)
        self.ui.points.valueChanged.connect(self.points_changed)
        self.ui.step.valueChanged.connect(self.step_changed)
        
        if defaults is not None:
            self.ui.low.setValue(defaults[0])
            self.ui.high.setValue(defaults[1])
            self.ui.points.setValue(defaults[2])
    
    def low_changed(self, low):
        """Sets the new minimum for high, moves high to a higher value
        if it is too low
        """
        high = self.ui.high.value()
        if high <= low:
            high = low + self.ui.high.singleStep()
            self.ui.high.setValue(high)
        else:
            self.ui.points.valueChanged.emit(self.ui.points.value())
            self.sigRangeChanged.emit(low, high)
        self.ui.high.setMinimum(low)
    
    def high_changed(self, high):
        """Sets the new maximum for low, if low is to high moves low to
        a lower value
        """
        low = self.ui.low.value()
        if low >= high:
            low = high - self.ui.high.singleStep()
            self.ui.low.setValue(low)
        else:
            self.ui.points.valueChanged.emit(self.ui.points.value())
            self.sigRangeChanged.emit(low, high)
        self.ui.low.setMaximum(high)
    
    def points_changed(self, points):
        """Changes the step value based on the current high and low
        values
        """
        self.ui.step.blockSignals(True)
        self.ui.step.setValue(
            (self.ui.high.value() - self.ui.low.value()) / (points - 1)
        )
        self.ui.step.blockSignals(False)
        
        self.sigPointsChanged.emit(points)
    
    def step_changed(self, step):
        """Changes the number of points based on the new step value
        and current high and low values
        """
        points = round(
            ((self.ui.high.value() - self.ui.low.value()) / step) + 1
        )
        self.ui.points.blockSignals(True)
        self.ui.points.setValue(points)
        self.ui.points.blockSignals(False)
        
        self.sigPointsChanged.emit(points)
        
