# -*- coding: utf-8 -*-
"""
@author: thampy
"""

# Standard library imports
import sys, os, fnmatch, time

# Other Imports
import numpy as np

from collections import OrderedDict
from joblib import Parallel, delayed
import multiprocessing as mp

# This module imports
from lmfit.models import LinearModel

import pyFAI
from silx.io.specfile import SpecFile

xdart_dir = os.getcwd().split('xdart')[0] + 'xdart'
if __name__ == '__main__':
    if xdart_dir not in sys.path:
        sys.path.append(xdart_dir)
    
from xdart.utils import get_motor_val, query, query_yes_no
from xdart.utils import get_img_data, fit_images_2D
from xdart.modules.pySSRL_bServer.bServer_funcs import specCommand, wait_until_SPECfinished, get_console_output


def get_detector_config():
    """Gets the configuration of the detector

    Returns:
        detector_name -- Pilatus100K, 300K etc.
        pixel_sz -- pixel size in meters
        ccd_shape -- number of pixels along both directions
        orientation -- vertical/horizontal
        init_dist -- calls function get_initial_distance to esimate the rough sample detector distance
    """
    
    detector_name = get_detector_name()
    detector = pyFAI.detector_factory(detector_name)

    pixel_sz = detector.pixel1
    ccd_shape = detector.max_shape

    orientation = get_detector_orientation()
    init_dist = get_initial_distance()
    
    return detector_name, pixel_sz, ccd_shape, orientation, init_dist


def check_recalibrate():
    """Check if user wants to recalibrate"""

    calibScan = query('Enter scan name to recalibrate with existing scan. Else press enter for new calibration: ')
    return calibScan
    

def check_ready():
    """Check if detector is ready for direct beam scan"""

    ready = query_yes_no('\nAre filters in? Can detector take direct beam?')

    if ready != 'yes':
        print('Cannot proceed with direct beam scan..')
        sys.exit()
    

def get_current_state():
    """Save current pd_savepath, specfilename, and scan number to
    restore the current state after callibration
    
    Returns:
        pd_savepath -- Current PD Savepath
        filename -- Current SPEC filename
        scan_n -- Current SPEC scan number
    """
    
    print('Saving current state..\n')
    
    command = "print PD_SAVEPATH ' ' DATAFILE  ' ' SCAN_N"
    specCommand(command, queue=True)
    wait_until_SPECfinished()
    
    while 1:
        try:
            out = get_console_output(idx=1)[0]
            break
        except:
            pass
        
    pd_savepath, filename, scan_n = out.split(' ')
    return pd_savepath, filename, scan_n


def restore_state(saved_state):
    """Restore saved pd_savepath, specfilename, and scan number
    
    args:
        saved_state: Tuple containing pd_savepath, specfilename and scan number
    """
    
    pd_savepath, filename, scan_n = saved_state
    
    command = f'pd savepath {pd_savepath}; newfile_f("{filename}", {scan_n})'
    specCommand(command, queue=True)
    
    print('Saved state restored\n')
    
    
def get_detector_name():
    """Get detector type from User"""
    
    detectors_dict = {'1': 'Pilatus100K',
                      '2': 'Pilatus300K',
                      '3': 'Eiger1M',
                      '' : 'Pilatus100K'}

    while 1:
        det_number = query('Choose detector (1-3) [1] Pilatus100K (2) Pilatus300K (3) Eiger1M: ')
        try:
            detector = detectors_dict[det_number]
            print(f'Selected {detector}\n')
            return detector
        except:
            print('Choice must be a number from (1 - 3)')


def get_detector_orientation():
    """Get detector orientation from User"""
    
    orientations = {'v': 'vertical',
                    'h': 'horizontal',
                    '' : 'vertical'}

    while 1:
        orientation = query('Detector orientation ( Vertical [default] / Horizontal) [v/h]: ').lower()
        if orientation in ['h', 'v', '']:
            orientation = orientations[orientation]
            print(f'Selected orientation {orientation}\n')
            return orientation
        else:
            print('Please choose (v/h) or hit enter for default [v]: ')


def get_initial_distance(default=0.7):
    """Get rough initial sample detector distance from User"""
    
    while 1:
        init_dist = query(f'Enter rough detector sample distance in meters [default {default}]:')
        if len(init_dist) == 0:
            print(f'Using default value: {default}\n')
            return default
        try:
            init_dist = float(init_dist)
            return init_dist
        except:
            print('Please enter a numeric value')


