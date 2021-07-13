import threading
from queue import Queue
import time
from dataclasses import dataclass
import os
from threading import RLock

import h5py
from PyQt5.QtCore import QThread, pyqtSignal


def _get_unique_name(name, data):
    _name = name
    i = 0
    while _name in data.keys():
        _name = name + "_" + str(time.time()).split('.')[1] + str(i)
        i += 1
    return _name


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
    objectReady = pyqtSignal(object)
    def __init__(self, taskQueue, dataLock, lazy, data_dir, created_objects,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.taskQueue = taskQueue
        self.dataLock = dataLock
        self._lazy = lazy
        self.data_dir = data_dir
        self.created_objects = created_objects

    def run(self):
        while True:
            task, args = self.taskQueue.get()
            if task == "load":
                self._load_object(*args)
            elif task == "save":
                self._save_object(*args)
            elif task == "register":
                self._register_object(*args)

    def _load_object(self, name, obj, slot, kwargs):
        _obj = None
        if obj is not None:
            _obj = obj
            _obj.load_from_hdf5(lazy=self._lazy, **kwargs)
        elif name is not None:
            try:
                data: DataStruct = self.created_objects[name]
                if data.instance_ is None:
                    data.open(self._lazy)
                _obj = data.instance_

            except KeyError:
                print(f"{name} not found")

        if slot is not None:
            self._emit_object(_obj, slot)

    def _save_object(self, obj, slot, kwargs):
        obj.save_to_hdf5(**kwargs)
        if slot is not None:
            self._emit_object(obj, slot)

    def _emit_object(self, obj, slot):
        try:
            self.objectReady.disconnect()
        except TypeError:
            pass
        self.objectReady.connect(slot)
        self.objectReady.emit(obj)
        self.objectReady.disconnect()

    def _get_unique_name(self, name):
        return _get_unique_name(name, self.created_objects)

    def _register_object(self, obj, name, slot):
        _name = self._get_unique_name(name)
        obj._name = name
        _path = os.path.join(self.data_dir, _name + ".hdf5")
        obj.set_datafile(_path, copy=True, lazy=self._lazy)
        with self.dataLock:
            self.created_objects[_name] = DataStruct(
                os.path.join(self.data_dir, _name + ".hdf5"),
                type(obj),
                obj
            )
        if slot is not None:
            self._emit_object(obj, slot)


class DataManager:
    def __init__(self, data_dir, lazy=False, *args, **kwargs):
        self.dataLock = RLock()
        self.data_dir = data_dir
        self.created_objects = {}
        self.taskQueue = Queue()
        self._worker = DataManagerThread(self.taskQueue, self.dataLock, lazy,
                                         self.data_dir, *args, **kwargs)
        self._lazy = lazy

    def create(self, cls, name):
        _name = _get_unique_name(name, self.created_objects)
        obj = cls()
        obj.set_datafile(os.path.join(self.data_dir, _name + ".hdf5"), lazy=self._lazy)
        obj._name = _name
        with self.dataLock:
            self.created_objects[_name] = DataStruct(
                os.path.join(self.data_dir, _name + ".hdf5"),
                cls,
                obj
            )
        return obj

    def load(self, name=None, obj=None, slot=None, **kwargs):
        self.taskQueue.put(("load", (name, slot, obj, kwargs)))

    def save(self, obj, slot=None, **kwargs):
        self.taskQueue.put(("save", (obj, slot, kwargs)))

    def register(self, obj, name, slot=None):
        self.taskQueue.put(("register", (obj, name, slot)))

