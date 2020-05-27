# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from queue import Queue
import multiprocessing as mp
import copy
import os
import traceback

# Other imports
import h5py
from matplotlib import pyplot as plt

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
QWidget = QtWidgets.QWidget
QSizePolicy = QtWidgets.QSizePolicy
QFileDialog = QtWidgets.QFileDialog

## This module imports
from xdart.classes.ewald import EwaldSphere
from xdart.utils import catch_h5py_file as catch
from xdart import utils as ut
from .timescanUI import Ui_Form
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

class timescanWidget(QWidget):
    """Tab for integrating data collected by a scanning area detector.
    As of current version, only handles a single angle (2-theta).
    Displays raw images, stitched Q Chi arrays, and integrated I Q
    arrays. Also displays metadata and exposes parameters for
    controlling integration.
    
    children:
        displayframe: widget which handles displaying images and
            plotting data.
        h5viewer: Has a file explorer panel for loading scans, and
            a panel which shows images that are associated with the
            loaded scan. Has other file saving and loading functions
            as well as configuration saving and loading functions.
        integrator_thread: Not visible to user, but a sub-thread which
            handles integration to free resources for the gui
        integratorTree: Widget for setting the basic integration
            parameters. Also has buttons for starting integration.
        metawidget: Table wiget which displays metadata either for
            entire scan or individual image.
        
    attributes:
        arch: int, idx of current arch # TODO: this should be an EwaldArch
        command_queue: Queue, used to send commands to wrangler
        dirname: str, absolute path of current directory for scan
        file_lock: mp.Condition, process safe lock
        fname: str, current data file name
        sphere: EwaldSphere, current scan data
        timer: QTimer, currently unused but can be used for periodic
            functions.
        ui: Ui_Form, layout from qtdesigner
    
    methods:
        bai_1d: Sends signal to thread to start integrating 1d
        bai_2d:  Sends signal to thread to start integrating 2d
        clock: Unimplemented, used for periodic updates
        close: Handles cleanup prior to closing
        continue_wrangler, pause_wrangler, stop_wrangler: send commands
            to wrangler thread. Wired to signals in wrangler
        enable_integration: Sets enabled status of widgets related to
            integration
        first_arch, last_arch, next_arch: Handle moving between
            different arches in the overall sphere
        get_args: Calls integrator tree get_args on sphere
        load_and_set: Combination of load and set methods. Also governs
            file explorer behavior in h5viewer.
        load_sphere: 
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Data object initialization
        self.file_lock = mp.Condition()
        self.dirname = os.path.join(os.path.dirname(__file__).split('xdart')[0],
                                    os.path.join('xdart', 'data'))
        if not os.path.isdir(self.dirname):
            os.mkdir(self.dirname)
        self.fname = os.path.join(self.dirname, 'default.hdf5')
        self.sphere = EwaldSphere('null_main', data_file=self.fname)
        
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

        # H5Viewer signal connections
        self.h5viewer.ui.listScans.itemDoubleClicked.connect(self.load_and_set)
        self.h5viewer.ui.listData.itemClicked.connect(self.set_data)
        self.h5viewer.actionOpen.triggered.connect(self.open_file)
        self.h5viewer.actionSaveImage.triggered.connect(self.save_image)
        self.h5viewer.actionSaveArray.triggered.connect(self.save_array)
        self.h5viewer.actionSaveDataAs.triggered.connect(self.save_data_as)
        self.h5viewer.actionNewFile.triggered.connect(self.new_file)

        # DisplayFrame setup
        self.displayframe = displayFrameWidget(parent=self.ui.middleFrame)
        self.ui.middleFrame.setLayout(self.displayframe.ui.layout)

        # DisplayFrame signal connections
        self.displayframe.ui.pushRight.clicked.connect(self.next_arch)
        self.displayframe.ui.pushLeft.clicked.connect(self.prev_arch)
        self.displayframe.ui.pushRightLast.clicked.connect(self.last_arch)
        self.displayframe.ui.pushLeftLast.clicked.connect(self.first_arch)
        self.displayframe.ui.imageNorm.activated.connect(self.update_display_frame)
        #self.displayframe.ui.imageMethod.activated.connect(self.update_display_frame)
        self.displayframe.ui.imageUnit.activated.connect(self.update_display_frame)
        #self.displayframe.ui.imageNRP.activated.connect(self.update_display_frame)
        self.displayframe.ui.imageMask.stateChanged.connect(self.update_display_frame)
        #self.displayframe.ui.shareAxis.stateChanged.connect(self.update_display_frame)
        self.displayframe.ui.plotMethod.activated.connect(self.update_display_frame)
        self.displayframe.ui.plotUnit.activated.connect(self.update_display_frame)
        #self.displayframe.ui.plotNRP.activated.connect(self.update_display_frame)
        #self.displayframe.ui.plotOverlay.stateChanged.connect(self.update_display_frame)
        
        # IntegratorFrame setup
        self.integratorTree = integratorTree()
        self.ui.integratorFrame.setLayout(self.integratorTree.ui.verticalLayout)
        self.integratorTree.update(self.sphere)

        # Integrator signal connections
        self.integratorTree.sigUpdateArgs.connect(self.get_args)
        self.integratorTree.ui.integrate1D.clicked.connect(self.bai_1d)
        self.integratorTree.ui.integrate2D.clicked.connect(self.bai_2d)
        self.integrator_thread.update.connect(self.update_display_frame)
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
        
        self.get_args('bai_1d')
        self.get_args('bai_2d')
        
        # Setup defaultWidget in h5viewer with parameters
        parameters = [self.integratorTree.parameters]
        for i in range(self.ui.wranglerStack.count()):
            w = self.ui.wranglerStack.widget(i)
            parameters.append(w.parameters)
        self.h5viewer.defaultWidget.set_parameters(parameters)
        
        # Update h5viewer with dirname
        # TODO: Can this be moved earlier in __init__?
        self.h5viewer.update(self.dirname)

        self.show()
    
    def set_wrangler(self, qint):
        """Sets the wrangler based on the selected item in the dropdown.
        Syncs the wrangler's attributes and wires signals as needed.
        
        args:
            qint: Qt int, index of the new wrangler
        """
        self.wrangler = self.ui.wranglerStack.widget(qint)
        self.wrangler.input_q = self.command_queue
        self.wrangler.fname = self.fname
        self.wrangler.file_lock = self.file_lock
        self.wrangler.sigStart.connect(self.start_wrangler)
        self.wrangler.sigUpdateData.connect(self.update_data)
        self.wrangler.sigUpdateFile.connect(self.new_scan)
        self.wrangler.finished.connect(self.wrangler_finished)
        self.wrangler.setup()
    
    def update_display_frame(self):
        """Calls displayframe update. Used to pass on self.sphere and
        arch to displayframe.
        """
        # TODO: See if sphere can be held as a shared memory object.
        self.displayframe.update(self.sphere, self.arch)
    
    def clock(self):
        """Called whenever the QTimer counts down.
        """
        pass
        #if isinstance(self.sphere, EwaldSphere):
        #    if self.sphere.sphere_lock._lock._count > 0:
        #        self.h5viewer.ui.listScans.setEnabled(False)
        #        self.h5viewer.ui.listData.setEnabled(False)
        #    else:
        #        self.h5viewer.ui.listScans.setEnabled(True)
        #        self.h5viewer.ui.listData.setEnabled(True)
    
    def open_file(self):
        """Changes the directory being displayed in the file explorer.
        """
        # TODO: Change name to what it is supposed to be
        dirname = QFileDialog().getExistingDirectory()
        self.h5viewer.update(dirname)
        self.dirname = dirname

    def set_file(self, fname):
        """Changes the data file. Ensures children with same file name
        are properly synced.
        
        args:
            fname: str, absolute path for data file
        """
        with self.file_lock:
            if fname in ('', self.fname):
                return
            
            try:
                with catch(fname, 'a') as _:
                    self.fname = fname
                    self.sphere.data_file = fname
            except:
                traceback.print_exc()

            self.h5viewer.fname = self.fname
            if not self.wrangler.thread.isRunning():
                self.wrangler.set_fname(self.fname)
    
    def load_sphere(self, name):
        """Loads EwaldSphere object into memory.
        
        args:
            name: str, name of the scan
        """
        # TODO: Don't initialize sphere, find way to reset sphere
        if not isinstance(self.sphere, EwaldSphere):
            self.sphere = EwaldSphere(name, data_file=self.fname)
        
        elif self.sphere.name != name:
            self.sphere = EwaldSphere(name, data_file=self.fname)
        with self.file_lock:
            self.sphere.load_from_h5()
        self.displayframe.sphere = self.sphere
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
        self.h5viewer.set_data(self.sphere)
        self.integratorTree.update(self.sphere)
        self.get_args('bai_1d')
        self.get_args('bai_2d')
        self.metawidget.update(self.sphere)
        if self.wrangler.scan_name != self.sphere.name:
            self.enable_integration(True)
        elif self.wrangler.scan_name == self.sphere.name:
            self.enable_integration(False)
    
    def update_data(self, q):
        """Called by signal from wrangler. If the current scan name
        is the same as the wrangler scan name, updates the data in
        memory.
        """
        with self.sphere.sphere_lock:
            if self.sphere.name == self.wrangler.scan_name:
                with self.file_lock:
                    self.sphere.load_from_h5(
                        replace=False, data_only=True, 
                        set_mg=False
                    )
                    self.update_all()
            
                
    def set_data(self, q):
        """Connected to h5viewer, sets the data in displayframe based
        on the selected image or overall data.
        
        args:
            q: QListItem, the item selected in the h5viewer.
        """
        if q.data(0) != 'No data':
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)

            if not isinstance(self.sphere, EwaldSphere):
                return
            
            if q.data(0) == 'Overall' or 'scan' in q.data(0):
                self.arch = None
                self.displayframe.arch = None
                self.displayframe.update(self.sphere, self.arch)
                self.displayframe.ui.imageNorm.setEnabled(False)
                self.displayframe.ui.imageMask.setEnabled(False)

                self.integratorTree.ui.all1D.setChecked(True)
                self.integratorTree.ui.all1D.setEnabled(False)
                self.integratorTree.ui.all2D.setChecked(True)
                self.integratorTree.ui.all2D.setEnabled(False)
                
                self.metawidget.update(self.sphere)
            
            else:
                try:
                    self.arch = int(q.data(0))
                except ValueError:
                    return
                self.displayframe.arch = int(q.data(0))
                self.displayframe.update(self.sphere, self.arch)
                self.displayframe.ui.imageNorm.setEnabled(True)
                self.displayframe.ui.imageMask.setEnabled(True)

                self.integratorTree.ui.all1D.setEnabled(True)
                self.integratorTree.ui.all2D.setEnabled(True)
                
                self.metawidget.update(self.sphere, self.arch)

    def load_and_set(self, q):
        """Combination of load and setting functions. Connected to
        h5viewer.
        
        q: QListItem, item selected in h5viewer.
        """
        if q.data(0) != 'No scans':
            if q.data(0) == '..':
                if self.dirname[-1] in ['/', '\\']:
                    up = os.path.dirname(self.dirname[:-1])
                else:
                    up = os.path.dirname(self.dirname)
                
                if (os.path.isdir(up) and
                    os.path.splitdrive(up)[1] != ''):
                    self.dirname = up
                    self.h5viewer.update(self.dirname)
            elif '/' in q.data(0):
                self.dirname = os.path.join(self.dirname, q.data(0))
                self.h5viewer.update(self.dirname)
            else:
                self.h5viewer.ui.listData.clear()
                self.h5viewer.ui.listData.addItem('Loading...')
                Qt.QtGui.QApplication.processEvents()
                
                self.set_file(os.path.join(self.dirname, q.data(0)))
                self.load_sphere(q.data(0).split('.')[0])
                try:
                    self.set_data(q)
                except TypeError:
                    traceback.print_exc()
    
    def save_image(self):
        """Saves currently displayed image. Formats are automatically
        grabbed from Qt. Also implements tiff saving.
        """
        ext_filter = "Images ("
        for f in formats:
            ext_filter += "*." + f + " "

        ext_filter += "*.tiff)"

        fname, _ = QFileDialog.getSaveFileName(filter=ext_filter)
        if fname == '':
            return

        _, ext = fname.split('.')
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

        _, ext = fname.split('.')
        if ext.lower() == 'xye':
            ut.write_xye(fname, xdata, ydata)
        
        elif ext.lower() == 'csv':
            ut.write_csv(fname, xdata, ydata)
    
    def save_data_as(self):
        """Saves all data to hdf5 file. Also sets fname to be the
        selected file.
        """
        fname, _ = QFileDialog.getSaveFileName()
        with self.file_lock:
            with catch(self.fname, 'r') as f1:
                with catch(fname, 'w') as f2:
                    for key in f1:
                        f1.copy(f1[key], f2)
                    for attr in f1.attrs:
                        f2.attrs[attr] = f1.attrs[attr]
        self.set_file(fname)
    
    def new_file(self):
        """Calls file dialog and sets the file name.
        """
        fname, _ = QFileDialog.getSaveFileName()
        self.set_file(fname)
    
    def next_arch(self):
        """Advances to next arch in data list, updates displayframe
        """
        if (self.arch == self.sphere.arches.iloc(-1).idx or 
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
        if (self.arch == self.sphere.arches.iloc(0).idx or 
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
            if self.arch == self.sphere.arches.iloc(-1).idx:
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
        if self.arch == self.sphere.arches.iloc(0).idx or self.arch is None:
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
    
    def get_args(self, key):
        """Calls integratorTree get_args function.
        """
        self.integratorTree.get_args(self.sphere, key)
    
    def bai_1d(self, q):
        """Uses the integrator_thread attribute to call bai_1d
        """
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            if self.integratorTree.ui.all1D.isChecked() or type(self.arch) != int:
                self.integrator_thread.method = 'bai_1d_all'
            else:
                self.integrator_thread.method = 'bai_1d_SI'
        self.enable_integration(False)
        with self.file_lock:
            with catch(self.sphere.data_file, 'a') as file:
                ut.dict_to_h5(self.sphere.bai_1d_args, file, 'bai_1d_args')
        self.integrator_thread.start()

    def bai_2d(self, q):
        """Uses the integrator_thread attribute to call bai_2d
        """
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            if self.integratorTree.ui.all2D.isChecked():
                self.integrator_thread.method = 'bai_2d_all'
            else:
                self.integrator_thread.method = 'bai_2d_SI'
        self.enable_integration(False)
        with self.file_lock:
            with catch(self.sphere.data_file, 'a') as file:
                ut.dict_to_h5(self.sphere.bai_2d_args, file, 'bai_2d_args')
        self.integrator_thread.start()

    def mg_setup(self, q):
        """Uses the integrator_thread attribute to call mg_setup
        """
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            self.integrator_thread.method = 'mg_setup'
        self.enable_integration(False)
        self.integrator_thread.start()

    def mg_1d(self, q):
        """Uses the integrator_thread attribute to call mg_1d
        """
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            self.integrator_thread.method = 'mg_1d'
        self.enable_integration(False)
        self.integrator_thread.start()
    
    def mg_2d(self, q):
        """Uses the integrator_thread attribute to call mg_2d
        """
        with self.integrator_thread.lock:
            self.integrator_thread.sphere = self.sphere
            self.integrator_thread.arch = self.arch
            self.integrator_thread.method = 'mg_2d'
        self.enable_integration(False)
        self.integrator_thread.start()
    
    def enable_integration(self, enable=True):
        """Calls the integratorTree setEnabled function.
        """
        self.integratorTree.setEnabled(enable)

    def update_all(self):
        """Updates all data in displays TODO: Currently taking the most
        time for the main gui thread
        """
        self.displayframe.update(self.sphere, self.arch)
        self.h5viewer.set_data(self.sphere)
        if self.displayframe.auto_last:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.count() - 1
            )
    
    def thread_finished(self):
        """Function connected to threadFinished signals for
        integratorThread
        """
        self.enable_integration(True)
        self.ui.wranglerBox.setEnabled(True)
        self.wrangler.enabled(True)
        self.h5viewer.set_open_enabled(True)
        self.update()
    
    def new_scan(self, name, fname):
        """Connected to sigUpdateFile from wrangler. Called when a new
        scan is started. 
        
        args:
            name: str, scan name
            fname: str, path to data file for scan
        """
        if isinstance(self.sphere, EwaldSphere):
            if self.sphere.name == name or self.sphere.name == 'null_main':
                self.dirname = os.path.dirname(fname)
                self.set_file(fname)
                self.load_sphere(name)
        else:
            self.set_file(fname)
            self.load_sphere(name)
        self.h5viewer.update(self.dirname)

    def start_wrangler(self):
        """Sets up wrangler, ensures properly synced args, and starts
        the wrangler.thread main method.
        """
        self.ui.wranglerBox.setEnabled(False)
        self.wrangler.enabled(False)
        #self.h5viewer.set_open_enabled(False) // why was this here?
        args = {'bai_1d_args': self.sphere.bai_1d_args,
                'bai_2d_args': self.sphere.bai_2d_args}
        self.wrangler.sphere_args = copy.deepcopy(args)
        self.wrangler.setup()
        self.wrangler.thread.start()
    
    def wrangler_finished(self):
        """Called by the wrangler finished signal. If current scan
        matches the wrangler scan, allows for integration.
        """
        if isinstance(self.sphere, EwaldSphere):
            if self.sphere.name == self.wrangler.scan_name:
                self.thread_finished()
            else:
                self.ui.wranglerBox.setEnabled(True)
                self.wrangler.enabled(True)
        else:
            self.ui.wranglerBox.setEnabled(True)
            self.wrangler.enabled(True)

    def pause_wrangler(self):
        """Passes pause signal to wrangler TODO: Do these three need
        to be in the main widget??
        """
        if self.batch_integrator.isRunning():
            self.command_queue.put('pause')

    def continue_wrangler(self):
        if self.batch_integrator.isRunning():
            self.command_queue.put('continue')

    def stop_wrangler(self):
        if self.batch_integrator.isRunning():
            self.command_queue.put('stop')

                


