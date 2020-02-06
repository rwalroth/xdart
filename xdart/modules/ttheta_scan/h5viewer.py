# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imorts

# Other imports
from xdart.utils import catch_h5py_file as catch

# Qt imports
from pyqtgraph.Qt import QtWidgets
QTreeWidget = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QWidget = QtWidgets.QWidget

# This module imports
from .h5viewerUI import Ui_Form
from xdart.gui.gui_utils import defaultWidget

class H5Viewer(QWidget):
    def __init__(self, file_lock, fname, parent=None):
        super().__init__(parent)
        self.file_lock = file_lock
        self.fname = fname
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.layout = self.ui.layout

        # Toolbar setup
        self.toolbar = QtWidgets.QToolBar('Tools')

        # File menu setup (part of toolbar)
        self.actionOpen = QtWidgets.QAction()
        self.actionOpen.setText('Open')

        self.actionSetDefaults = QtWidgets.QAction()
        self.actionSetDefaults.setText('Advanced...')

        self.actionSaveDataAs = QtWidgets.QAction()
        self.actionSaveDataAs.setText('Save As')

        self.actionNewFile = QtWidgets.QAction()
        self.actionNewFile.setText('New')

        self.exportMenu = QtWidgets.QMenu()
        self.exportMenu.setTitle('Export')

        self.actionSaveImage = QtWidgets.QAction()
        self.actionSaveImage.setText('Current Image')
        self.exportMenu.addAction(self.actionSaveImage)

        self.actionSaveArray = QtWidgets.QAction()
        self.actionSaveArray.setText('Current 1D Array')
        self.exportMenu.addAction(self.actionSaveArray)
        
        self.actionSaveData = QtWidgets.QAction()
        self.actionSaveData.setText('Save')
        
        self.paramMenu = QtWidgets.QMenu()
        self.paramMenu.setTitle('Config')
        
        self.paramMenu.addAction(self.actionSetDefaults)

        self.fileMenu = QtWidgets.QMenu()
        self.fileMenu.addAction(self.actionOpen)
        self.fileMenu.addAction(self.actionNewFile)
        self.fileMenu.addAction(self.actionSaveData)
        self.fileMenu.addAction(self.actionSaveDataAs)
        self.fileMenu.addMenu(self.exportMenu)

        self.fileButton = QtWidgets.QToolButton()
        self.fileButton.setText('File')
        self.fileButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.fileButton.setMenu(self.fileMenu)
        
        self.paramButton = QtWidgets.QToolButton()
        self.paramButton.setText('Config')
        self.paramButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.paramButton.setMenu(self.paramMenu)
        # End file menu setup

        self.toolbar.addWidget(self.fileButton)
        self.toolbar.addWidget(self.paramButton)
        # End toolbar setup

        self.layout.addWidget(self.toolbar, 0, 0, 1, 2)
        self.defaultWidget = defaultWidget()
        self.actionSetDefaults.triggered.connect(self.defaultWidget.show)

        self.show()

    def update(self, fname):
        """Takes in file, adds keys to scan list
        """
        idx = self.ui.listScans.currentRow()
        with self.file_lock:
            if fname == self.fname:
                with catch(self.fname, 'r') as file:
                    self.ui.listScans.clear()
                    for key in file:
                        self.ui.listScans.addItem(key)
        if idx > self.ui.listScans.count() - 1:
            idx = self.ui.listScans.count() - 1
        self.ui.listScans.setCurrentRow(idx)
    
    def set_data(self, sphere):
        """Takes sphere object and updates list with all arch ids
        """
        idx = self.ui.listData.currentRow()
        with sphere.sphere_lock:
            self.ui.listData.clear()
            self.ui.listData.addItem('Overall')
            for arch in sphere.arches.sort_index():
                self.ui.listData.addItem(str(arch.idx))
        if idx > self.ui.listData.count() - 1:
            idx = self.ui.listData.count() - 1
        self.ui.listData.setCurrentRow(idx)
    
    def set_open_enabled(self, enable):
        self.actionSaveDataAs.setEnabled(enable)
        self.actionSetDefaults.setEnabled(enable)
        self.actionOpen.setEnabled(enable)
        self.actionNewFile.setEnabled(enable)
