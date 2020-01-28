# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import copy
from queue import Queue
import multiprocessing as mp

# Other imports
from .....classes.ewald import EwaldSphere

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import Parameter

# This module imports
class wranglerWidget(Qt.QtWidgets.QWidget):
    sigStart = Qt.QtCore.Signal()
    sigUpdateData = Qt.QtCore.Signal(int)
    sigUpdateFile = Qt.QtCore.Signal(str)
    finished = Qt.QtCore.Signal()

    def __init__(self, fname, file_lock, parent=None):
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
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
    
    def enabled(self, enable):
        """Use this function to control what is enabled and disabled
        during integration.
        """
        pass

    def setup(self):
        self.thread = wranglerThread(self.command_queue, self.sphere_args, self.fname, self.file_lock, self)
    
    def set_fname(self, fname):
        self.fname = fname
        self.thread.fname = fname


class wranglerThread(Qt.QtCore.QThread):
    sigUpdate = Qt.QtCore.Signal(int)
    sigUpdateFile = Qt.QtCore.Signal(str)
    def __init__(self, command_queue, sphere_args, fname, file_lock, parent=None):
        super().__init__(parent)
        self.input_q = command_queue # thread queue
        self.sphere_args = sphere_args
        self.fname = fname
        self.file_lock = file_lock
        self.signal_q = mp.Queue()
        self.command_q = mp.Queue()
    
    def run(self):
        process = wranglerProcess(
            self.command_q, 
            self.signal_q, 
            self.sphere_args,
            self.fname,
            self.file_lock
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
    def __init__(self, command_q, signal_q, sphere_args, fname, file_lock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_q = command_q
        self.signal_q = signal_q
        self.sphere_args = sphere_args
        self.fname = fname
        self.file_lock = file_lock
    
    def run(self):
        sphere = EwaldSphere(**self.sphere_args)
        while True:
            if not self.command_q.empty():
                command = self.command_q.get()
                if command == 'stop':
                    break
