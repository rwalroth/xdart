# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports
import pandas as pd

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt

# This module imports
from ....gui.gui_utils import DFTableModel

class metadataWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = Qt.QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.tableview = Qt.QtWidgets.QTableView()
        self.tableview.setModel(DFTableModel())
        self.layout.addWidget(self.tableview)
    
    def update(self, sphere, arch=None):
        #self.tableview.reset()
        if arch is None:
            self.tableview.setModel(DFTableModel(sphere.scan_data.transpose()))
        
        else:
            data = pd.DataFrame(sphere.arches[arch].scan_info, index=[0])
            self.tableview.setModel(DFTableModel(data.transpose()))
