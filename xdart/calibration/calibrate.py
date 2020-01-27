import sys, os, glob, fnmatch, re
import numpy as np
import matplotlib.pyplot as plt

sys.path.append('~/Research/RDA/repos/xdart')

from collections import OrderedDict

from skimage import io

import scipy
import scipy.ndimage as ndimage
from scipy.signal import medfilt2d

from lmfit import Model
from lmfit_models import PlaneModel, LorentzianSquared2DModel, Gaussian2DModel, update_param_hints

from joblib import Parallel, delayed
import multiprocessing as mp

from xdart.utils import get_from_pdi, read_image_file, get_motor_val, smooth_img


def get_fit(im):
    # Flatten Arrays
    ydata = im.flatten()
    nrows, ncols = im.shape
    rows, cols = np.meshgrid(np.arange(0,ncols), np.arange(0,nrows))
    x = [rows.flatten(), cols.flatten()]

    plane_mod = PlaneModel()
    lor2D_mod = Gaussian2DModel()

    # Using the guess function
    pars = plane_mod.guess(ydata, x)
    pars += lor2D_mod.guess(ydata, x)

    Hints = {'sigma_x': {'value':5, 'min': 1},
             'sigma_y': {'value':5, 'min': 1},
             'amplitude': {'min': 0}
            }

    update_param_hints(pars, **Hints)
    
    mod_2D = plane_mod + lor2D_mod
    mod_2D.missing = 'drop'

    out = mod_2D.fit(ydata, pars, x=x)

    # Fit results
    I_fit = out.eval(x=[rows.flatten(), cols.flatten()])
    im_fit = I_fit.reshape(im.shape)
    
    return out, pars, im_fit


def fit_images_2D(fname, tth, kernel_size=3, window_size=3, order=0, verbose=False):
    if verbose: print(f'Processing {fname}')
    img = read_image_file(fname, return_float=True, verbose=False)
    
    smooth_img(img, kernel_size=kernel_size, window_size=window_size, order=order)
    fit_result, init_params, img_fit = get_fit(img)
    
    tth = np.round(tth, 3)
    Fit_Results[tth] = fit_result
    FNames[tth] = fname
    Img_Fits[tth] = img_fit
    Init_Params[tth] = init_params
    
    return


