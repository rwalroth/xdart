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

# paws
from paws.operations.SPEC.LoadSpecFile import LoadSpecFile

from .analyzer import Analyzer
from .spec_server import Server
from . import visualizer as vis

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

def tth_scan(scan_number, data_points):
    """Main function for handling a scan. Currently operates on a scan
    by scan basis rather than communicating with spec. Called by the
    user triggering a scan with specific number of data points.
    """
    data_queue = mp.Queue() # produced by server, consumed by analyzer
    command_queue = mp.Queue() # produced by main, consumed by server
    scan_name = 'scan' + str(scan_number).zfill(2)
    sphere_args.update({'name': scan_name})

    server = Server(data_queue, command_queue, spec_name, user, image_dir, 
                    data_points, scan_number, lsf_inputs, mp_inputs)
    analyzer = Analyzer(data_queue, data_file, sphere_args)
    
    server_proc = mp.Process(target=server.run)
    analyzer_proc = mp.Process(target=analyzer.run)

    server_proc.start()
    analyzer_proc.start()
    #time.sleep(1)
    fig = plt.figure()
    ax1 = fig.add_subplot(2,1,1)
    ax2 = fig.add_subplot(2,1,2)

    def animate(i):
        """Needs to be defined per scan, updats the figure animation.
        Will be replaced by gui eventually.
        """
        vis.animation(data_file, scan_name, ax1, ax2)
    ani = animation.FuncAnimation(fig, animate, interval=100)

    plt.show()
    server_proc.join()
    analyzer_proc.join()

    # Animated figure not interactive, after closing a new figure is generated
    # that can be interacted with
    fig = plt.figure()
    ax1 = fig.add_subplot(2,1,1)
    ax2 = fig.add_subplot(2,1,2)

    start = time.time()
    while True:
        if time.time() - start > 5:
            break
        try:
            with h5py.File(data_file, 'r') as file:
                map_norm, tth, all_norm, arch_int_norm = vis.get_last_arch(file, scan_name)
            vis.update_fig(ax1, ax2, map_norm, tth, all_norm, arch_int_norm)
            break
        except (KeyError, ValueError):
            pass
    
    plt.show()
    

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

