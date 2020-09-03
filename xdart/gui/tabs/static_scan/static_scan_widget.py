# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from queue import Queue
import multiprocessing as mp
import copy
import os
from collections import OrderedDict

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets, QtCore

# This module imports
from xdart.modules.ewald import EwaldSphere, EwaldArch
from .ui.staticUI import Ui_Form
from .h5viewer import H5Viewer
from .display_frame_widget import displayFrameWidget
from .integrator import integratorTree
from .metadata import metadataWidget
# from .wranglers import specWrangler, liveSpecWrangler, wranglerWidget
from .wranglers import specWrangler, wranglerWidget

QWidget = QtWidgets.QWidget
QSizePolicy = QtWidgets.QSizePolicy
QFileDialog = QtWidgets.QFileDialog

wranglers = {
    'SPEC': specWrangler
}


def spherelocked(func):
    def wrapper(self, *args, **kwargs):
        if isinstance(self.sphere, EwaldSphere):
            with self.sphere.sphere_lock:
                func(self, *args, **kwargs)
                return func(self, *args, **kwargs)

    return wrapper


class staticWidget(QWidget):
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
        arch: EwaldArch, currently loaded arch object
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
        enable_integration: Sets enabled status of widgets related to
            integration
        first_arch, last_arch, next_arch: Handle moving between
            different arches in the overall sphere
        load_and_set: Combination of load and set methods. Also governs
            file explorer behavior in h5viewer.
        load_sphere:
    """

    def __init__(self, local_path=None, parent=None):
        super().__init__(parent)

        # Data object initialization
        self.file_lock = mp.Condition()
        self.local_path = local_path
        self.dirname = os.path.join(local_path)
        if not os.path.isdir(self.dirname):
            os.mkdir(self.dirname)
        self.fname = os.path.join(self.dirname, 'default.hdf5')
        self.sphere = EwaldSphere('null_main',
                                  data_file=self.fname,
                                  keep_in_memory=True)
        self.arch = EwaldArch()
        self.arch_ids = []
        self.arches = OrderedDict()

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # H5Viewer setup
        self.h5viewer = H5Viewer(self.file_lock, self.local_path, self.dirname,
                                 self.sphere, self.arch, self.arch_ids, self.arches,
                                 self.ui.hdf5Frame)
        self.h5viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.hdf5Frame.setLayout(self.h5viewer.layout)
        self.h5viewer.ui.listData.addItem('No data')
        self.h5viewer.ui.listData.setCurrentRow(0)

        # H5Viewer signal connections
        self.h5viewer.sigUpdate.connect(self.set_data)
        self.h5viewer.file_thread.sigTaskStarted.connect(self.thread_state_changed)
        self.h5viewer.sigThreadFinished.connect(self.thread_state_changed)
        self.h5viewer.ui.listData.itemClicked.connect(self.enable_last)

        # DisplayFrame setup
        self.displayframe = displayFrameWidget(self.sphere, self.arch,
                                               self.arch_ids, self.arches,
                                               parent=self.ui.middleFrame)
        self.ui.middleFrame.setLayout(self.displayframe.ui.layout)

        # DisplayFrame signal connections
        self.displayframe.ui.pushRight.clicked.connect(self.next_arch)
        self.displayframe.ui.pushLeft.clicked.connect(self.prev_arch)
        self.displayframe.ui.pushRightLast.clicked.connect(self.last_arch)
        self.displayframe.ui.pushLeftLast.clicked.connect(self.first_arch)
        self.h5viewer.actionSaveImage.triggered.connect(
            self.displayframe.save_image
        )
        self.h5viewer.actionSaveArray.triggered.connect(
            self.displayframe.save_array
        )

        # IntegratorFrame setup
        self.integratorTree = integratorTree(self.sphere, self.arch,
                                             self.file_lock)
        self.ui.integratorFrame.setLayout(self.integratorTree.ui.verticalLayout)
        self.integratorTree.update()

        # Integrator signal connections
        self.integratorTree.integrator_thread.started.connect(self.thread_state_changed)
        self.integratorTree.integrator_thread.update.connect(self.integrator_thread_update)
        self.integratorTree.integrator_thread.finished.connect(self.integrator_thread_finished)

        # Metadata setup
        self.metawidget = metadataWidget(self.sphere, self.arch,
                                         self.arch_ids, self.arches)
        self.ui.metaFrame.setLayout(self.metawidget.layout)

        # Wrangler frame setup
        self.wrangler = wranglerWidget("uninitialized", mp.Condition())
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

        self.integratorTree.get_args('bai_1d')
        self.integratorTree.get_args('bai_2d')

        # Setup defaultWidget in h5viewer with parameters
        parameters = [self.integratorTree.parameters]
        for i in range(self.ui.wranglerStack.count()):
            w = self.ui.wranglerStack.widget(i)
            parameters.append(w.parameters)
        self.h5viewer.defaultWidget.set_parameters(parameters)
        self.h5viewer.load_starting_defaults()

        # self.show()
        """
        self.timer = Qt.QtCore.QTimer()
        self.timer.timeout.connect(self.clock)
        self.timer.start()
    """

    def set_wrangler(self, qint):
        """Sets the wrangler based on the selected item in the dropdown.
        Syncs the wrangler's attributes and wires signals as needed.

        args:
            qint: Qt int, index of the new wrangler
        """
        if 'wrangler' in self.__dict__:
            self.disconnect_wrangler()

        self.wrangler = self.ui.wranglerStack.widget(qint)
        self.wrangler.input_q = self.command_queue
        self.wrangler.fname = self.fname
        self.wrangler.file_lock = self.file_lock
        self.wrangler.sigStart.connect(self.start_wrangler)
        self.wrangler.sigUpdateData.connect(self.update_data)
        self.wrangler.sigUpdateFile.connect(self.new_scan)
        self.wrangler.started.connect(self.thread_state_changed)
        self.wrangler.finished.connect(self.wrangler_finished)
        self.wrangler.setup()
        self.h5viewer.sigNewFile.connect(self.wrangler.set_fname)

    def disconnect_wrangler(self):
        """Disconnects all signals attached the the current wrangler
        """
        for signal in (self.wrangler.sigStart,
                       self.wrangler.sigUpdateData,
                       self.wrangler.sigUpdateFile,
                       self.wrangler.finished,
                       self.h5viewer.sigNewFile):
            while True:
                try:
                    signal.disconnect()
                except TypeError:
                    break

    def thread_state_changed(self):
        """Called whenever a thread is started or finished.
        """
        wrangler_running = self.wrangler.thread.isRunning()
        integrator_running = self.integratorTree.integrator_thread.isRunning()
        loader_running = self.h5viewer.file_thread.running
        same_name = self.sphere.name == self.wrangler.scan_name

        if loader_running:
            self.h5viewer.ui.listData.setEnabled(False)
            self.h5viewer.ui.listScans.setEnabled(False)
            self.h5viewer.set_open_enabled(False)
            self.integratorTree.setEnabled(False)

        elif integrator_running:
            self.h5viewer.ui.listData.setEnabled(True)
            self.integratorTree.setEnabled(False)
            self.h5viewer.ui.listScans.setEnabled(False)
            self.h5viewer.set_open_enabled(False)
            if same_name or wrangler_running:
                self.wrangler.enabled(False)
            else:
                self.wrangler.enabled(True)

        elif wrangler_running:
            self.h5viewer.ui.listData.setEnabled(True)
            self.h5viewer.ui.listScans.setEnabled(True)
            self.h5viewer.set_open_enabled(True)
            self.h5viewer.paramMenu.setEnabled(False)
            self.wrangler.enabled(False)
            if same_name:
                self.integratorTree.setEnabled(False)
            else:
                self.integratorTree.setEnabled(True)

        else:
            self.h5viewer.ui.listData.setEnabled(True)
            self.h5viewer.ui.listScans.setEnabled(True)
            self.h5viewer.set_open_enabled(True)
            self.integratorTree.setEnabled(True)
            self.wrangler.enabled(True)

    def update_data(self, q):
        """Called by signal from wrangler. If the current scan name
        is the same as the wrangler scan name, updates the data in
        memory.
        """
        with self.sphere.sphere_lock:
            if self.sphere.name == self.wrangler.scan_name:
                self.h5viewer.file_thread.queue.put("update_sphere")

                with self.file_lock:
                    self.update_all()

        self.h5viewer.activateWindow()
        self.h5viewer.ui.listData.focusWidget()
        self.h5viewer.ui.listData.setFocus()

    def enable_last(self, q):
        """
        Parameters
        ----------
        q : Qt.QtWidgets.QListWidgetItem
        """
        self.displayframe.auto_last = False
        self.displayframe.ui.pushRightLast.setEnabled(True)

    def set_data(self):
        """Connected to h5viewer, sets the data in displayframe based
        on the selected image or overall data.
        """
        if self.sphere.name != 'null_main':
            print(f'static_scan_widget > updating displayframe')
            self.displayframe.update()

            if self.arch.idx is None:
                # self.displayframe.ui.imageIntRaw.setEnabled(False)
                self.displayframe.ui.imageMask.setEnabled(False)

                self.integratorTree.ui.all1D.setChecked(True)
                self.integratorTree.ui.all1D.setEnabled(False)
                self.integratorTree.ui.all2D.setChecked(True)
                self.integratorTree.ui.all2D.setEnabled(False)

            else:
                # self.displayframe.ui.imageIntRaw.setEnabled(True)
                self.displayframe.ui.imageMask.setEnabled(True)

                self.integratorTree.ui.all1D.setEnabled(True)
                self.integratorTree.ui.all2D.setEnabled(True)

            self.metawidget.update()
            self.integratorTree.update()

        self.h5viewer.ui.listData.focusWidget()

    def next_arch(self):
        """Advances to next arch in data list, updates displayframe
        """
        if (self.arch == self.sphere.arches.iloc(-1).idx or
                self.arch is None or
                self.h5viewer.ui.listData.currentRow() == \
                self.h5viewer.ui.listData.count() - 1):
            self.displayframe.auto_last = True
            # pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.currentRow() + 1
            )
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)

    def prev_arch(self):
        """Goes back one arch in data list, updates displayframe
        """
        if (self.arch == self.sphere.arches.iloc(0).idx or
                self.arch.idx is None or
                self.h5viewer.ui.listData.currentRow() == 1):
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.currentRow() - 1
            )
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)

    def last_arch(self):
        """Advances to last arch in data list, updates displayframe, and
        set auto_last to True
        """
        if self.arch.idx is None:
            pass

        else:
            if self.arch.idx == self.sphere.arches.index[-1]:
                pass

            else:
                self.h5viewer.ui.listData.setCurrentRow(
                    self.h5viewer.ui.listData.count() - 1
                )

            self.displayframe.auto_last = True
            self.displayframe.ui.pushRightLast.setEnabled(False)

    def first_arch(self):
        """Goes to first arch in data list, updates displayframe
        """
        if self.arch == self.sphere.arches.iloc(0).idx or self.arch.idx is None:
            pass
        else:
            self.h5viewer.ui.listData.setCurrentRow(1)
            self.displayframe.auto_last = False
            self.displayframe.ui.pushRightLast.setEnabled(True)

    def close(self):
        """Tries a graceful close.
        """
        del self.sphere
        del self.displayframe.sphere
        del self.arch
        del self.displayframe.arch
        super().close()

    def enable_integration(self, enable=True):
        """Calls the integratorTree setEnabled function.
        """
        self.integratorTree.setEnabled(enable)

    def update_all(self):
        """Updates all data in displays
        TODO: Currently taking the most time for the main gui thread
        """
        self.h5viewer.update_data()
        if self.displayframe.auto_last:
            self.h5viewer.ui.listData.setCurrentRow(
                self.h5viewer.ui.listData.count() - 1
            )
        else:
            self.displayframe.update()
        self.metawidget.update()

        # self.h5viewer.ui.listData.setFocus()
        self.h5viewer.ui.listData.focusWidget()

    def integrator_thread_update(self, idx):
        self.thread_state_changed()
        if self.displayframe.auto_last:
            items = self.h5viewer.ui.listData.findItems(str(idx),
                                                        QtCore.Qt.MatchExactly)
            for item in items:
                self.h5viewer.ui.listData.setCurrentItem(item)
            self.displayframe.auto_last = True
        else:
            self.displayframe.update()

    def integrator_thread_finished(self):
        """Function connected to threadFinished signals for
        integratorThread
        """
        self.thread_state_changed()
        self.enable_integration(True)
        self.h5viewer.set_open_enabled(True)
        self.update_all()
        if not self.wrangler.thread.isRunning():
            self.ui.wranglerBox.setEnabled(True)
            self.wrangler.enabled(True)

    def new_scan(self, name, fname):
        """Connected to sigUpdateFile from wrangler. Called when a new
        scan is started.

        args:
            name: str, scan name
            fname: str, path to data file for scan
        """
        if self.sphere.name == name or self.sphere.name == 'null_main':
            self.h5viewer.dirname = os.path.dirname(fname)
            self.h5viewer.set_file(fname)
        self.h5viewer.update()

    def start_wrangler(self):
        """Sets up wrangler, ensures properly synced args, and starts
        the wrangler.thread main method.
        """
        self.ui.wranglerBox.setEnabled(False)
        self.wrangler.enabled(False)
        args = {'bai_1d_args': self.sphere.bai_1d_args,
                'bai_2d_args': self.sphere.bai_2d_args}
        self.wrangler.sphere_args = copy.deepcopy(args)
        self.wrangler.setup()
        self.wrangler.thread.start()

    def wrangler_finished(self):
        """Called by the wrangler finished signal. If current scan
        matches the wrangler scan, allows for integration.
        """
        self.thread_state_changed()
        if self.sphere.name == self.wrangler.scan_name:
            self.integrator_thread_finished()
        else:
            self.ui.wranglerBox.setEnabled(True)
            self.wrangler.enabled(True)

