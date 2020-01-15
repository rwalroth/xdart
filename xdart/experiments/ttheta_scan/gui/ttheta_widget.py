# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
from functools import partial
import time
from queue import Queue
import multiprocessing as mp
import copy

# Other imports
import h5py
from matplotlib import pyplot as plt

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
QWidget = QtWidgets.QWidget
QSizePolicy = QtWidgets.QSizePolicy
QFileDialog = QtWidgets.QFileDialog
from pyqtgraph.parametertree import (
    Parameter, ParameterTree, ParameterItem, registerParameterType
)

## This module imports
from ....classes.ewald import EwaldSphere
from ....utils import catch_h5py_file as catch
from .... import utils as ut
from ....gui.gui_utils import defaultWidget
from .tthetaUI import Ui_Form
from .h5viewer import H5Viewer
from .display_frame_widget import displayFrameWidget
from .integrator import integratorTree
from .sphere_threads import integratorThread
from .metadata import metadataWidget
from .wranglers import specWrangler, liveSpecWrangler

wranglers = {
    'SPEC': specWrangler, 
    'Live Spec': liveSpecWrangler
}

formats = [
    str(f.data(), encoding='utf-8').lower() for f in
    Qt.QtGui.QImageReader.supportedImageFormats()
]

def spherelocked(func):
    def wrapper(self, *args, **kwargs):
        if isinstance(self.sphere, EwaldSphere):
            with self.sphere.sphere_lock:
                func(self, *args, **kwargs)
                return func(self, *args, **kwargs)
    return wrapper

class tthetaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Data object initialization
        self.file_lock = mp.Condition()
        self.fname = None
        self.sphere = None
        
        self.arch = None
        self.integrator_thread = integratorThread(self.sphere, self.arch)
        self.timer = Qt.QtCore.QTimer()
        self.timer.timeout.connect(self.clock)
        self.timer.start(42)

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # H5Viewer setup
        self.h5viewer = H5Viewer(self.file_lock, self.fname, self.ui.hdf5Frame)
        self.h5viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.hdf5Frame.setLayout(self.h5viewer.layout)
        self.h5viewer.ui.listData.addItem('No data')
        self.h5viewer.ui.listData.setCurrentRow(0)
        self.h5viewer.ui.listScans.addItem('No scans')

        # H5Viewer signal connections
        self.h5viewer.ui.listScans.itemDoubleClicked.connect(self.load_and_set)
        self.h5viewer.ui.listData.itemClicked.connect(self.set_data)
        self.h5viewer.actionOpen.triggered.connect(self.open_file)
        self.h5viewer.actionSaveImage.triggered.connect(self.save_image)
        self.h5viewer.actionSaveArray.triggered.connect(self.save_array)
        self.h5viewer.actionSaveData.triggered.connect(self.save_data)
        self.h5viewer.actionSaveDataAs.triggered.connect(self.save_data_as)
        self.h5viewer.actionNewFile.triggered.connect(self.new_file)
        self.h5viewer.actionSetDefaults.triggered.connect(self.set_defaults)

        # DisplayFrame setup
        self.displayframe = displayFrameWidget(parent=self.ui.middleFrame)
        self.ui.middleFrame.setLayout(self.displayframe.ui.layout)

        # DisplayFrame signal connections
        self.displayframe.ui.pushRight.clicked.connect(self.next_arch)
        self.displayframe.ui.pushLeft.clicked.connect(self.prev_arch)
        self.displayframe.ui.pushRightLast.clicked.connect(self.last_arch)
        self.displayframe.ui.pushLeftLast.clicked.connect(self.first_arch)

        # IntegratorFrame setup
        self.integratorTree = integratorTree()
        self.ui.integratorFrame.setLayout(self.integratorTree.ui.layout)

        # Integrator signal connections
        self.integratorTree.parameters.sigTreeStateChanged.connect(
            self.parse_param_change
        )
        self.integratorTree.ui.integrateBAI1D.clicked.connect(self.bai_1d)
        self.integratorTree.ui.integrateBAI2D.clicked.connect(self.bai_2d)
        self.integratorTree.ui.setupMG.clicked.connect(self.mg_setup)
        self.integratorTree.ui.integrateMG1D.clicked.connect(self.mg_1d)
        self.integratorTree.ui.integrateMG2D.clicked.connect(self.mg_2d)
        self.integrator_thread.update.connect(self.displayframe.update)
        self.integrator_thread.finished.connect(self.thread_finished)

        # Metadata setup
        self.metawidget = metadataWidget()
        self.ui.metaFrame.setLayout(self.metawidget.layout)

        # Wrangler frame setup
        for name, w in wranglers.items():
            self.ui.wranglerStack.addWidget(
                w(
                    self.fname,
                    self.file_lock
                )
            )
            self.ui.wranglerBox.addItem(name)
        self.ui.wranglerStack.currentChanged.connect(self.set_wrangler)
        self.command_queue = Queue()
        self.set_wrangler(self.ui.wranglerStack.currentIndex())
        
        args = self.get_all_args()
        self.sphere = EwaldSphere(name='null_main', **args)

        self.show()
    
    def set_wrangler(self, qint):
        self.wrangler = self.ui.wranglerStack.widget(qint)
        self.wrangler.input_q = self.command_queue
        self.wrangler.fname = self.fname
        self.wrangler.file_lock = self.file_lock
        self.wrangler.sigStart.connect(self.start_wrangler)
        self.wrangler.sigUpdateData.connect(self.update_data)
        self.wrangler.sigUpdateFile.connect(self.new_scan)
        self.wrangler.finished.connect(self.wrangler_finished)
        self.wrangler.setup()
    
    def clock(self):
        pass
        #if isinstance(self.sphere, EwaldSphere):
        #    if self.sphere.sphere_lock._lock._count > 0:
        #        self.h5viewer.ui.listScans.setEnabled(False)
        #        self.h5viewer.ui.listData.setEnabled(False)
        #    else:
        #        self.h5viewer.ui.listScans.setEnabled(True)
        #        self.h5viewer.ui.listData.setEnabled(True)
    
    def open_file(self):
        """Reads hdf5 file, populates list of scans in h5viewer. 
        Creates persistent h5py file object.
        """
        fname, _ = QFileDialog().getOpenFileName()
        self.set_file(fname)

    def set_file(self, fname):
        with self.file_lock:
            if fname == '' or fname == self.fname:
                return
            
            try:
                with catch(fname, 'a') as f:
                    self.fname = fname
            except Exception as e:
                print(e)

            self.h5viewer.fname = self.fname
            self.h5viewer.update(self.fname)
            if not self.wrangler.thread.isRunning():
                self.wrangler.set_fname(self.fname)
    
    def load_sphere(self, name):
        """Loads EwaldSphere object into memory
        """
        if not isinstance(self.sphere, EwaldSphere):
            self.sphere = EwaldSphere(name)
        
        elif self.sphere.name != name:
            with self.sphere.sphere_lock:
                self.sphere = EwaldSphere(name)
        while True:
            try:
                with self.file_lock:
                    with h5py.File(self.fname, 'r') as file:
                        self.sphere.load_from_h5(file)
                        break
            except OSError:
                pass
        self.displayframe.sphere = self.sphere
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
        self.h5viewer.set_data(self.sphere)
        #self.h5viewer.ui.listData.setCurrentRow(0)
        self.integratorTree.update(self.sphere)
        args = self.get_all_args()
        self.sphere.bai_1d_args.update(args['bai_1d_args'])
        self.sphere.bai_2d_args.update(args['bai_2d_args'])
        self.sphere.mg_args.update(args['mg_args'])
        self.metawidget.update(self.sphere)
        if self.wrangler.scan_name != self.sphere.name:
            self.enable_integration(True)
        elif self.wrangler.scan_name == self.sphere.name:
            self.enable_integration(False)
    
    def update_data(self, q):
        if self.sphere is None:
            self.sphere = EwaldSphere(self.wrangler.scan_name)
            with self.sphere.sphere_lock:
                with self.file_lock:
                    with catch(self.fname, 'r') as file:
                        self.sphere.load_from_h5(file)
        else:
            with self.sphere.sphere_lock:
                if (q not in self.sphere.arches.index and 
                        self.sphere.name == self.wrangler.scan_name):
                    with self.file_lock:
                        with catch(self.fname, 'r') as file:
                            self.sphere.load_from_h5(
                                file, replace=False, data_only=True, 
                                arches=[q], set_mg=False
                            )
        self.update_all()
            
                
    def set_data(self, q):
        """Updates data in displayframe
        """
        if q.data(0) != 'No data':
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)

            if not isinstance(self.sphere, EwaldSphere):
                return
            
            elif q.data(0) == 'Overall' or 'scan' in q.data(0):
                self.arch = None
                self.displayframe.arch = None
                self.displayframe.update()
                self.displayframe.ui.imageIntRaw.setEnabled(False)
                self.displayframe.ui.imageMethod.setEnabled(True)
                self.displayframe.ui.imageMask.setEnabled(False)

                self.integratorTree.ui.integrateBAIAll.setChecked(True)
                self.integratorTree.ui.integrateBAIAll.setEnabled(False)
                
                self.metawidget.update(self.sphere)
            
            else:
                try:
                    self.arch = int(q.data(0))
                except ValueError:
                    return
                self.displayframe.arch = int(q.data(0))
                self.displayframe.update()
                self.displayframe.ui.imageIntRaw.setEnabled(True)
                self.displayframe.ui.imageMethod.setEnabled(False)
                self.displayframe.ui.imageMask.setEnabled(True)

                self.integratorTree.ui.integrateBAIAll.setEnabled(True)
                
                self.metawidget.update(self.sphere, self.arch)

    def load_and_set(self, q):
        """Combination of load and setting functions
        """
        if q.data(0) != 'No scans':
            self.h5viewer.ui.listData.clear()
            self.h5viewer.ui.listData.addItem('Loading...')
            Qt.QtGui.QApplication.processEvents()

            self.load_sphere(q.data(0))
            self.set_data(q)
    
    def save_image(self):
        """Saves currently displayed image. Formats are automatically
        grabbed from Qt. Also implements tiff saving.
        """
        filter = "Images ("
        for f in formats:
            filter += "*." + f + " "

        filter += "*.tiff)"

        fname, _ = QFileDialog.getSaveFileName(filter=filter)
        if fname == '':
            return

        name, ext = fname.split('.')
        if ext.lower() in formats:
            self.displayframe.image.save(fname)
        
        elif ext.lower() == 'tiff':
            data = self.displayframe.update_image(self.sphere, self.arch)
            plt.imsave(fname, data.T, cmap='gray')
    
    def save_array(self):
        """Saves currently displayed data. Currently supports .xye
        and .csv.
        """
        fname, _ = QFileDialog.getSaveFileName(
            filter="XRD Files (*.xye *.csv)"
        )
        if fname == '':
            return

        xdata, ydata = self.displayframe.update_plot(self.sphere, self.arch)

        name, ext = fname.split('.')
        if ext.lower() == 'xye':
            ut.write_xye(fname, xdata, ydata)
        
        elif ext.lower() == 'csv':
            ut.write_csv(fname, xdata, ydata)
    
    def save_data(self):
        """Saves all data to hdf5 file.
        """
        if isinstance(self.sphere, EwaldSphere):
            if self.fname is not None:
                with self.file_lock:
                    with catch(self.fname, 'a') as file:
                        self.sphere.save_to_h5(file, replace=True)
                        self.h5viewer.update(self.fname)
            else:
                self.save_data_as()
    
    def save_data_as(self):
        """Saves all data to hdf5 file.
        """
        with self.file_lock:
            if isinstance(self.sphere, EwaldSphere):
                self.open_file()
                self.save_data()
    
    def new_file(self):
        fname, _ = QFileDialog.getSaveFileName()
        self.set_file(fname)
    
    def set_defaults(self):
        parameters = [self.integratorTree.parameters]
        for i in range(self.ui.wranglerStack.count()):
            w = self.ui.wranglerStack.widget(i)
            parameters.append(w.parameters)
        self.defaultWidget = defaultWidget(parameters)
        self.defaultWidget.show()
    
    def next_arch(self):
        """Advances to next arch in data list, updates displayframe
        """
        if (self.arch == self.sphere.arches.iloc[-1].idx or 
            self.arch is None or
            self.h5viewer.ui.listData.currentRow() == self.h5viewer.ui.listData.count() - 1):
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.currentRow() + 1
            )
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)
            self.set_data(self.h5viewer.ui.listData.currentItem())
    
    def prev_arch(self):
        """Goes back one arch in data list, updates displayframe
        """
        if (self.arch == self.sphere.arches.iloc[0].idx or 
            self.arch is None or
            self.h5viewer.ui.listData.currentRow() == 1):
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.currentRow() - 1
            )
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)
            self.set_data(self.h5viewer.ui.listData.currentItem())
    
    def last_arch(self):
        """Advances to last arch in data list, updates displayframe, and
        set auto_last to True
        """
        if self.arch is None:
            pass

        else: 
            if self.arch == self.sphere.arches.iloc[-1].idx:
                pass

            else:
                self.h5viewer.ui.listData.setCurrentRow(
                    self.h5viewer.ui.listData.count() - 1
                )
                self.set_data(self.h5viewer.ui.listData.currentItem())
        
            self.displayframe.auto_last = True
            self.displayframe.ui.pushRightLast.setEnabled(False)

    def first_arch(self):
        """Goes to first arch in data list, updates displayframe
        """
        if self.arch == self.sphere.arches.iloc[0].idx or self.arch is None:
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(1)
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)
            self.set_data(self.h5viewer.ui.listData.currentItem())
    
    def close(self):
        """Tries a graceful close.
        """
        del(self.sphere)
        del(self.displayframe.sphere)
        del(self.arch)
        del(self.displayframe.arch)
        super().close()
    
    @spherelocked
    def parse_param_change(self, param, changes, args=None):
        if args is None:
            bai_1d_args = self.sphere.bai_1d_args
            bai_2d_args = self.sphere.bai_2d_args
            mg_args = self.sphere.mg_args
        else:
            bai_1d_args = args['bai_1d_args']
            bai_2d_args = args['bai_2d_args']
            mg_args = args['mg_args']
        for change in changes:
            SI = False
            smg = False
            d1 = False
            par = change[0]
            while par.parent() is not None:
                if par.name() == 'Integrate 1D':
                    d1 = True
                elif par.name() == 'Multi Geometry Setup':
                    smg = True
                    break
                elif par.name() == 'Single Image':
                    SI = True
                    break
                par = par.parent()
            if SI:
                if d1:
                    self.update_args(change, bai_1d_args)
                else:
                    self.update_args(change, bai_2d_args)
            else:
                if smg:
                    self.update_args(change, mg_args)
                else:
                    with self.integrator_thread.lock:
                        if d1:
                            self.update_args(
                                change, self.integrator_thread.mg_1d_args)
                        else:
                            self.update_args(
                                change, self.integrator_thread.mg_2d_args)
    

    def update_args(self, change, args):
        if change[2] == 'None':
            upval = None
        else:
            upval = change[2]
        if 'range' in change[0].parent().name():
            _range = change[0].parent()
            if _range.child('Auto').value():
                args[_range.name()] = None
            else:
                args[_range.name()] = [
                    _range.child('Low').value(),
                    _range.child('High').value(),
                ]
        elif change[0].name() == 'polarization_factor':
            if change[0].parent().child('Apply polarization factor').value():
                args['polarization_factor'] = upval

        elif change[0].name() == 'Apply polarization factor':
            if upval:
                args['polarization_factor'] = \
                    self.integratorTree.bai_1d_pars.child('polarization_factor').value()
            else:
                args['polarization_factor'] = None
        else:
            args.update(
                [(change[0].name(), upval)]
            )
    
    def bai_1d(self, q):
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            if self.integratorTree.ui.integrateBAIAll.isChecked():
                self.integrator_thread.method = 'bai_1d_all'
            else:
                self.integrator_thread.method = 'bai_1d_SI'
        self.enable_integration(False)
        self.integrator_thread.start()

    def bai_2d(self, q):
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            if self.integratorTree.ui.integrateBAIAll.isChecked():
                self.integrator_thread.method = 'bai_2d_all'
            else:
                self.integrator_thread.method = 'bai_2d_SI'
        self.enable_integration(False)
        self.integrator_thread.start()

    def mg_setup(self, q):
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            self.integrator_thread.method = 'mg_setup'
        self.enable_integration(False)
        self.integrator_thread.start()

    def mg_1d(self, q):
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            self.integrator_thread.method = 'mg_1d'
        self.enable_integration(False)
        self.integrator_thread.start()
    
    def mg_2d(self, q):
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            self.integrator_thread.method = 'mg_2d'
        self.enable_integration(False)
        self.integrator_thread.start()
    
    def enable_integration(self, enable=True):
        self.integratorTree.tree.setEnabled(enable)
        
        self.integratorTree.ui.integrateBAI1D.setEnabled(enable)
        self.integratorTree.ui.integrateBAI2D.setEnabled(enable)
        self.integratorTree.ui.setupMG.setEnabled(enable)
        self.integratorTree.ui.integrateMG1D.setEnabled(enable)
        self.integratorTree.ui.integrateMG2D.setEnabled(enable)

    def update_all(self):
        self.displayframe.update()
        self.h5viewer.set_data(self.sphere)
        if self.displayframe.auto_last:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.count() - 1
            )
    
    def thread_finished(self):
        self.enable_integration(True)
        self.ui.wranglerBox.setEnabled(True)
        self.wrangler.enabled(True)
        self.h5viewer.set_open_enabled(True)
        self.update()
    
    def new_scan(self, name):
        self.h5viewer.update(self.fname)
        if isinstance(self.sphere, EwaldSphere):
            if self.sphere.name == name or self.sphere.name == 'null_main':
                self.load_sphere(name)
        else:
            self.load_sphere(name)

    def start_wrangler(self):
        if self.fname is None:
            self.new_file()
        self.ui.wranglerBox.setEnabled(False)
        self.wrangler.enabled(False)
        self.h5viewer.set_open_enabled(False)
        args = self.get_all_args()
        self.wrangler.sphere_args = copy.deepcopy(args)
        self.wrangler.setup()
        self.wrangler.thread.start()
    
    def wrangler_finished(self):
        if isinstance(self.sphere, EwaldSphere):
            if self.sphere.name == self.wrangler.scan_name:
                self.thread_finished()
            else:
                self.ui.wranglerBox.setEnabled(True)
                self.wrangler.enabled(True)
        else:
            self.ui.wranglerBox.setEnabled(True)
            self.wrangler.enabled(True)
    
    def unroll_tree(self, changes, param):
        if param.hasChildren():
            for child in param.children():
                if child.isType('group'):
                    changes = self.unroll_tree(changes, child)
                else:
                    changes.append((child, None, child.value()))
        elif not param.isType('group'):
            changes.append((param, None, param.value()))
        
        return changes
        
    def get_all_args(self):
        args = {
            'bai_1d_args': {},
            'bai_2d_args': {},
            'mg_args': {}
        }
        changes = []
        changes = self.unroll_tree(changes, self.integratorTree.parameters)
        self.parse_param_change(None, changes, args)
        return args


    def pause_wrangler(self):
        if self.batch_integrator.isRunning():
            self.command_queue.put('pause')

    def continue_wrangler(self):
        if self.batch_integrator.isRunning():
            self.command_queue.put('continue')

    def stop_wrangler(self):
        if self.batch_integrator.isRunning():
            self.command_queue.put('stop')

                


