# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports
import pandas as pd

# Qt imports
from pyqtgraph import Qt

# This module imports
from ...gui_utils import DFTableModel

class metadataWidget(Qt.QtWidgets.QWidget):
    """Widget for displaying metadata.
    
    attributes:
        layout: QVBoxLayout, widget layout
        tableview: QTableView, viewer for table model
    
    methods:
        update: Updates the data displayed
    """
    def __init__(self, sphere, arch, parent=None):
        super().__init__(parent)
        self.layout = Qt.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.tableview = Qt.QtWidgets.QTableView()
        self.tableview.setModel(DFTableModel())
        self.layout.addWidget(self.tableview)
        self.sphere = sphere
        self.arch = arch
    
    def update(self):
        """Updates the table with new data.
        """
        #self.tableview.reset()
        if self.arch.idx is None:
            self.tableview.setModel(
                DFTableModel(self.sphere.scan_data.transpose())
            )
        
        else:
            data = pd.DataFrame(self.arch.scan_info, index=[self.arch.idx])
            self.tableview.setModel(DFTableModel(data.transpose()))
