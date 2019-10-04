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
from .server import Server
from . import visualizer as vis

from .config import (
    user, 
    image_dir,  
    lsf_inputs, 
    mp_inputs,  
    data_file, 
    sphere_args,
    spec_name
)

def max_string(lst):
    return str(max([eval(x) for x in lst]))

def plot_no_zero(ax, x, y):
    ax.plot(x[y > 0], y[y > 0])

def tth_scan(scan_number, data_points):
    data_queue = mp.Queue()
    command_queue = mp.Queue()
    scan_name = 'scan' + str(scan_number).zfill(2)
    sphere_args.update({'name': scan_name})

    proc = Server(data_queue, command_queue, spec_name, user, image_dir, 
                    data_points, scan_number, lsf_inputs, mp_inputs)
    red = Analyzer(data_queue, data_file, sphere_args)
    
    proc_thread = mp.Process(target=proc.run)
    red_thread = mp.Process(target=red.run)

    proc_thread.start()
    red_thread.start()
    #time.sleep(1)
    fig = plt.figure()
    ax1 = fig.add_subplot(2,1,1)
    ax2 = fig.add_subplot(2,1,2)

    def animate(i):
        vis.animation(data_file, scan_name, ax1, ax2)
    ani = animation.FuncAnimation(fig, animate, interval=100)

    plt.show()
    proc_thread.join()
    red_thread.join()

    start = time.time()
    
    fig = plt.figure()
    ax1 = fig.add_subplot(2,1,1)
    ax2 = fig.add_subplot(2,1,2)
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
        