def create_remote_paths(scan_path, img_path):
    """Create folders on SPEC machine to store calibration scan and images if they don't exist"""
    
    command = f'u mkdir {scan_path}'
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()    

    # Create images folder on SPEC machine if it doesn't exist
    command = f'u mkdir {img_path}'
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()    


def create_SPEC_file(path):
    """Create new calibration spec file with date time stamp"""
    
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
    """Change PD Savepath to img_path
    
    args:
        img_path: New PD savepath
    """

    print(f'Changing PD SavePath to {img_path}')
    command = f'pd savepath {img_path}'
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()
        

def get_tth_scan_range(init_dist=0.7, pixel_sz=0.000172, ccd_shape=(195,487), orientation='vertical'):
    """Estimate the range for 2th scan for calibration

    Keyword Arguments:
        init_dist {float} -- Estimate of sample detector distance (default: {0.7})
        pixel_sz {float} -- Pixel size in meters (default: {0.000172})
        ccd_shape {tuple} -- Detector size in pixels (default: {(195,487)})
        orientation {str} -- detector orientation (vertical/horizontal) (default: {'vertical'})

    Returns:
        tuple -- 2th range, number of steps (step size is 0.02 degrees)
    """
    if orientation == 'vertical':
        ccd_shape = (487, 195)

    tth = np.round(np.rad2deg( np.arctan(pixel_sz*ccd_shape[0]/2 / init_dist) ) + 0.2, 1)
    steps = len(np.arange(-tth, tth, 0.02))

    return tth, steps


def run_direct_beam_scan(tth, steps):
    """Function to run direct beam scan to calibrate

    Arguments:
        tth {float} -- maximum 2th value to scan. Scan is performed from -tth to +tth
        steps {int} -- number of steps
    """
    command = f'ascan  tth -{tth} {tth} {steps} 1'
    print(f'Running direct beam scan [{command}]')
    try:
        specCommand(command, queue=True)
    except Exception as e:
        print(e)
        print(f"Command '{command}' not sent")
        sys.exit()
        
    # Wait till Scan is finished to continue
    print('Waiting for scan to finish..')
    wait_until_SPECfinished(polling_time=5)
    time.sleep(5)
    print('Done', '\n')


def read_SPEC_file(scan_path, calibScan):
    """Read SPEC file into an object

    Arguments:
        scan_path {path} -- path where SPEC file is stored
        calibScan {str} -- Calibration file name

    Returns:
        SpecFile object -- SpecFile Object as per SILX
    """
    spec_file = SpecFile( os.path.join(scan_path, f'{calibScan}') )
    
    return spec_file


def get_img_fnames(img_path, pdi_path, calibScan):
    """Get filenames of image files used for direct beam calibration

    Arguments:
        img_path {path} -- Directory where images are stored
        pdi_path {path} -- Directory where the associated PDI files are stored
        calibScan {string} -- Name of calibration scan

    Returns:
        tuple -- Image and PDI file names
    """

    img_fnames = sorted(fnmatch.filter(os.listdir(img_path), f'*{calibScan}*.raw'))
    pdi_fnames = [f'{img_fname}.pdi' for img_fname in img_fnames
                if os.path.exists( os.path.join(pdi_path, f'{img_fname}.pdi') )]

    if len(pdi_fnames) != len(img_fnames):
        print('PDI files for all images not present..')
        
    return img_fnames, pdi_fnames
        
           
def get_TTh_w_direct_beam(img_path, img_fnames, pdi_path, pdi_fnames):
    """Get range of TTh Values that see Direct Beam

    Arguments:
        img_path {path} -- Path for image files
        img_fnames {[str]} -- image file names
        pdi_path {path} -- Path for PDI files
        pdi_fnames {[str]} -- PDI file names

    Returns:
        tuple -- 2th values, image and PDI filenames of points that see direct beam
    """
    # Get Range of TTh Values that see Direct Beam
    img_mean_vals = [ np.mean(get_img_data( os.path.join(img_path, img_fname),
                                              return_float=True ))
                     for img_fname in img_fnames]
    median_mean_vals = np.median( np.asarray(img_mean_vals) )

    for (idx, img_fname) in enumerate(img_fnames):
        img = get_img_data( os.path.join(img_path, img_fname), return_float=True )
        if np.mean(img) > median_mean_vals/2.:
            break
    if idx > 0:
        img_fnames = img_fnames[idx:-idx]
    
    for (idx, img_fname) in enumerate(img_fnames[::-1]):
        img = get_img_data( os.path.join(img_path, img_fname), return_float=True )
        if np.mean(img) > median_mean_vals/2.:
            break
    if idx > 0:
        img_fnames = img_fnames[idx:-idx]
    
    n0 = len(img_fnames)//2
    img_fnames = img_fnames[:20] + img_fnames[n0-20 : n0+21] + img_fnames[-20:]
    
    pdi_fnames = [f'{img_fname}.pdi' for img_fname in img_fnames]
    tths = [get_motor_val( os.path.join(pdi_path, pdi_fname), 'TwoTheta' )
            for pdi_fname in pdi_fnames]
    
    return img_fnames, pdi_fnames, tths

      
