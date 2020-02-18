# -*- coding: utf-8 -*-
"""
@author: thampy
"""

# Standard library imports
import sys, os, glob, imp, fnmatch, re, time

# Other Imports
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import numpy as np
import scipy

from collections import OrderedDict
from copy import deepcopy

from joblib import Parallel, delayed
import multiprocessing as mp

# This module imports
from lmfit import Model, Parameters
from lmfit.models import LinearModel, GaussianModel, PseudoVoigtModel

import pyFAI
from pyFAI.multi_geometry import MultiGeometry
from silx.io.specfile import SpecFile

sys.path.append('/Users/v/Research/RDA/repos/xdart/')
from xdart.utils import get_from_pdi, query_yes_no, read_image_file, smooth_img, get_fit, fit_images_2D
from xdart.pySSRL_bServer.bServer_funcs import specCommand, wait_until_SPECfinished


def check_ready():
    # Check if detector is ready for direct beam scan

    ready = query_yes_no('Are filters in? Can detector take direct beam?')

    if ready != 'yes':
        print('Cannot proceed with direct beam scan..')
        sys.exit()
    
    
def create_SPEC_file(path):
    # Create new calibration spec file with date time stamp

    timestr = time.strftime("%Y%m%d-%H%M%S")
    calibScan = f'calib_{timestr}'

    print(f'Creating new SPEC file {calibScan} for calibration scan in {path}..')
    command = f'newfile {path}/{calibScan}'
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()    
        
    return calibScan
        
        
def set_PD_savepath(img_path):
    # Change PD Savepath

    print(f'Changing PD SavePath to {img_path}')
    command = f'pd savepath {img_path}'
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()
        
        
def run_direct_beam_scan():
    # Run Direct Beam Scan

    command = f'ascan  tth -4 4  400 1'
    print(f'Running direct beam scan [{command}]')
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()
        
    # Wait till Scan is finished to continue
    wait_until_SPECfinished(polling_time=5)
    time.sleep(5)


def read_SPEC_file(spec_path):
    spec_file = SpecFile( os.path.join(spec_path, {calibScan}) )
    
    return spec_file


def get_img_fnames(img_path, calibScan):
    # Read Spec File and get Image and PDI File Names

    img_path = os.path.join(path, 'images')
    pdi_path = img_path

    img_fnames = sorted(fnmatch.filter(os.listdir(img_path), f'*{calibScan}*.raw'))
    pdi_fnames = [f'{img_fname}.pdi' for img_fname in img_fnames
                if os.path.exists( os.path.join(pdi_path, f'{img_fname}.pdi') )]

    if len(pdi_fnames) != len(img_fnames):
        print('PDI files for all images not present..')
        
    return img_fnames, pdi_fnames
        
           

def get_TTh_w_direct_beam(img_path, img_fnames, pdi_path, pdi_fnames):
    # Get Range of TTh Values that see Direct Beam
    img_mean_vals = [ np.mean(read_image_file( os.path.join(img_path, img_fname),
                                              return_float=True ))
                     for img_fname in img_fnames]
    median_mean_vals = np.median( np.asarray(img_mean_vals) )

    TThs = OrderedDict()
    for (img_fname, pdi_fname) in zip(img_fnames, pdi_fnames):
        img = read_image_file( os.path.join(img_path, img_fname), return_float=True )
        if np.mean(img) > median_mean_vals/2.:
            tth = get_motor_val( os.path.join(pdi_path, pdi_fname), 'TwoTheta' )
            TThs[img_fname] = tth


    # Limit to TThs that have both positive and negative values
    while True:
        keys = list(TThs.keys())
        tths = np.asarray([tth for k, tth in TThs.items()])

        if abs(tths[0]) == abs(tths[-1]):
            break

        if np.abs(tths[0]) > tths[-1]:
            del TThs[keys[0]]
        else:
            del TThs[keys[-1]]

    n0 = len(tths)//2
    keys = keys[:20] + keys[n0-20 : n0+20] + keys[-20:]
    TThs = OrderedDict({k:TThs[k] for k in keys})
    return TThs

  
def fit_all_images(img_path, img_fnames, tths, n_cores=None):
    if n_cores is None:
        n_cores = mp.cpu_count()
        
    fit_results = Parallel(n_jobs=n_cores) (
        delayed(fit_images_2D)(os.path.join(img_path, fname), tth, function='pvoigt',
                               kernel_size=3, window_size=1,
                               verbose='True', orientation='vertical', flip=False)
        for (fname, tth) in zip(img_fnames[::], tths[::]) )


    Fit_Results = OrderedDict ( { tth:fit_result for (tth, fit_result) in fit_results } )

    tths = np.asarray( list(Fit_Results.keys()) )
    xs = np.asarray( [Fit_Results[tth].params['center_x'] for tth in tths] )
    ys = np.asarray( [Fit_Results[tth].params['center_y'] for tth in tths] )
    
    return tths, xs, ys

          
def get_db_pixel(tths, xs, ys):
    # Get direct beam pixel at TTh = 0 degrees

    n0 = len(tths)//2
    s_ = np.s_[n0-20:n0+20]

    xs, ys, tths = xs[s_], ys[s_], tths[s_]

    mod_xs = LinearModel()
    params_xs = mod_xs.guess(xs, x=tths)
    fit_xs = mod_xs.fit(xs, params=params_xs, x=tths)
    fit_xs = mod_xs.fit(xs, params=fit_xs.params, x=tths)
    xs_fit_val = fit_xs.eval(params=fit_xs.params, xdata=tths)

    mod_ys = LinearModel()
    params_ys = mod_ys.guess(ys, x=tths)
    fit_ys = mod_ys.fit(ys, params=params_ys, x=tths)
    fit_ys = mod_ys.fit(ys, params=fit_ys.params, x=tths)
    ys_fit_val = fit_ys.eval(params=fit_ys.params, xdata=tths)
    
    x0 = fit_xs.eval(params=fit_xs.params, x=0.0)
    y0 = fit_ys.eval(params=fit_ys.params, x=0.0)

    return x0, y0
          
          
