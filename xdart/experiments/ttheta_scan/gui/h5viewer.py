# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imorts

# Other imports
import h5py

# Qt imports
from PyQt5.QtWidgets import QWidget
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

# This module imports
from .h5viewerUI import *

class H5Viewer(QWidget):
    def __init__(self, file, fname, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.layout = self.ui.layout

        # Toolbar setup
        self.toolbar = QtWidgets.QToolBar('Tools')

        # File menu setup (part of toolbar)
        self.actionOpen = QtWidgets.QAction()
        self.actionOpen.setText('Open')

        self.actionSetDefaults = QtWidgets.QAction()
        self.actionSetDefaults.setText('Set Defaults')

        self.actionSaveDataAs = QtWidgets.QAction()
        self.actionSaveDataAs.setText('Save Data As')

        self.saveMenu = QtWidgets.QMenu()
        self.saveMenu.setTitle('Save')

        self.actionSaveImage = QtWidgets.QAction()
        self.actionSaveImage.setText('Current Image')
        self.saveMenu.addAction(self.actionSaveImage)

        self.actionSaveArray = QtWidgets.QAction()
        self.actionSaveArray.setText('Current 1D Array')
        self.saveMenu.addAction(self.actionSaveArray)
        
        self.actionSaveData = QtWidgets.QAction()
        self.actionSaveData.setText('Data')
        self.saveMenu.addAction(self.actionSaveData)

        self.fileMenu = QtWidgets.QMenu()
        self.fileMenu.addAction(self.actionOpen)
        self.fileMenu.addMenu(self.saveMenu)
        self.fileMenu.addAction(self.actionSaveDataAs)
        self.fileMenu.addAction(self.actionSetDefaults)

        self.fileButton = QtWidgets.QToolButton()
        self.fileButton.setText('File')
        self.fileButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.fileButton.setMenu(self.fileMenu)
        # End file menu setup

        self.toolbar.addWidget(self.fileButton)
        # End toolbar setup

        self.layout.addWidget(self.toolbar, 0, 0, 1, 2)

        self.show()

    def update(self, file):
        """Takes in file, adds keys to scan list
        """
        if isinstance(file, h5py.File):
            self.ui.listScans.clear()
            for key in file:
                self.ui.listScans.addItem(key)
    
    def set_data(self, sphere):
        """Takes sphere object and updates list with all arch ids
        """
        self.ui.listData.clear()
        self.ui.listData.addItem('Overall')
        for arch in sphere.arches.sort_index():
            self.ui.listData.addItem(str(arch.idx))

