import threading
from queue import Queue
import time
from dataclasses import dataclass

import h5py


@dataclass
class DataStruct:
    path: str
    class_: type
    instance_: object = None

    def open(self, lazy=True):
        self.instance_ = self.class_()
        self.instance_.from_hdf5(self.path, lazy=lazy)
        return self.instance_

    def close(self):
        if self.instance_ is not None:
            self.instance_.to_hdf5(self.path)
            self.instance_.close()
            self.instance_ = None


class DataManager:
    def __init__(self, data_dir,):
        self.data_dir = data_dir
        self.created_objects = {}

    def create_object(self, cls, name, signal=None):
        _name = name
        i = 0
        while _name in self.created_objects.keys():
            _name = name + "_" + str(time.time()).split('.')[1] + str(i)
            i += 1
        else:
            _obj = obj