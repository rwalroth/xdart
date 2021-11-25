# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
from queue import Queue
import multiprocessing as mp
import traceback

# Other imports

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.parametertree import Parameter

# This module imports
from xdart.modules.ewald import EwaldSphere


class wranglerWidget(Qt.QtWidgets.QWidget):
    """Base class for wranglers. Extending this ensures all methods,
    signals, and attributes expected by ttheta_widget are present.
    Threads should be started by use of sigStart.emit, which ensures
    tthetaWidget handles initiation.
    
    attributes:
        command_queue: Queue, used to send commands to thread
        file_lock, mp.Condition, process safe lock for file access
        fname: str, path to data file
        parameters: pyqtgraph Parameter, stores parameters from user
        scan_name: str, current scan name, used to handle syncing data
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        thread: wranglerThread or subclass, QThread for controlling
            processes
    
    methods:
        enabled: Enables or disables interactivity
        set_fname: Method to safely change file name
        setup: Syncs thread parameters prior to starting
    
    signals:
        finished: Should be connected to thread.finished signal
        sigStart: Tells tthetaWidget to start the thread and prepare
            for new data.
        sigUpdateData: int, signals a new arch has been added.
        sigUpdateFile: (str, str, bool, str, bool), sends new scan_name, file name
            GI flag (grazing incidence), theta motor for GI, and
             single_image flag to static_scan_Widget.
    """
    sigStart = Qt.QtCore.Signal()
    sigUpdateData = Qt.QtCore.Signal(int)
    # sigUpdateArch = Qt.QtCore.Signal(dict)
    sigUpdateFile = Qt.QtCore.Signal(str, str, bool, str, bool)
    sigUpdateGI = Qt.QtCore.Signal(bool)
    finished = Qt.QtCore.Signal()
    started = Qt.QtCore.Signal()

    def __init__(self, fname, file_lock, parent=None):
        """fname: str, file path
        file_lock: mp.Condition, process safe lock
        """
        #ic()
        super().__init__(parent)
        self.file_lock = file_lock
        self.fname = fname
        self.scan_name = 'null_thread'
        self.parameters = Parameter.create(
            name='wrangler_widget', type='int', value=0
        )
        self.sphere_args = {}

        self.command_queue = Queue()
        self.thread = wranglerThread(self.command_queue, self.sphere_args, self.fname, self.file_lock, self)
        self.thread.finished.connect(self.finished.emit)
        self.thread.started.connect(self.started.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        # self.thread.sigUpdateArch.connect(self.sigUpdateArch.emit)
        self.thread.sigUpdateGI.connect(self.sigUpdateGI.emit)

    def enabled(self, enable):
        """Use this function to control what is enabled and disabled
        during integration.
        """
        #ic()
        pass

    def setup(self):
        """Sets the thread child object. Called by tthetaWidget prior
        to starting thread.
        """
        #ic()
        self.thread = wranglerThread(self.command_queue, self.sphere_args, self.fname, self.file_lock, self)

    def set_fname(self, fname):
        """Changes fname attribute of self and thread.
        args:
            fname: str, path for new file.
        """
        #ic()
        with self.file_lock:
            if not self.thread.isRunning():
                self.fname = fname
                self.thread.fname = fname


class wranglerThread(Qt.QtCore.QThread):
    """Base class for wranglerThreads. Used to manage processes
    including data and command queues. Subclasses should override the
    run method.
    
    attributes:
        command_q: mp.Queue, queue to send commands to process
        file_lock: mp.Condition, process safe lock for file access
        fname: str, path to data file.
        input_q: mp.Queue, queue for commands sent from parent
        signal_q: mp.Queue, queue for commands sent from process
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
    
    methods:
        run: Called by start, main thread task.
    
    signals:
        sigUpdate: int, signals a new arch has been added.
        sigUpdateFile: (str, str, bool, str, bool), sends new scan_name, file name
            GI flag (grazing incidence), theta motor for GI, and
             single_image flag to static_scan_Widget.
        sigUpdateGI: bool, signals the grazing incidence condition has changed.
    """
    sigUpdate = Qt.QtCore.Signal(int)
    # sigUpdateArch = Qt.QtCore.Signal(dict)
    sigUpdateFile = Qt.QtCore.Signal(str, str, bool, str, bool)
    sigUpdateGI = Qt.QtCore.Signal(bool)

    def __init__(self, command_queue, sphere_args, fname, file_lock,
                 parent=None):
        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        file_lock: mp.Condition, process safe lock for file access
        """
        #ic()
        super().__init__(parent)
        self.input_q = command_queue # thread queue
        self.sphere_args = sphere_args
        self.fname = fname
        self.file_lock = file_lock
        self.signal_q = mp.Queue()
        self.command_q = mp.Queue()
    
    def run(self):
        """Main task. Should initialize child process here and listen
        to input and signal queues.
        """
        #ic()
        process = wranglerProcess(
            self.command_q, 
            self.signal_q, 
            self.sphere_args,
            self.fname,
            self.file_lock,
        )
        process.start()
        while True:
            if not self.input_q.empty():
                command = self.input_q.get()
                if command == 'stop':
                    self.command_q.put('stop')
                    break
        process.join()


class wranglerProcess(mp.Process):
    """Base class for wrangler processes. Subclasses should extend
    _main, NOT run. _main is run in a try except clause which ensures
    errors are printed.
    
    attributes:
        command_q: mp.Queue, queue for commands from parent thread.
        file_lock: mp.Condition, process safe lock for file access
        fname: str, path to data file
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
    
    methods:
        _main: method to be overridden in subclasses.
        run: called by start, overriding this function should take into
            account proper error handling.
    """
    def __init__(self, command_q, signal_q, sphere_args, fname, file_lock,
                 *args, **kwargs):
        """command_q: mp.Queue, queue for commands from parent thread.
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file
        file_lock: mp.Condition, process safe lock for file access
        """
        #ic()
        super().__init__(*args, **kwargs)
        self.command_q = command_q
        self.signal_q = signal_q
        self.sphere_args = sphere_args
        self.fname = fname
        self.file_lock = file_lock

    def run(self):
        """Target of process, calls _main inside a try except clause to
        handle errors.
        """
        #ic()
        try:
            self._main()
        except:
            print("-"*60)
            traceback.print_exc()
            print("-"*60)

    def _main(self):
        """Treated like overriding run in a normal multiprocess Process.
        """
        #ic()
        sphere = EwaldSphere(data_file=self.fname,
                             # keep_in_memory=True,
                             static=True,
                             **self.sphere_args)
        while True:
            if not self.command_q.empty():
                command = self.command_q.get()
                if command == 'stop':
                    break
