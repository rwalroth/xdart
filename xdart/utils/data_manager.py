import threading
from queue import Queue
import time

import h5py


class DataManager:
    def __init__(self, data_path,):
        self.data_path = data_path
        self.created_objects = {}

    def create_object(self, cls, name, obj=None, signal=None):
        _name = name
        i = 0
        while _name in self.created_objects.keys():
            _name = name + "_" + str(int(time.time() % 10007 + i))
            i += 1
        else:
            _obj = obj

    def get_data(self, name, obj=None):
        pass

    def set_data(self, name, obj):
        pass