if __name__ == "__main__":
    print('running..')
    path = '/Users/v/SSRL_Data/RDA/calibration_test_data/2019_12_09'
    img_path = os.path.join(path, 'images')
    pdi_path = os.path.join(path, 'images')


    img_fnames = sorted(fnmatch.filter(os.listdir(img_path), '*direct_beam_full_scan1*.raw'))
    pdi_fnames = [f'{img_fname}.pdi' for img_fname in img_fnames
                if os.path.exists( os.path.join(pdi_path, f'{img_fname}.pdi') )]

    if len(pdi_fnames) != len(img_fnames):
        print('PDI files for all images not present..')
        
    tths = [get_motor_val( os.path.join(pdi_path, f), 'TwoTheta' ) for f in pdi_fnames]

    img_mean_vals = np.zeros(len(img_fnames))
    for idx, img_fname in enumerate(img_fnames):
        img = read_image_file( os.path.join(img_path, img_fname), return_float=True )
        img_mean_vals[idx] = np.mean(img)

    median_mean_vals = np.median(img_mean_vals)

    TThs = OrderedDict()
    no_peaks = []
    for idx, (img_fname, pdi_fname)  in enumerate(zip(img_fnames, pdi_fnames)):
        img = read_image_file( os.path.join(img_path, img_fname), return_float=True )
        if np.mean(img) > median_mean_vals/2.:
            tth = get_motor_val( os.path.join(pdi_path, pdi_fname), 'TwoTheta' )
            TThs[img_fname] = tth

    while True:
        keys = list(TThs.keys())
        tths = np.asarray([tth for k, tth in TThs.items()])
        
        if abs(tths[0]) == abs(tths[-1]):
            break
            
        if np.abs(tths[0]) > tths[-1]:
            del TThs[keys[0]]
        else:
            del TThs[keys[-1]]

    keys = keys[:20] + [keys[len(keys)//2]] + keys[-20:]
    TThs = OrderedDict({k:TThs[k] for k in keys})

    img_fnames = list(TThs.keys())
    pdi_fnames = [f'{img_fname}.pdi' for img_fname in img_fnames]
    tths = np.asarray([tth for k, tth in TThs.items()])
    print(tths[0], tths[-1])    
            
    plt.figure()
    plt.plot(img_mean_vals)


    Fit_Results, FNames, Img_Fits, Init_Params = dict(), dict(), dict(), dict()

    n_cores = mp.cpu_count()
    _ = Parallel(n_jobs=n_cores, require='sharedmem') (
        delayed(fit_images_2D)(os.path.join(img_path, fname),
                            tth, kernel_size=3, window_size=1, verbose='True')
        for (fname, tth) in zip(img_fnames[::], tths[::]) )


    tths_ = sorted(Fit_Results.keys())

    n0 = len(tths_)//2; tth0 = tths_[n0]
    x0, y0 = Fit_Results[tth0].params['center_y'], Fit_Results[tth0].params['center_x']

    xys = []
    ds, Ds, alphas, alphas1, rot3s, all_tths = [], [], [], [], [], []
    D_s = []
    for ii in range(0, n0):
        tth1, tth2 = tths_[ii].astype(np.float128), tths_[-ii-1].astype(np.float128)
        x1, y1 = Fit_Results[tth1].params['center_y'], Fit_Results[tth1].params['center_x']
        x2, y2 = Fit_Results[tth2].params['center_y'], Fit_Results[tth2].params['center_x']
        
        xys.append(np.asarray([x1, y1, x2, y2]))
        
        d1 = np.sqrt( (x1 - x0)**2 + (y1 - y0)**2 )
        d2 = np.sqrt( (x2 - x0)**2 + (y2 - y0)**2 )
        
        ds.append(np.asarray([d1,d2]))
        
        tth = np.deg2rad (abs(tth1))
        
        D = 2 * d1 * d2 * np.cos(tth) / np.sqrt(
            (d1 + d2)**2 - 4 * d1 * d2 * np.cos(tth)**2 ) * 0.0172
        
        D_ = 2 * d1 * d2 * (d1 + d2) * np.tan(tth) / (
            (d1 + d2)**2 * np.tan(tth)**2  + (d1 - d2)**2 ) * 0.0172

        alpha = np.arccos( (d1 + d2) * np.sin(tth) / np.sqrt(
            (d1 + d2)**2 - 4 * d1 * d2 * np.cos(tth)**2 ) ) * 180/np.pi
        
        alpha1 = np.rad2deg( np.arctan( 1/np.tan(tth) * (d1 - d2) / (d1 + d2) ) )
        
        rot3 = np.rad2deg( (x1 - x2) / (y1 - y2) )
        
        Ds.append(D)
        D_s.append(D_)
        alphas.append(alpha)
        alphas1.append(alpha1)
        rot3s.append(rot3)
        all_tths.append(tth)

    ds = np.asarray(ds); xys = np.asarray(xys)

    d1, d2 = ds[:,0], ds[:,1] 

    plt.figure()
    #plt.plot(d1)
    #plt.plot(d2)
    plt.plot(all_tths, d1-d2)

    plt.figure()
    plt.plot(all_tths, Ds[:])
    plt.title('D')

    plt.figure()
    plt.plot(all_tths, D_s[:])
    plt.title('D_')

    plt.figure()
    plt.plot(alphas[:])
    plt.title('alphas')

    plt.figure()
    plt.plot(alphas1[:])
    plt.title('alphas1')

    plt.figure()
    plt.plot(rot3s[:])
    plt.title('rot3')