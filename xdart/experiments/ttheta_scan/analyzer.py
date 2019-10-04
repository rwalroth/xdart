import h5py
from matplotlib import pyplot as plt 
import pandas as pd
from time import time

from paws.plugins.ewald import EwaldSphere, EwaldArch
from paws.containers import PONI
from paws.pawstools import catch_h5py_file

class Analyzer(object):
    def __init__(self, data_queue, data_file, sphere_args):
        self.data_q = data_queue
        self.plugin = EwaldSphere
        self.plugin_args = sphere_args
        self.data_file = data_file
    
    def run(self):
        sphere = self.plugin(**self.plugin_args)
        with catch_h5py_file(self.data_file, mode='a') as file:
            sphere.save_to_h5(file, replace=True)
        while True:
            start = time()
            flag, data = self.data_q.get()
            print(flag)
            if flag == 'TERMINATE' and data is None:
                with catch_h5py_file(self.data_file, mode='a') as file:
                    sphere.save_to_h5(file, replace=True)
                break
            elif flag == 'image':
                idx, map_raw, scan_info, poni = data
                print(f'fetching took {time() - start}')
                start = time()
                arch = EwaldArch(idx, map_raw, PONI.from_yamdict(poni), scan_info=scan_info)
                sphere.add_arch(
                    arch=arch.copy(), calculate=True, update=True, get_sd=True, 
                    set_mg=False
                )
                print(f'adding arch took {time() - start}')
                start = time()
                with catch_h5py_file(self.data_file, mode='a') as file:
                    sphere.save_to_h5(file, arches=[idx], data_only=True, replace=False)
                print(f'saving took {time() - start}')


