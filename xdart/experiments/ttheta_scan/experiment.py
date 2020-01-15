# python builtins
import os
import sys
from queue import Queue
from threading import Thread
import time
import multiprocessing as mp

# modules
from matplotlib import pyplot as plt
from matplotlib import animation
import h5py 
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore

from ...classes.spec import LoadSpecFile

# TODO: when deployed as plugin these should be deleted
if __name__ == '__main__':
    from analyzer import Analyzer
    from pre_processors import *
    from gui import visualizer as vis
    from gui import TThetaGUI

    # fs -> from spec in future
    from config import (
        user, # fs
        image_dir, # fs
        lsf_inputs, # fs
        mp_inputs,
        data_file, 
        sphere_args,
        spec_name
    )

else:
    from .analyzer import Analyzer
    from .pre_processors import *
    from .gui import visualizer as vis
    from .gui import TThetaGUI

    # fs -> from spec in future
    from .config import (
        user, # fs
        image_dir, # fs
        lsf_inputs, # fs
        mp_inputs,
        data_file, 
        sphere_args,
        spec_name
    )

PreProcessor = SpecPreProcessor

def visualize(data_file, scan_name):
    app = QtGui.QApplication([])
    win = TThetaGUI(data_file, scan_name)
    win.show()
    app.exec_()

def tth_scan(scan_number, data_points):
    """Main function for handling a scan. Currently operates on a scan
    by scan basis rather than communicating with spec. Called by the
    user triggering a scan with specific number of data points.
    """
    data_queue = mp.Queue() # produced by server, consumed by analyzer
    command_queue = mp.Queue() # produced by main, consumed by server
    scan_name = 'scan' + str(scan_number).zfill(2)

    sphere_args.update({'name': scan_name})

    preprocessor = PreProcessor(data_queue, command_queue, spec_name, user, image_dir, 
                    data_points, scan_number, lsf_inputs, mp_inputs)
    analyzer = Analyzer(data_queue, data_file, sphere_args)
    
    print("Launching processors")
    
    preproc_proc = mp.Process(target=preprocessor.run)
    analyzer_proc = mp.Process(target=analyzer.run)
    visualize_proc = mp.Process(target=visualize, args=(data_file, scan_name))
    
    print("Starting processors")
    preproc_proc.start()
    analyzer_proc.start()
    visualize_proc.start()
    #time.sleep(1)

    preproc_proc.join()
    analyzer_proc.join()
    visualize_proc.join()
    

def main():
    command = ""
    while True:
        command = input("Enter 'exit' or 'scan scan_number number_of_points'\n")
        if command == 'exit':
            break
        elif 'scan' in command:
            try:
                params = command.split()
                scan_number = int(params[1])
                data_points = int(params[2])
            except (IndexError, NameError, ValueError):
                print("Invalid Scan Command, form should be 'scan int int'")
                continue
            tth_scan(scan_number, data_points)
        else:
            print('Invalid command')

if __name__ == '__main__':
    main()

