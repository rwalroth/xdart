# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imorts
import inspect
import os
import traceback

# This module imports
from xdart.modules.ewald import EwaldArch
from xdart.utils import catch_h5py_file
from .ui.h5viewerUI import Ui_Form
from .sphere_threads import fileHandlerThread
from ...widgets import defaultWidget

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

QTreeWidget = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QWidget = QtWidgets.QWidget
QFileDialog = QtWidgets.QFileDialog
QItemSelectionModel = QtCore.QItemSelectionModel

debug = True


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

    def __init__(self, file_lock, local_path, dirname, sphere,
                 arch, arch_ids, arches,
                 data_1d={}, data_2d={},
                 parent=None):
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        super().__init__(parent)
        self.local_path = local_path
        self.file_lock = file_lock
        self.dirname = dirname

        # Data Objects
        self.sphere = sphere
        self.arch = arch
        self.arch_ids = arch_ids
        self.arches = arches
        self.data_1d = data_1d
        self.data_2d = data_2d

        # Link UI
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
        self.ui.listData.itemSelectionChanged.connect(self.data_changed)
        self.actionOpenFolder.triggered.connect(self.open_folder)
        self.actionSaveDataAs.triggered.connect(self.save_data_as)
        self.actionNewFile.triggered.connect(self.new_file)
        
        self.file_thread = fileHandlerThread(self.sphere, self.arch,
                                             self.file_lock,
                                             arch_ids=self.arch_ids,
                                             arches=self.arches,
                                             data_1d=self.data_1d,
                                             data_2d=self.data_2d)
        self.file_thread.sigTaskDone.connect(self.thread_finished)
        self.file_thread.sigNewFile.connect(self.sigNewFile.emit)
        self.file_thread.sigUpdate.connect(self.sigUpdate.emit)
        self.file_thread.start(Qt.QtCore.QThread.LowPriority)
        
        # self.update()
        # self.show()

    def load_starting_defaults(self):
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        default_path = os.path.join(self.local_path, "last_defaults.json")
        if os.path.exists(default_path):
            self.defaultWidget.load_defaults(fname=default_path)
        else:
            self.defaultWidget.save_defaults(fname=default_path)

    def set_user_defaults(self):
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        default_path = os.path.join(self.local_path, "last_defaults.json")
        self.defaultWidget.save_defaults(fname=default_path)

    def update(self):
        """Calls both update_scans and update_data.
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        self.update_scans()
        self.update_data()
        
    def update_scans(self):
        """Takes in directory path and adds files in path to listScans
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
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
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        previous_loc = self.ui.listData.currentRow()
        previous_sel = self.ui.listData.selectedItems()
        self.ui.listData.itemSelectionChanged.disconnect(self.data_changed)
        print(f'h5viewer > update_data: previous_loc = {previous_loc}')
        print(f'h5viewer > update_data: data_2d.keys = {self.data_2d.keys()}')

        if self.sphere.name != "null_main":
            with self.sphere.sphere_lock:
                _idxs = list(self.sphere.arches.index)

            # Clear data 1d/1d objects if reintegrated
            if len(_idxs) < len(self.data_2d.keys()):
                print(f'h5viewer > update_data: clearing data_1d/2d objects')
                self.data_2d.clear()
                self.data_1d.clear()

            print(f'h5viewer > update_data: len(_idxs) = {len(_idxs)}')
            print(f'h5viewer > update_data: self.ui.listData.count() = {self.ui.listData.count()}')
            if (len(_idxs) == 0) or (len(_idxs) > self.ui.listData.count() - 1):
                self.ui.listData.clear()
                self.ui.listData.addItem('Overall')
                for idx in _idxs:
                    self.ui.listData.addItem(str(idx))

        if previous_loc > self.ui.listData.count() - 1:
            previous_loc = self.ui.listData.count() - 1

        print(f'h5viewer > update_data: resetting selection = {len(previous_sel)}')
        if len(previous_sel) < 2:
            self.ui.listData.setCurrentRow(previous_loc)
        else:
            for item in previous_sel:
                print(f'h5viewer > update_data: item = {item.text()}')
                item.setSelected(True)
        self.ui.listData.itemSelectionChanged.connect(self.data_changed)

        print(f'h5viewer > update_data: listitems (updated) = {self.ui.listData.count()}')
        print(f'h5viewer > update_data: currentRow (updated) = {self.ui.listData.currentRow()}')

        # self.ui.listData.activateWindow()
        self.ui.listData.setFocus()
        self.ui.listData.focusWidget()

    def thread_finished(self, task):
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        if task != "load_arch":
            self.update()
        self.sigThreadFinished.emit()
    
    def scans_clicked(self, q):
        """Handles items being double clicked in listScans. Either
        navigates to new folder or loads in sphere data.
        
        q: QListItem, item selected in h5viewer.
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
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
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
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

    def data_changed(self):
        """Connected to currentItemChanged signal of listData
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        self.arch_ids.clear()
        items = self.ui.listData.selectedItems()
        self.arch_ids += [str(item.text()) for item in items]
        self.arch_ids.sort()
        idxs = self.arch_ids
        print(f'h5viewer > data_changed: idxs = {idxs}')

        if (len(idxs) == 0) or (idxs[0] == 'No data'):
            self.sigUpdate.emit()
            return

        # Put 'Overall' first in list
        if 'Overall' in self.arch_ids:
            self.arch_ids.remove('Overall')
            self.arch_ids.insert(0, 'Overall')
            idxs = self.sphere.arches.index

        print(f'\n*************')
        print(f'h5viewer > data_changed - selected items: {self.arch_ids} ')
        print(f'h5viewer > data_changed - sphere.gi, sphere.static: {self.sphere.gi}, {self.sphere.gi} ')

        if len(idxs) == 0:
            self.sigUpdate.emit()
            return

        if 'No Data' not in self.arch_ids:
            self.arches.clear()
            # self.arches.update({str(idx): EwaldArch(idx=idx, static=True, gi=self.sphere.gi) for idx in idxs})
            self.arches.update({int(idx): EwaldArch(idx=idx, static=True, gi=self.sphere.gi) for idx in idxs})

            idxs_memory = []
            for idx in idxs:
                # if str(idx) in self.data_2d.keys():
                if int(idx) in self.data_2d.keys():
                    # self.arches[str(idx)] = self.data_2d[str(idx)]
                    self.arches[int(idx)] = self.data_2d[int(idx)]
                    print(f'h5viewer > data_changed: loaded arch{idx} from memory')
                    # idxs_memory.append(str(idx))
                    idxs_memory.append(int(idx))

            # self.file_thread.arch_ids = [str(idx) for idx in idxs
            #                              if str(idx) not in idxs_memory]
            self.file_thread.arch_ids = [int(idx) for idx in idxs
                                         if int(idx) not in idxs_memory]

            print(f'h5viewer > data_changed: len(self.arches) = {len(self.arches)}')
            print(f'h5viewer > data_changed: file_thread.arch_ids = {self.file_thread.arch_ids}')
            if len(self.file_thread.arch_ids) > 0:
                self.file_thread.queue.put("load_arches")
            else:
                self.sigUpdate.emit()

    def data_reset(self):
        """Resets data in memory (self.arches, self.arch_ids, self.data_..
        """
        self.arches.clear()
        self.arch_ids.clear()
        self.data_1d.clear()
        self.data_2d.clear()

        if self.ui.listData.count() > 1:
            self.ui.listData.setCurrentRow(0)

    def open_folder(self):
        """Changes the directory being displayed in the file explorer.
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        self.dirname = QFileDialog().getExistingDirectory()
        self.arches.clear()
        self.data_2d.clear()
        self.data_1d.clear()
        self.update_scans()
    
    def set_open_enabled(self, enable):
        """Sets the save and open actions to enable
        
        args:
            enable: bool, if True actions are enabled
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        self.actionSaveDataAs.setEnabled(enable)
        self.paramMenu.setEnabled(enable)
        self.actionOpenFolder.setEnabled(enable)
        self.actionNewFile.setEnabled(enable)
        self.ui.listScans.setEnabled(enable)
    
    def save_data_as(self):
        """Saves all data to hdf5 file. Also sets fname to be the
        selected file.
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        fname, _ = QFileDialog.getSaveFileName()
        with self.file_thread.lock:
            self.file_thread.new_fname = fname
            self.file_thread.queue.put("save_data_as")
        self.set_file(fname)
    
    def new_file(self):
        """Calls file dialog and sets the file name.
        """
        if debug:
            print(f'- h5viewer > H5Viewer: {inspect.currentframe().f_code.co_name} -')
        fname, _ = QFileDialog.getSaveFileName()
        self.set_file(fname)