def fit_all_images(img_path, img_fnames, tths, n_cores=None):
    """Perform 2D pvoigt function fits to all images to get the pixel position of the direct beam 

    Arguments:
        img_path {path} -- image file path
        img_fnames {[str]} -- image file names
        tths {[float]} -- 2th values for each image

    Keyword Arguments:
        n_cores {int} -- Number of cores to use for parallel processing (default: {None})

    Returns:
        tuple -- the direct beam pixel coordinates for each tth value and the tth values
    """
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
    """Get direct beam pixel at TTH = 0 degrees. This is done by taking a 
    total of 40 images around TTH = 0, finding the direct beam pixel for each of them
    and fitting these positions to a line to get the direct beam pixel position at TTH = 0

    Arguments:
        tths {[float]} -- array of 2th values
        xs {[float]} -- array of the x positions of the direct beam pixel
        ys {[float]} -- array of the y positions of the direct beam pixel

    Returns:
        tuple -- x0, y0 (direct beam pixel position at 2th = 0)
    """

    n0 = len(tths)//2
    s_ = np.s_[n0-20:n0+20]

    xs, ys, tths = xs[s_], ys[s_], tths[s_]

    mod_xs = LinearModel()
    params_xs = mod_xs.guess(xs, x=tths)
    fit_xs = mod_xs.fit(xs, params=params_xs, x=tths)
    fit_xs = mod_xs.fit(xs, params=fit_xs.params, x=tths)

    mod_ys = LinearModel()
    params_ys = mod_ys.guess(ys, x=tths)
    fit_ys = mod_ys.fit(ys, params=params_ys, x=tths)
    fit_ys = mod_ys.fit(ys, params=fit_ys.params, x=tths)
    
    x0 = fit_xs.eval(params=fit_xs.params, x=0.0)
    y0 = fit_ys.eval(params=fit_ys.params, x=0.0)

    return x0, y0
          
          
def get_poni_params(tths, xs, ys, x0, y0, pixel_sz=0.000172):
    """Calculate PONI file parameters from the direct beam pixel values over the 2th scan

    Arguments:
        tths {[float]} -- 2th values for the scan
        xs {[float]} -- pixel positions along X for the points of the scan
        ys {[float]} -- pixel positions along Y for the points of the scan
        x0 {float} -- pixel positions along X for direct beam at 2th=0
        y0 {float} -- pixel positions along Y for direct beam at 2th=0

    Keyword Arguments:
        pixel_sz {float} -- Pixel size (default: {0.000172})

    Returns:
        dictionary -- dictionary containing poni file parameters
    """
    xs = np.round(xs, 2)
    ys = np.round(ys, 2)
    
    n0 = len(tths)//2; tth0 = tths[n0]

    xys = []
    ds, Ds, alphas, rot3s, all_tths = [], [], [], [], []
    for ii in range(0, n0):
        idx1, idx2 = ii, -ii-1
        tth1, tth2 = tths[idx1], tths[idx2]
        
        if abs(tth1) < 2.8:
            break

        if tth1 != -tth2:
            print(f'tth1 ({tth1}) != -tth2 ({tth2})')
            continue
            
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
    """Create poni file from poni file parameters

    Arguments:
        poni_file {str} -- poni file name
        spec_file {SpecFile Object} -- SpecFile object that contains information form the SPEC file
        params {dictionary} -- Poni file paramter dictionary

    Keyword Arguments:
        detector {str} -- Detector type (default: {"Pilatus100k"})
    """
    energy = spec_file.motor_position_by_name(0, 'Monochrom')
    wavelength = 12398/energy * 1e-10
    print(f'Energy: {energy}, Wavelength: {wavelength}')

    poni_params = dict(
        detector = detector,
        wavelength = wavelength,
        **params)

    ai = pyFAI.azimuthalIntegrator.AzimuthalIntegrator(**poni_params)
    ai.save(poni_file)
    print(ai)
    

