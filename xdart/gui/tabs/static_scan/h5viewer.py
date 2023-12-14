# -*- coding: utf-8 -*-
"""
@author: walroth
"""
# Standard library imports
import os
import time
import traceback
import gc

# This module imports
from .ui.h5viewerUI import Ui_Form
from xdart.modules.ewald import EwaldArch
from .sphere_threads import fileHandlerThread
from ...widgets import defaultWidget
from xdart import utils
from xdart.utils.containers import int_2d_data_static
from xdart.utils import catch_h5py_file as catch
from xdart.utils.containers import create_ai_from_dict

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets, QtCore

# from icecream import ic; ic.configureOutput(prefix='', includeContext=True)

QTreeWidget = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QWidget = QtWidgets.QWidget
QFileDialog = QtWidgets.QFileDialog
QItemSelectionModel = QtCore.QItemSelectionModel


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

    def __init__(self, file_lock, local_path, dirname,
                 sphere, arch, arch_ids, arches,
                 data_1d, data_2d,
                 parent=None):
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
        self.new_scan = True
        self.update_2d = True
        self.auto_last = True
        self.latest_idx = None
        self.new_scan_loaded = False
        # self.new_scan_name = None

        # Link UI
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # self.layout = self.ui.layout
        self.layout = self.ui.gridLayout
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
        # self.ui.listScans.itemActivated.connect(self.scans_clicked)
        self.ui.listData.itemSelectionChanged.connect(self.data_changed)
        self.ui.listData.itemClicked.connect(self.data_changed)
        self.ui.show_all.clicked.connect(self.show_all)
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
        # ic()
        # self.update_scans()
        self.update_data()
        
    def update_scans(self):
        """Takes in directory path and adds files in path to listScans
        """
        # ic()
        if not os.path.exists(self.dirname):
            return

        self.ui.listScans.clear()
        self.ui.listScans.addItem('..')

        for name in sorted(os.listdir(self.dirname)):
            abspath = os.path.join(self.dirname, name)
            if os.path.isdir(abspath):
                self.ui.listScans.addItem(name + '/')
            elif name.split('.')[-1] in ('h5', 'hdf5'):
                self.ui.listScans.addItem(name)
    
    def update_data(self):
        """Updates list with all arch ids.
        """
        # ic()
        if self.sphere.name == "null_main":
            return

        # with self.sphere.sphere_lock:
        _idxs = [str(i) for i in list(self.sphere.arches.index)]
        # ic(_idxs, self.data_1d.keys(), self.latest_idx, self.auto_last, self.new_scan_loaded)

        if len(_idxs) == 0:
            self.ui.listData.clear()
            # self.ui.listData.addItem('No Data')
            return

        lw = self.ui.listData
        items = [lw.item(x).text() for x in range(lw.count())]
        eq = _idxs == items
        # ic(_idxs, items, eq)

        if (len(_idxs) > 1) and (_idxs == items):
            if self.new_scan_loaded:
                self.new_scan_loaded = False
                self.ui.listData.setCurrentRow(-1)
                self.arch_ids = []
                return
            if self.auto_last and (self.latest_idx in _idxs) and (len(self.latest_idx) == 1):
                items = self.ui.listData.findItems(str(self.latest_idx), QtCore.Qt.MatchExactly)
                # ic(self.latest_idx, items)
                if len(items):
                    for item in items:
                        self.h5viewer.ui.listData.setCurrentItem(item)
                return
        if (len(_idxs) > 1) and (len(_idxs) == (len(items))):
            return

        previous_loc = self.ui.listData.currentRow()
        previous_sel = self.ui.listData.selectedItems()
        # self.ui.listData.itemSelectionChanged.disconnect(self.data_changed)

        # ic(previous_loc, previous_sel)

        self.ui.listData.clear()
        self.ui.listData.insertItems(0, _idxs)

        if self.new_scan_loaded:
            self.new_scan_loaded = False
            self.ui.listData.setCurrentRow(-1)
            self.arch_ids.clear()
            return

        # ic(self.auto_last, self.latest_idx, _idxs)
        if self.auto_last and isinstance(self.latest_idx, int) and (str(self.latest_idx) in _idxs):
            items = self.ui.listData.findItems(str(self.latest_idx), QtCore.Qt.MatchExactly)
            # ic(self.latest_idx, items)
            # self.ui.listData.itemSelectionChanged.connect(self.data_changed)
            if len(items):
                for item in items:
                    self.ui.listData.setCurrentItem(item)
            return
        # for idx in _idxs:
        #     self.ui.listData.addItem(str(idx))

        # if self.new_scan_name == self.sphere.name:

        # for idx in _idxs:
        #     self.ui.listData.addItem(str(idx))

        # if (len(_idxs) == 0) or (len(_idxs) > self.ui.listData.count() - 1):
        #     self.ui.listData.clear()
        #     # self.ui.listData.addItem('Overall')
        #     for idx in _idxs:
        #         self.ui.listData.addItem(str(idx))

        # lw = self.ui.listData
        # items = [lw.item(x).text() for x in range(lw.count())]

        if previous_loc > self.ui.listData.count() - 1:
            previous_loc = self.ui.listData.count() - 1

        # self.ui.listData.itemSelectionChanged.connect(self.data_changed)
        if len(previous_sel) < 2:
            self.ui.listData.setCurrentRow(previous_loc)
        else:
            for item in previous_sel:
                item.setSelected(True)

    def show_all(self):
        # ic()

        if len(self.sphere.arches.index) > 0:
            self.arch_ids.clear()
            self.arch_ids += self.sphere.arches.index

        # ic(self.arch_ids)
        self.new_scan = False
        self.data_changed(show_all=True)

    def thread_finished(self, task):
        # ic()
        if task != "load_arch":
            self.update()
        self.sigThreadFinished.emit()

        gc.collect()
    
    def scans_clicked(self, q):
        """Handles items being double clicked in listScans. Either
        navigates to new folder or loads in sphere data.
        
        q: QListItem, item selected in h5viewer.
        """
        # ic()
        try:
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
                self.new_scan_loaded = True
        except AttributeError:
            pass
    
    def set_file(self, fname):
        """Changes the data file.
        
        args:
            fname: str, absolute path for data file
        """
        # ic()
        if fname != '':
            try:
                # with self.file_lock:
                #     with catch_h5py_file(fname, 'a') as _:
                #         pass

                self.ui.listData.itemSelectionChanged.disconnect(self.data_changed)
                self.ui.listData.clear()
                self.ui.listData.addItem('Loading...')
                # self.set_open_enabled(False)
                self.file_thread.fname = fname
                self.file_thread.queue.put("set_datafile")
                self.ui.listData.itemSelectionChanged.connect(self.data_changed)
                self.new_scan = True
            except:
                traceback.print_exc()
                return

    def data_changed(self, show_all=False):
        """Connected to currentItemChanged signal of listData
        """
        # ic()
        if not show_all:
            self.arch_ids.clear()
            items = self.ui.listData.selectedItems()
            self.arch_ids += sorted([str(item.text()) for item in items])
            idxs = self.arch_ids
        else:
            idxs = self.arch_ids

        # ic(idxs, self.new_scan)

        if (len(idxs) == 0) or ('No data' in idxs):
            time.sleep(0.1)
            return

        # if idxs[0] == 'No data':
        #     self.arch_ids = []
        #     self.sigUpdate.emit()
        #     return

        # if self.new_scan and ('Overall' in idxs) and (len(self.data_1d) == 0):
        # if self.new_scan and ('Overall' in idxs):
        # if self.new_scan:
        #     self.new_scan = False
        #     return

        # ic(idxs, self.new_scan, len(self.data_1d), len(self.data_2d), len(self.sphere.arches.index))

        # Put 'Overall' first in list
        load_2d = self.update_2d
        # if 'Overall' in self.arch_ids:
        #     self.arch_ids.insert(0, self.arch_ids.pop(self.arch_ids.index('Overall')))
        #     idxs = self.sphere.arches.index

        if len(self.sphere.arches.index) > 1:
            if len(idxs) == len(self.sphere.arches.index):
                load_2d = False

        if load_2d:
            idxs_memory = [int(idx) for idx in idxs if int(idx) in self.data_2d.keys()]
        else:
            idxs_memory = [int(idx) for idx in idxs if int(idx) in self.data_1d.keys()]

        # ic(load_2d, idxs_memory)

        # Remove 2d data from 'Sum' if for unselected keys
        if load_2d:
            if (len(self.arches) == 0) or (len(self.data_2d) == 0):
                self.arches.update({'sum_int_2d': int_2d_data_static(), 'sum_map_raw': 0})
                self.arches.update({'idxs': [], 'add_idxs': [], 'sub_idxs': []})

            if len(idxs) > 1:
                self.get_arches_sum(idxs, idxs_memory)

            self.arches['idxs'] = [int(idx) for idx in idxs]

        # self.file_thread.arch_ids = [int(idx) for idx in idxs
        #                              if int(idx) not in idxs_memory]
        arch_ids = [int(idx) for idx in idxs
                    if int(idx) not in idxs_memory]

        # ic(arch_ids)
        # if len(self.file_thread.arch_ids) > 0:
        #     self.file_thread.update_2d = load_2d
        #     self.file_thread.queue.put("load_arches")
        if len(arch_ids) > 0:
            self.load_arches_data(arch_ids, load_2d)

        self.sigUpdate.emit()

    gc.collect()

    def data_reset(self):
        """Resets data in memory (self.arches, self.arch_ids, self.data_..
        """
        # ic()
        self.arches.clear()
        self.arch_ids.clear()
        self.data_1d.clear()
        self.data_2d.clear()
        self.new_scan = True

    def open_folder(self):
        """Changes the directory being displayed in the file explorer.
        """
        # ic()
        dirname = QFileDialog().getExistingDirectory(
            caption='Choose Directory',
            directory='',
            options=QFileDialog.ShowDirsOnly
        )
        if os.path.exists(dirname):
            self.dirname = dirname
            self.arches.clear()
            self.data_1d.clear()
            self.data_2d.clear()
            self.new_scan = True
            self.update_scans()
    
    def set_open_enabled(self, enable):
        """Sets the save and open actions to enable
        
        args:
            enable: bool, if True actions are enabled
        """
        # ic()
        self.actionSaveDataAs.setEnabled(enable)
        self.paramMenu.setEnabled(enable)
        self.actionOpenFolder.setEnabled(enable)
        self.actionNewFile.setEnabled(enable)
        # self.ui.listScans.setEnabled(enable)
    
    def save_data_as(self):
        """Saves all data to hdf5 file. Also sets fname to be the
        selected file.
        """
        # ic()
        fname, _ = QFileDialog.getSaveFileName()
        with self.file_thread.lock:
            self.file_thread.new_fname = fname
            self.file_thread.queue.put("save_data_as")
        self.set_file(fname)
    
    def new_file(self):
        """Calls file dialog and sets the file name.
        """
        # ic()
        fname, _ = QFileDialog.getSaveFileName()
        self.set_file(fname)

    def load_arches_data(self, arch_ids, load_2d):
        """Loads data from hdf5 file and sets attributes.

        args:
            file: h5py file or group object
        """
        # ic()
        with catch(self.sphere.data_file, 'r') as file:
            # ic(arch_ids)
            for idx in arch_ids:
                try:
                    # ic(idx)
                    arch = EwaldArch(idx=idx, static=True, gi=self.sphere.gi)
                    if not load_2d:
                        # arch.load_from_h5(file['arches'], load_2d=False)
                        self.load_arch_data(file['arches'], arch, idx, load_2d=False)
                        self.data_1d[int(idx)] = arch.copy(include_2d=False)
                        # ic('loaded 1D data', self.data_1d.keys())
                    else:
                        try:
                            if len(arch.int_2d.i_qChi) == 0:
                                pass
                        except TypeError:
                            arch.load_from_h5(file['arches'], load_2d=True)

                        self.data_1d[int(idx)] = arch.copy(include_2d=False)
                        self.data_2d[int(idx)] = {'map_raw': arch.map_raw,
                                                  'bg_raw': arch.bg_raw,
                                                  'mask': arch.mask,
                                                  'int_2d': arch.int_2d}

                        # ic('loaded 1 and 2D data', self.data_1d.keys(), self.data_2d.keys())
                        # ic(idx, self.arches['add_idxs'], self.arches['sub_idxs'])
                        if idx in self.arches['add_idxs']:
                            self.arches['sum_int_2d'] += self.data_2d[int(idx)]['int_2d']
                            # self.arches['sum_map_raw'] += self.data_2d[int(idx)]['map_raw']
                            self.arches['sum_map_raw'] += (self.data_2d[int(idx)]['map_raw'] -
                                                           self.data_2d[int(idx)]['bg_raw'])
                        elif idx in self.arches['sub_idxs']:
                            self.arches['sum_int_2d'] -= self.data_2d[int(idx)]['int_2d']
                            # self.arches['sum_map_raw'] -= self.data_2d[int(idx)]['map_raw']
                            self.arches['sum_map_raw'] -= (self.data_2d[int(idx)]['map_raw'] -
                                                           self.data_2d[int(idx)]['bg_raw'])

                except KeyError:
                    pass

    @staticmethod
    def load_arch_data(file, arch, idx, load_2d=True):
        # ic()
        if str(idx) not in file:
            print("No data can be found")
        else:
            grp = file[str(idx)]
            if 'type' in grp.attrs:
                if grp.attrs['type'] == 'EwaldArch':
                    if load_2d:
                        lst_attr = [
                            "map_raw", "mask", "map_norm", "scan_info", "ai_args",
                            "gi", "static", "poni_dict", "bg_raw"
                        ]
                        utils.h5_to_attributes(arch, grp, lst_attr)
                        arch.int_1d.from_hdf5(grp['int_1d'])
                        arch.int_2d.from_hdf5(grp['int_2d'])
                    else:
                        lst_attr = [
                            "scan_info", "ai_args",
                            "gi", "static", "poni_dict"
                        ]
                        utils.h5_to_attributes(arch, grp, lst_attr)
                        arch.int_1d.from_hdf5(grp['int_1d'])

                    # if self.poni_file is not None:
                    if arch.poni_dict is not None:
                        arch.integrator = create_ai_from_dict(arch.poni_dict)

    def get_arches_sum(self, idxs, idxs_memory):
        # ic()
        new_idxs = set([int(idx) for idx in idxs])
        old_idxs, data_keys = set(self.arches['idxs']), set(self.data_2d.keys())

        changed_idxs = new_idxs ^ old_idxs
        load_idxs = changed_idxs - data_keys

        # ic(new_idxs, old_idxs, changed_idxs, load_idxs)

        add_from_data = (new_idxs - old_idxs) & data_keys
        add_from_h5 = new_idxs - old_idxs - data_keys
        self.arches['add_idxs'] = [int(k) for k in add_from_h5]

        sub_from_data = (old_idxs - new_idxs) & data_keys
        sub_from_h5 = old_idxs - new_idxs - data_keys
        self.arches['sub_idxs'] = [int(k) for k in sub_from_h5]

        for x in load_idxs:
            if int(x) in idxs_memory:
                idxs_memory.remove(int(x))

        for k in add_from_data:
            try:
                self.arches['sum_int_2d'] += self.data_2d[int(k)]['int_2d']
                self.arches['sum_map_raw'] += self.data_2d[int(k)]['map_raw']
            except ValueError:
                self.arches['sum_int_2d'] = self.data_2d[int(k)]['int_2d']
                self.arches['sum_map_raw'] = self.data_2d[int(k)]['map_raw']

        for k in sub_from_data:
            try:
                self.arches['sum_int_2d'] -= self.data_2d[int(k)]['int_2d']
                self.arches['sum_map_raw'] -= self.data_2d[int(k)]['map_raw']
            except ValueError:
                self.arches['sum_int_2d'] = self.data_2d[int(k)]['int_2d']
                self.arches['sum_map_raw'] = self.data_2d[int(k)]['map_raw']
