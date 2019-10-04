import os
import time

from matplotlib import pyplot as plt
import h5py
import numpy as np

def plot_no_zero(ax, x, y):
    ax.plot(x[y > 0], y[y > 0])

def max_string(lst):
    return str(max([eval(x) for x in lst]))

def animation(data_file, scan_name, ax1, ax2):
    if os.path.isfile(data_file):
        start = time.time()
        while True:
            if time.time() - start > 5:
                break
            try:
                with h5py.File(data_file, 'r') as file:
                    map_norm, tth, all_norm, arch_int_norm = get_last_arch(file, scan_name)

                update_fig(ax1, ax2, map_norm, tth, all_norm, arch_int_norm)
                break
            except (KeyError, ValueError):
                time.sleep(0.1)
                pass
    else:
        map_norm = np.arange(100).reshape(10,10)
        tth = np.arange(100)
        all_norm = np.arange(100)
        arch_int_norm = np.arange(100)
        update_fig(ax1, ax2, map_norm, tth, all_norm, arch_int_norm)

def get_last_arch(file, scan_name):
    arch_idx = max_string(file[scan_name]['arches'].keys())
    arch = file[scan_name]['arches'][arch_idx]
    arch_int_1d = arch['int_1d']
    arch_int_norm = arch_int_1d['norm'][()]
    tth = arch_int_1d['ttheta'][()]
    map_norm = arch['map_norm'][()]
    all_norm = file[scan_name]['bai_1d']['norm'][()]
    return map_norm, tth, all_norm, arch_int_norm


def update_fig(ax1, ax2, map_norm, tth, all_norm, arch_int_norm):
    ax1.clear()
    ax2.clear()
    ax1.imshow(map_norm.T)
    plot_no_zero(ax2, tth, all_norm)
    plot_no_zero(ax2, tth, arch_int_norm)
    plt.tight_layout()