def get_poni_params(tths, xs, ys, x0, y0, pixel_sz=0.000172):
    xs = np.round(xs, 2)
    ys = np.round(ys, 2)
    
    n0 = len(tths)//2; tth0 = tths[n0]

    xys = []
    ds, Ds, alphas, rot3s, all_tths = [], [], [], [], []
    for ii in range(0, n0):
        idx1, idx2 = ii, -ii-1
        tth1, tth2 = tths[idx1], tths[idx2]
        
        if abs(tth1) < 3:
            continue

        if tth1 != -tth2:
            print(f'tth1 ({tth1}) != -tth2 ({tth2})')
            break
            
        x1, x2 = xs[idx1], xs[idx2]
        y1, y2 = ys[idx1], ys[idx2]

        xys.append(np.asarray([x1, y1, x2, y2]))

        d1 = np.sqrt( (x1 - x0)**2 + (y1 - y0)**2 ) * pixel_sz
        d2 = np.sqrt( (x2 - x0)**2 + (y2 - y0)**2 ) * pixel_sz

        ds.append(np.asarray([d1, d2]))

        tth = np.deg2rad (abs(tth1))

        D = 2 * d1 * d2 * (d1 + d2) * np.tan(tth) / (
            (d1 + d2)**2 * np.tan(tth)**2  + (d1 - d2)**2 )

        alpha = - np.arctan( 1/np.tan(tth) * (d1 - d2) / (d1 + d2) )
        rot3 = - (x1 - x2) / (y1 - y2)

        Ds.append(D)
        alphas.append(alpha)
        rot3s.append(rot3)
        all_tths.append( np.rad2deg(tth) )

    D = np.mean(Ds[:-1])
    rot2 = np.mean(alphas[:-1])
    rot3 = np.mean(rot3s[:-1])

    poni1 = y0 * pixel_sz - D*np.tan(rot2)*np.cos(rot3)
    poni2 = x0 * pixel_sz + D*np.tan(rot2)*np.sin(rot3)
    #poni1 = (485-y0) * pixel_sz + D*np.tan(rot2)*np.cos(rot3)# + 0.005

    poni_params = OrderedDict(dist=D, rot2=rot2, rot3=rot3, poni1=poni1, poni2=poni2)
    print(poni_params)
    
    return poni_params
 
 
def make_poni(poni_file, spec_file, params, detector="Pilatus100k"):
    energy = spec_file.motor_position_by_name(0, 'Monochrom')
    wavelength = 12398/energy * 1e-10
    print(f'Energy: {energy}, Wavelength: {wavelength}')

    poni_params = dict(
        detector = detector,
        wavelength = wavelength,
        **params
    )

    ai = pyFAI.azimuthalIntegrator.AzimuthalIntegrator(**poni_params)
    ai.save(os.path.join(poni_path, f'{calibScan}.poni'))
    print(ai)
    
          
if __name__ == '__main__':
    detector = 'Pilatus100K'
    pixel_sz = 0.000172
    
    # Paths
    remote_path = '~/data/calibration'
    local_path = 'P:\\Data'
    poni_path = 'P:'
    
    # Remote (SPEC) Computer Paths
    path = remote_path
    
    spec_path = path
    img_path = os.path.join(path, 'images')
    pdi_path = img_path

    # Initialize and set paths
    check_ready()
    calibScan = create_calib_file(local_path)
    set_PD_savepath(local_path)
    
    # Run direct beam scan
    run_direct_beam_scan()
    
    # ********************** Now moving to local computer ***************************
    
    # Set local paths
    path = local_path

    spec_path = path
    img_path = os.path.join(path, 'images')
    pdi_path = img_path

    # Read SPEC File and Images from Remote (Windows) Path
    spec_file = read_SPEC_file(spec_path)
    img_fnames, pdi_fnames = get_img_fnames(img_path, calibScan)
    
    # Get Range of TTh Values that see Direct Beam
    print('Getting all images that see direct beam')
    TThs = get_TTh_w_direct_beam(img_path, img_fnames, pdi_path, pdi_fnames)

    # Restrict Image Names to above
    img_fnames = list(TThs.keys())
    pdi_fnames = [f'{img_fname}.pdi' for img_fname in img_fnames]
    tths = np.asarray([tth for k, tth in TThs.items()])
    print(f'TTh range for direct beam: [{tths[0]}, {tths[-1]}]\n')

    # Fit all Images
    print('Fitting 2D PVoigt to all images..')
    tths, xs, ys =  fit_all_images(img_path, img_fnames, tths)
    print('Done \n')

    # Get Direct Beam Pixel
    print('Obtaining direct beam pixel at TTh=0')
    x0, y0 = get_db_pixel(tths, xs, ys)
    print(f'Direct beam pixel at TTh=0: [{x0:.2f}, {y0:.2f}]\n')
    
    # Obtain Poni Parameters
    print('Calculating PONI File parameters (dist, rot2, rot3, poni1, poni2)')
    poni_params = get_poni_params(tths, xs, ys, x0, y0, pixel_sz=pixel_sz)
    
    # Create and save PONI file
    poni_file = os.path.join(poni_path, f'{calibScan}.poni')
    print(f'Making and saving {poni_file}')
    make_poni(poni_file, spec_file, poni_params, detector=detector)
    
    
    
    