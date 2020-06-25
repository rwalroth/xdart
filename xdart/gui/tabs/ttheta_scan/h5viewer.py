# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imorts
import json
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
from .sphere_threads import fileHandlerThread
from ...widgets import defaultWidget
from ...gui_utils import XdartDecoder, XdartEncoder

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
    sigThreadFinished = Qt.QtCore.Signal()

    def __init__(self, file_lock, local_path, dirname, sphere, arch, parent=None):
        super().__init__(parent)
        self.local_path = local_path
        self.file_lock = file_lock
        self.dirname = dirname
        self.sphere = sphere
        self.arch = arch
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.layout = self.ui.layout
        self.defaultWidget = defaultWidget()
        self.defaultWidget.sigSetUserDefaults.connect(self.set_user_defaults)

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
        
        self.file_thread = fileHandlerThread(self.sphere, self.arch,
                                             self.file_lock)
        self.file_thread.sigTaskDone.connect(self.thread_finished)
        self.file_thread.sigNewFile.connect(self.sigNewFile.emit)
        self.file_thread.sigUpdate.connect(self.sigUpdate.emit)
        self.file_thread.start(Qt.QtCore.QThread.LowPriority)
        
        self.update()
        self.show()

    def load_starting_defaults(self):
        default_path = os.path.join(self.local_path, "last_defaults.json")
        if os.path.exists(default_path):
            self.defaultWidget.load_defaults(fname=default_path)
        else:
            self.defaultWidget.save_defaults(fname=default_path)

    def set_user_defaults(self):
        default_path = os.path.join(self.local_path, "last_defaults.json")
        self.defaultWidget.save_defaults(fname=default_path)


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
        if self.sphere.name != "null_main":
            with self.sphere.sphere_lock:
                _idxs = list(self.sphere.arches.index)
            self.ui.listData.clear()
            self.ui.listData.addItem('Overall')
            for idx in _idxs:
                self.ui.listData.addItem(str(idx))
        if previous_loc > self.ui.listData.count() - 1:
            previous_loc = self.ui.listData.count() - 1
        self.ui.listData.setCurrentRow(previous_loc)
    
    def thread_finished(self, task):
        if task != "load_arch":
            self.update()
        self.sigThreadFinished.emit()
    
    def scans_clicked(self, q):
        """Handles items being double clicked in listScans. Either
        navigates to new folder or loads in sphere data.
        
        q: QListItem, item selected in h5viewer.
        """
        if q.data(0) == '..':
            if self.dirname[-1] in ['/', '\\']:
                up = os.path.dirname(self.dirname[:-1])
            else:
                up = os.path.dirname(self.dirname)
            
            if os.path.isdir(up) and os.path.splitdrive(up)[1] != '':
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
        if fname != '':
            try:
                with self.file_lock:
                    with catch_h5py_file(fname, 'a') as _:
                        pass
            
                self.ui.listData.clear()
                self.ui.listData.addItem('Loading...')
                self.set_open_enabled(False)
                self.file_thread.fname = fname
                self.file_thread.queue.put("set_datafile")
            except:
                traceback.print_exc()
                return
    
    def data_clicked(self, current, previous):
        """Connected to currentItemChanged signal of listData
        
        current: QListItem, item selected
        previous: QListItem, previous selection
        """
        if current is not None and previous is not None:
            nochange = (current.data(0) == previous.data(0))
        else:
            nochange = False
        if (current is not None and 
                current.data(0) not in ('No data', "Loading...") and not
                nochange):
            self.arch.reset()
            if current.data(0) != 'Overall' and 'scan' not in current.data(0):
                try:
                    idx = int(current.data(0))
                except ValueError:
                    return
                self.arch.idx = idx
                self.file_thread.queue.put("load_arch")
            else:
                self.sigUpdate.emit()
    
    def open_folder(self):
        """Changes the directory being displayed in the file explorer.
        """
        dirname = QFileDialog().getExistingDirectory()
        if dirname != "":
            self.dirname = dirname
            self.update_scans()
    
    def set_open_enabled(self, enable):
        """Sets the save and open actions to enable
        
        args:
            enable: bool, if True actions are enabled
        """
        self.actionSaveDataAs.setEnabled(enable)
        self.paramMenu.setEnabled(enable)
        self.actionOpenFolder.setEnabled(enable)
        self.actionNewFile.setEnabled(enable)
        self.ui.listScans.setEnabled(enable)
    
    def save_data_as(self):
        """Saves all data to hdf5 file. Also sets fname to be the
        selected file.
        """
        fname, _ = QFileDialog.getSaveFileName()
        with self.file_thread.lock:
            self.file_thread.new_fname = fname
            self.file_thread.queue.put("save_data_as")
        self.set_file(fname)
    
    def new_file(self):
        """Calls file dialog and sets the file name.
        """
        fname, _ = QFileDialog.getSaveFileName()
        self.set_file(fname)
