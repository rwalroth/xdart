# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import Parameter

# This module imports

class wranglerWidget(Qt.QtWidgets.QWidget):
    sigStart = Qt.QtCore.Signal()
    sigPause = Qt.QtCore.Signal()
    sigStop = Qt.QtCore.Signal()
    sigContinue = Qt.QtCore.Signal()
    sigEndScan = Qt.QtCore.Signal()
    sigNewScan = Qt.QtCore.Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_number = 0 # this attribute must be an int
        self.parameters = Parameter.create(
            name='wrangler_widget', type='int', value=0
        )
    
    def wrangle(self, i):
        """This function will be called to get data from wrangler. Must
        return a tuple of (flag, data).
        """
        print("WRANGLE NOT IMPLEMENTED")
        return "TERMINATE", None
    
    def enabled(self, enable):
        """Use this function to control what is enabled and disabled
        during integration.
        """
        pass