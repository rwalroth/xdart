# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imorts
import os
import traceback

# Other imports
from xdart.utils import catch_h5py_file as catch

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
QTreeWidget = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QWidget = QtWidgets.QWidget
QFileDialog = QtWidgets.QFileDialog

# This module imports
from xdart.utils import catch_h5py_file
from .h5viewerUI import Ui_Form
from ...widgets import defaultWidget

class H5Viewer(QWidget):
    """Widget for displaying the contents of an EwaldSphere object and
    a basic file explorer. Also holds menus for more general tasks like
    setting defaults.
    
    attributes:
        (QAction attributes not shown, associated menus are)
        exportMenu: Sub-menu for exporting images and 1d data
        file_lock: Condition, lock governing file access
        fileMenu: Menu for saving files and exporting data
        fname: Current data file name
        layout: ui layout TODO: this can stay with ui
        paramMenu: Menu for saving and loading defaults
        toolbar: QToolBar, holds the menus
        ui: Ui_Form from qtdesigner

    methods:
        set_data: Sets the data in the dataList
        set_open_enabled: Sets the ability to open scans to enabled or
            disables
        update: Updates files in scansList
        TODO: Rename the methods and attributes based on what they
            actually do
    """
    sigNewFile = Qt.QtCore.Signal(str)
    sigUpdate = Qt.QtCore.Signal()
    def __init__(self, file_lock, fname, dirname, sphere, arch, parent=None):
        super().__init__(parent)
        self.file_lock = file_lock
        self.dirname = dirname
        self.sphere = sphere
        self.arch = arch
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.layout = self.ui.layout
        self.defaultWidget = defaultWidget()

        # Toolbar setup
        self.toolbar = QtWidgets.QToolBar('Tools')

        # File menu setup (part of toolbar)
        self.actionOpenFolder = QtWidgets.QAction()
        self.actionOpenFolder.setText('Open Folder')

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
        
        self.paramMenu = QtWidgets.QMenu()
        self.paramMenu.setTitle('Config')
        
        self.actionSaveParams = QtWidgets.QAction()
        self.actionSaveParams.setText('Save')
        self.actionSaveParams.triggered.connect(self.defaultWidget.save_defaults)
        self.paramMenu.addAction(self.actionSaveParams)
        
        self.actionLoadParams = QtWidgets.QAction()
        self.actionLoadParams.setText('Load')
        self.actionLoadParams.triggered.connect(self.defaultWidget.load_defaults)
        self.paramMenu.addAction(self.actionLoadParams)
        
        self.paramMenu.addAction(self.actionSetDefaults)

        self.fileMenu = QtWidgets.QMenu()
        self.fileMenu.addAction(self.actionOpenFolder)
        self.fileMenu.addAction(self.actionNewFile)
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
        self.actionSetDefaults.triggered.connect(self.defaultWidget.show)
        
        self.ui.listScans.itemDoubleClicked.connect(self.scans_clicked)
        self.ui.listData.currentItemChanged.connect(self.data_clicked)
        self.actionOpenFolder.triggered.connect(self.open_folder)
        self.actionSaveDataAs.triggered.connect(self.save_data_as)
        self.actionNewFile.triggered.connect(self.new_file)

        self.update()
        self.show()

    def update(self):
        """Calls both update_scans and update_data.
        """
        self.update_scans()
        self.update_data()
        
    def update_scans(self):
        """Takes in directory path and adds files in path to listScans
        """
        self.ui.listScans.clear()
        self.ui.listScans.addItem('..')
        for name in os.listdir(self.dirname):
            abspath = os.path.join(self.dirname, name)
            if os.path.isdir(abspath):
                self.ui.listScans.addItem(name + '/')
            elif name.split('.')[-1] in ('h5', 'hdf5'):
                self.ui.listScans.addItem(name)
    
    def update_data(self):
        """Updates list with all arch ids.
        """
        previous_loc = self.ui.listData.currentRow()
        with self.sphere.sphere_lock:
            self.ui.listData.clear()
            self.ui.listData.addItem('Overall')
            for idx in self.sphere.arches.index:
                self.ui.listData.addItem(str(idx))
        if previous_loc > self.ui.listData.count() - 1:
            previous_loc = self.ui.listData.count() - 1
        self.ui.listData.setCurrentRow(previous_loc)
    
    def scans_clicked(self, q):
        """Handles items being double clicked in listScans. Either
        navigates to new folder or loads in sphere data.
        
        q: QListItem, item selected in h5viewer.
        """
        # TODO: Most of this should be in h5viewer
        if q.data(0) == '..':
            if self.dirname[-1] in ['/', '\\']:
                up = os.path.dirname(self.dirname[:-1])
            else:
                up = os.path.dirname(self.dirname)
            
            if (os.path.isdir(up) and os.path.splitdrive(up)[1] != ''):
                self.dirname = up
                self.update_scans()
        elif '/' in q.data(0):
            dirname = os.path.join(self.dirname, q.data(0))
            if os.path.isdir(dirname):
                self.dirname = dirname
                self.update_scans()
        elif q.data(0) != 'No scans':
            self.set_file(os.path.join(self.dirname, q.data(0)))
    
    def set_file(self, fname):
        """Changes the data file.
        
        args:
            fname: str, absolute path for data file
        """
        with self.file_lock:
            if fname not in ('', self.sphere.data_file):
                try:
                    with catch_h5py_file(fname, 'a') as _:
                        pass
                
                    self.ui.listData.clear()
                    self.ui.listData.addItem('Loading...')
                    Qt.QtGui.QApplication.processEvents()
                    self.sphere.set_datafile(fname, 
                                             save_args={'compression':'lzf'})
                    self.update_data()
                    self.sigNewFile.emit(fname)
                    self.sigUpdate.emit()
                except:
                    traceback.print_exc()
                    return
    
    def data_clicked(self, current, previous):
        """Connected to currentItemChanged signal of listData
        
        current: QListItem, item selected
        previous: QListItem, previous selection
        """
        if current is not None and current.data(0) != 'No data':
            self.arch.reset()
            if current.data(0) != 'Overall' and 'scan' not in current.data(0):
                try:
                    idx = int(current.data(0))
                except ValueError:
                    return
                self.arch.idx = idx
                with self.file_lock:
                    with catch_h5py_file(self.sphere.data_file, 'r') as file:
                        self.arch.load_from_h5(file['arches'])
        else:
            self.sphere.reset()
            self.sphere.name = "null_main"
        self.sigUpdate.emit()
    
    def open_folder(self):
        """Changes the directory being displayed in the file explorer.
        """
        self.dirname = QFileDialog().getExistingDirectory()
        self.update_scans()
    
    def set_open_enabled(self, enable):
        """Sets the save and open actions to enable
        
        args:
            enable: bool, if True actions are enabled
        """
        self.actionSaveDataAs.setEnabled(enable)
        self.actionSetDefaults.setEnabled(enable)
        self.actionOpenFolder.setEnabled(enable)
        self.actionNewFile.setEnabled(enable)
    
    def save_data_as(self):
        """Saves all data to hdf5 file. Also sets fname to be the
        selected file.
        """
        fname, _ = QFileDialog.getSaveFileName()
        with self.file_lock:
            with catch(self.sphere.data_file, 'r') as f1:
                with catch(fname, 'w') as f2:
                    for key in f1:
                        f1.copy(key, f2)
                    for attr in f1.attrs:
                        f2.attrs[attr] = f1.attrs[attr]
        self.set_file(fname)
    
    def new_file(self):
        """Calls file dialog and sets the file name.
        """
        fname, _ = QFileDialog.getSaveFileName()
        self.set_file(fname)
    
