import h5py
from matplotlib import pyplot as plt 
import pandas as pd
from time import time

from ...classes.ewald import EwaldSphere, EwaldArch
from ...containers import PONI
from ...utils import catch_h5py_file

class Analyzer(object):
    """Process that takes in data for use in pyFAI integrators, using
    data objects from the paws library. Can be interfaced with different
    servers as long as they provide expected data types.
    """
    def __init__(self, data_queue, data_file, sphere_args):
        self.data_q = data_queue
        self.plugin = EwaldSphere
        self.plugin_args = sphere_args
        self.data_file = data_file
    
    def run(self):
        print("Analyzer called")
        # Plugin instantiated within process to avoid conflicts with locks
        sphere = self.plugin(**self.plugin_args)

        # Clears any scan data present in file
        with catch_h5py_file(self.data_file, mode='a') as file:
            sphere.save_to_h5(file, replace=True)

        # Main loop for analysis
        while True:
            flag, data = self.data_q.get()
            print(flag)
            if flag == 'TERMINATE' and data is None:
                # Terminate not only for errors, also signals end of scan.
                # All data is saved at the end.
                with catch_h5py_file(self.data_file, mode='a') as file:
                    sphere.save_to_h5(file, replace=True)
                break
            elif flag == 'image':
                # data point number, raw image numpy array, motor and detector
                # values, poni dictionary
                idx, map_raw, scan_info, poni = data
                arch = EwaldArch(
                    idx, map_raw, PONI.from_yamdict(poni), scan_info=scan_info
                )
                sphere.add_arch(
                    arch=arch.copy(), calculate=True, update=True, get_sd=True, 
                    set_mg=False
                )
                with catch_h5py_file(self.data_file, mode='a') as file:
                    sphere.save_to_h5(
                        file, arches=[idx], data_only=True, replace=False
                    )
                
                print(f"arch {idx} added to sphere")