def run_calibration(remote_path, local_path, poni_path, public_poni_path):
    """Main function to perform calibration

    Arguments:
        remote_path {str} -- path on remote computer (SPEC)
        local_path {str} -- path on local computer (Windows)
        poni_path {str} -- path to store poni file 
        public_poni_path {str} -- path to store poni file for global access
    """

    # Remote (SPEC) Computer Paths
    remote_scan_path = f'{remote_path}/scans'
    remote_img_path  = f'{remote_path}/images'

    # Local (Windows) paths
    scan_path = os.path.join(local_path, 'scans')
    img_path  = os.path.join(local_path, 'images')
    pdi_path  = img_path

    # Make Directories if they don't exist
    print("Creating folders if they don't exist")
    os.makedirs(scan_path, exist_ok=True)
    os.makedirs(img_path, exist_ok=True)
    os.makedirs(poni_path, exist_ok=True)
    
    # Set initial detector configuration
    detector, pixel_sz, ccd_shape, orientation, init_dist = get_detector_config()
    
    # Check if user wants to recalibrate with existing scan
    calibScan = check_recalibrate()
    if calibScan:
        if calibScan in os.listdir(scan_path):
            print(f'\nRalibrating using {calibScan}')
        else:
            print(f'Calibration file {calibScan} does not exist..')
            sys.exit()
           
    else:
        # ******************* SPEC Computer Commands ********************************

        # Check if filters are in place to allow direct beam scan
        check_ready()
        
        # Save current pd_savepath, filename and scan number
        saved_state = get_current_state()

        # Create remote_paths on SPEC computer if it doesn't exist
        #create_remote_paths(remote_scan_path, remote_img_path)

        # Create SPEC file and set PD savepath
        calibScan = create_SPEC_file(remote_scan_path)
        set_PD_savepath(remote_img_path)
        
        # Get direct beam scan range and steps
        tth, steps = get_tth_scan_range(init_dist=init_dist, pixel_sz=pixel_sz,
                                        ccd_shape=ccd_shape, orientation=orientation)

        # Run direct beam scan
        run_direct_beam_scan(tth, steps)
    
        # Restore saved current pd_savepath, specfilename, and scan number
        restore_state(saved_state)
        
    # ********************** Now moving to local computer ***************************
    
    # Read SPEC File and Images from Remote (Windows) Path
    spec_file = read_SPEC_file(scan_path, calibScan)
    img_fnames, pdi_fnames = get_img_fnames(img_path, pdi_path, calibScan)
    
    # Get Range of TTh Values that see Direct Beam
    print('\nGetting all images that see direct beam')
    img_fnames, pdi_fnames, tths = get_TTh_w_direct_beam(img_path, img_fnames, 
                                                         pdi_path, pdi_fnames)
    print(f'TTh range for direct beam: [{tths[0]}, {tths[-1]}]')

    # Fit all Images to get direct beam position at all TTH values
    print('\nFitting 2D PVoigt to all images..')
    tths, xs, ys =  fit_all_images(img_path, img_fnames, tths)
    print(len(tths), len(xs))
    print('Done')

    # Get Direct Beam Pixel at TTh = 0
    print('Obtaining direct beam pixel at TTh=0')
    x0, y0 = get_db_pixel(tths, xs, ys)
    print(f'Direct beam pixel at TTh=0: [{x0:.2f}, {y0:.2f}]\n')
    
    # Obtain Poni Parameters
    print('\nCalculating PONI File parameters (dist, rot2, rot3, poni1, poni2)')
    poni_params = get_poni_params(tths, xs, ys, x0, y0, pixel_sz=pixel_sz)
    
    # Create and save PONI file
    poni_file = os.path.join(poni_path, f'{calibScan}.poni')
    print(f'\nMaking and saving {poni_file}')
    make_poni(poni_file, spec_file, poni_params, detector=detector)

    # Create and save PONI file for Public
    poni_file = os.path.join(public_poni_path, f'{calibScan}.poni')
    print(f'\nMaking and saving {poni_file} to Public Folder')
    make_poni(poni_file, spec_file, poni_params, detector=detector)


if __name__ == '__main__':
    # Paths
    remote_path = '~/data/calibration'
    local_path  = 'P:\\bl2-1\\calibration'
    poni_path   = os.path.join(local_path, 'poni_files')
    public_poni_path  = os.path.join('C:\\Users\\Public', 'poni_files')
    
    run_calibration(remote_path, local_path, poni_path, public_poni_path)
