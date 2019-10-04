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

from .ttheta_scan_anlzr import Analyzer
from .ttheta_scan_srvr import Server

from .ttheta_scan_config import (
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
        if os.path.isfile(data_file):
            start = time.time()
            while True:
                if time.time() - start > 5:
                    break
                try:
                    with h5py.File(data_file, 'r') as file:
                        arch_idx = max_string(file[scan_name]['arches'].keys())
                        arch = file[scan_name]['arches'][arch_idx]
                        arch_int_1d = arch['int_1d']
                        arch_int_norm = arch_int_1d['norm'][()]
                        tth = arch_int_1d['ttheta'][()]
                        map_norm = arch['map_norm'][()]
                        all_norm = file[scan_name]['bai_1d']['norm'][()]

                    ax1.clear()
                    ax2.clear()
                    ax1.imshow(map_norm.T)
                    plot_no_zero(ax2, tth, all_norm)
                    plot_no_zero(ax2, tth, arch_int_norm)
                    plt.tight_layout()
                    break
                except (KeyError, ValueError):
                    time.sleep(0.1)
                    pass
        else:
            map_norm = np.arange(100).reshape(10,10)
            tth = np.arange(100)
            all_norm = np.arange(100)
            arch_int_norm = np.arange(100)
            ax1.clear()
            ax2.clear()
            ax1.imshow(map_norm.T)
            plot_no_zero(ax2, tth, all_norm)
            plot_no_zero(ax2, tth, arch_int_norm)
            plt.tight_layout()
    ani = animation.FuncAnimation(fig, animate, interval=100)

    plt.show()
    proc_thread.join()
    red_thread.join()

    start = time.time()
    while True:
        if time.time() - start > 5:
            break
        try:
            with h5py.File(data_file, 'r') as file:
                arch_idx = max_string(file[scan_name]['arches'].keys())
                arch = file[scan_name]['arches'][arch_idx]
                arch_int_1d = arch['int_1d']
                arch_int_norm = arch_int_1d['norm'][()]
                tth = arch_int_1d['ttheta'][()]
                map_norm = arch['map_norm'][()]
                all_norm = file[scan_name]['bai_1d']['norm'][()]
            fig = plt.figure()
            ax1 = fig.add_subplot(2,1,1)
            ax2 = fig.add_subplot(2,1,2)
            ax1.imshow(map_norm.T)
            plot_no_zero(ax2, tth, all_norm)
            plot_no_zero(ax2, tth, arch_int_norm)
            plt.tight_layout()
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
        


