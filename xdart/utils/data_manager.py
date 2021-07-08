import threading
from queue import Queue
import time
from dataclasses import dataclass
import os

import h5py
from PyQt5.QtCore import QThread, pyqtSignal


@dataclass
class DataStruct:
    path: str
    class_: type
    instance_: object = None

    def open(self, lazy=True):
        self.instance_ = self.class_()
        self.instance_.load_from_hdf5(self.path, lazy=lazy)
        return self.instance_

    def close(self):
        if self.instance_ is not None:
            self.instance_.save_to_hdf5(self.path)
            self.instance_.close()
            self.instance_ = None


class DataManagerThread(QThread):
    objectReady = pyqtSignal(str)
    def __init__(self, taskQueue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.taskQueue = taskQueue

    def run(self):
        task = self.taskQueue.get()


class DataManager:
    def __init__(self, data_dir, lazy=False):
        self.data_dir = data_dir
        self.created_objects = {}
        self.taskQueue = Queue()
        self._worker = DataManagerThread(self.taskQueue)
        self._lazy = lazy

    def create_object(self, cls, name, slot=None):
        _name = name
        i = 0
        while _name in self.created_objects.keys():
            _name = name + "_" + str(time.time()).split('.')[1] + str(i)
            i += 1
        obj = cls()
        obj.data_file = os.path.join(self.data_dir, _name + ".hdf5")
        obj.save_to_hdf5(replace=True)
        obj.load_from_hdf5(lazy=self._lazy)
        self.created_objects[_name] = DataStruct(_name, cls, obj)
        return obj

    def load_object(self, name):


