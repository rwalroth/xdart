# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import sys

# Other imports
import numpy as np
import re

from skimage import io

import scipy
import scipy.ndimage as ndimage
from scipy.signal import medfilt2d
import pandas as pd
import yaml
import json
import h5py


# This module imports
from lmfit.models import LinearModel, GaussianModel, ParabolicModel
from xdart.calibration.lmfit_models import PlaneModel, Gaussian2DModel, LorentzianSquared2DModel, Pvoigt2DModel, update_param_hints


def write_xye(fname, xdata, ydata):
    with open(fname, "w") as file:
        for i in range(0, len(xdata)):
            file.write(
                str(xdata[i]) + "\t" +
                str(ydata[i]) + "\t" +
                str(np.sqrt(ydata[i])) + "\n"
            )


def write_csv(fname, xdata, ydata):
    with open(fname, 'w') as file:
        for i in range(0, len(xdata)):
            file.write(str(xdata[i]) + ', ' + str(ydata[i]) + '\n')


def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def find_between_r( s, first, last ):
    try:
        start = s.rindex( first ) + len( first )
        end = s.rindex( last, start )
        return s[start:end]
    except ValueError:
        return ""


def query(question):
    """Ask a question with allowed options via input()
    and return their answer.
    """
    sys.stdout.write(question)
    return input()

    
def get_from_pdi(pdi_file):

    with open(pdi_file, 'r') as f:
        pdi_data = f.read()

    pdi_data = pdi_data.replace('\n', ';')

    try:
        counters = re.search('All Counters;(.*);;# All Motors', pdi_data).group(1)
        cts = re.split(';|=', counters)
        Counters = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

        motors = find_between(pdi_data, 'All Motors;', ';#')
        cts = re.split(';|=', motors)
        Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
    except:
        ss1 = '# Diffractometer Motor Positions for image;# '
        ss2 = ';# Calculated Detector Calibration Parameters for image:'

        motors = re.search(f'{ss1}(.*){ss2}', pdi_data).group(1)
        cts = re.split(';|=', motors)
        Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
        Motors['TwoTheta'] = Motors['2Theta']
        Counters = {}

    return Counters, Motors


def get_motor_val(pdi_file, motor):
    _, Motors = get_from_pdi(pdi_file)

    return Motors[motor]


def read_image_file(fname, orientation='horizontal', flip=False,
                    shape_100K=(195, 487), shape_300K=(195,1475),
                    return_float=False, verbose=False):
    if verbose: print('Reading image data into numpy array..')
    if 'tif' in fname[-5:]:
        img = np.asarray(io.imread(fname))
    else:
        try:
            img = np.asarray(np.fromfile(fname, dtype='int32', sep="").reshape(shape_100K))
        except:
            img = np.asarray(np.fromfile(fname, dtype='int32', sep="").reshape(shape_300K))
            
    if return_float:
        img = np.asarray(img, np.float)
        
    if orientation == 'vertical':
        img = img.T
        
    if flip: 
        img = np.flipud(img)

    return img


def smooth_img(img, kernel_size=3, window_size=3, order=0):
    if (np.mod(kernel_size, 2) == 0) or (np.mod(window_size, 2) == 0):
        print('Smoothing windows should be odd integers')
        return img

    if order >= window_size:
        order = window_size - 1

    if kernel_size > 1:
        img = medfilt2d(img, 3)
    if window_size > 1:
        img = ndimage.gaussian_filter(img, sigma=(window_size, window_size), order=order)

    return img


def get_fit(im, function='gaussian'):
    # Flatten Arrays
    ydata = im.flatten()
    nrows, ncols = im.shape
    rows, cols = np.meshgrid(np.arange(0,ncols), np.arange(0,nrows))
    x = [rows.flatten(), cols.flatten()]

    Models = {'gaussian': Gaussian2DModel(),
              'lorentzian': LorentzianSquared2DModel(),
              'pvoigt': Pvoigt2DModel()}
    
    plane_mod = PlaneModel()
    curve_mod = Models[function]
    #curve_mod = Gaussian2DModel()

    # Using the guess function
    pars = plane_mod.guess(ydata, x)
    pars += curve_mod.guess(ydata, x)

    Hints = {'sigma_x':   {'value':5, 'min': 1},
             'sigma_y':   {'value':5, 'min': 1},
             'amplitude': {'min': 0},
             'intercept': {'value':0, 'vary':False},
             'slope_x':   {'value':0, 'vary':False},
             'slope_y':   {'value':0, 'vary':False},
            }

    update_param_hints(pars, **Hints)
    
    mod_2D = plane_mod + curve_mod
    mod_2D.missing = 'drop'

    out = mod_2D.fit(ydata, pars, x=x)

    # Fit results
    I_fit = out.eval(x=[rows.flatten(), cols.flatten()])
    im_fit = I_fit.reshape(im.shape)
    
    return out, pars, im_fit


def fit_images_2D(fname, tth, function='gaussian',
                  kernel_size=3, window_size=3, order=0,
                  Fit_Results={}, FNames={}, Img_Fits={}, Init_Params={},
                  verbose=False, **kwargs):
    if verbose: print(f'Processing {fname}')
    img = read_image_file(fname, return_float=True, verbose=False, **kwargs)
    
    smooth_img(img, kernel_size=kernel_size, window_size=window_size, order=order)
    fit_result, init_params, img_fit = get_fit(img, function=function)
    
    tth = np.round(tth, 3)
    Fit_Results[tth] = fit_result
    FNames[tth] = fname
    Img_Fits[tth] = img_fit
    Init_Params[tth] = init_params
    
    return (tth, fit_result)


def data_to_h5(data, grp, key, encoder='yaml', compression='lzf'):
    if data is None:
        grp.create_dataset(key, data=h5py.Empty("f"))
        grp[key].attrs['encoded'] = 'None'

    elif type(data) == dict:
        new_grp = grp.create_group(key)
        new_grp.attrs['encoded'] = 'dict'
        dict_to_h5(data, new_grp, compression=compression)

    elif type(data) == str:
        grp.create_dataset(key, data=np.string_(data))
        grp[key].attrs['encoded'] = 'str'

    elif type(data) == pd.core.series.Series:
        new_grp = grp.create_group(key)
        new_grp.attrs['encoded'] = 'Series'
        new_grp.create_dataset('data', data=np.array(data), compression=compression)
        index_to_h5(data.index, 'index', new_grp, compression)
        new_grp.create_dataset('name', data=np.string_(data.name))

    elif type(data) == pd.core.frame.DataFrame:
        new_grp = grp.create_group(key)
        new_grp.attrs['encoded'] = 'DataFrame'
        index_to_h5(data.index, 'index', new_grp, compression)
        index_to_h5(data.columns, 'columns', new_grp, compression)
        new_grp.create_dataset('data', data=np.array(data), compression=compression)

    else:
        try:
            if np.array(data).shape == ():
                grp.create_dataset(key, data=data)
                grp[key].attrs['encoded'] = 'data'
            else:
                grp.create_dataset(key, data=data, compression=compression)
                grp[key].attrs['encoded'] = 'data'

        except TypeError:
            print(f"TypeError, encoding {key} using {encoder}")
            try:
                if encoder == 'yaml':
                    string = np.string_(yaml.dump(data))
                elif encoder == 'json':
                    string = np.string_(json.dumps(data))
                grp.create_dataset(key, data=np.string_(string))
                grp[key].attrs['encoded'] = encoder
            except Exception as e:
                print(e)
                try:
                    grp.create_dataset(key, data=np.string_(data))
                    grp[key].attrs['encoded'] = 'unknown'
                except Exception as e:
                    print(e)
                    print(f"Unable to dump {key}")


def index_to_h5(index, key, grp, compression):
    if index.dtype == 'object':
        grp.create_dataset(
            key, data=np.array([np.string_(str(x)) for x in index])
        )
    else:
        grp.create_dataset(key, data=np.array(index), compression=compression)


def dict_to_h5(data, grp, **kwargs):
    """Adds dictionary data to hdf5 group with same keys as dictionary.
    See data_to_h5 for how datatypes are handled.

    args:
        data: dictionary to add to hdf5
        grp: h5py group object to add the data to

    returns:
        None
    """
    for key in data:
        s_key = str(key)
        sub_data = data[key]
        data_to_h5(sub_data, grp, s_key, **kwargs)


def attributes_to_h5(obj, grp, lst_attr=None, priv=False, dpriv=False,
                     **kwargs):
    """Function which takes a list of class attributes and stores them
    in a provided h5py group. See data_to_h5 for how datatypes are
    handled.
    """
    if lst_attr is None:
        if dpriv:
            lst_attr = list(obj.__dict__.keys())
        elif priv:
            lst_attr = [x for x in obj.__dict__.keys() if '__' not in x]
        else:
            lst_attr = [x for x in obj.__dict__.keys() if '_' not in x]
    for attr in lst_attr:
        if attr in grp.keys():
            del(grp[attr])
        data = getattr(obj, attr)
        data_to_h5(data, grp, attr, **kwargs)


def h5_to_data(grp, encoder=True, Loader=yaml.UnsafeLoader):
    if encoder and 'encoded' in grp.attrs:
        encoded = grp.attrs['encoded']
        if encoded == 'None':
            data = None

        elif encoded == 'dict':
            data = h5_to_dict(grp, encoder=encoder, Loader=Loader)

        elif encoded == 'str':
            data = grp[...].item().decode()

        elif encoded == 'Series':
            data = pd.Series(
                data = grp['data'][()],
                index = h5_to_index(grp['index']),
                name = grp['name'][...].item().decode()
            )

        elif encoded == 'DataFrame':
            data = pd.DataFrame(
                data = grp['data'][()],
                index = h5_to_index(grp['index']),
                columns = h5_to_index(grp['columns']),
            )

        elif encoded == 'data':
            if grp.shape == ():
                data = grp[...].item()
            else:
                data = grp[()]

        elif encoded == 'yaml':
            data = yaml.load(grp[...].item(), Loader=Loader)

        elif encoded == 'json':
            data = json.loads(grp[...].item())

        elif encoded == 'unknown':
            try:
                data = eval(grp[...].item())
            except:
                data = grp[...].item().decode()
    else:
        if type(grp) == h5py._hl.group.Group:
            data = h5_to_dict(grp, encoder=encoder, Loader=Loader)

        elif grp.shape == ():
            temp = grp[...].item()
            if type(temp) == bytes:
                temp = temp.decode()
            if temp == 'None':
                data = None
            else:
                data = temp

        elif grp.shape is None:
            data = None

        else:
            data = grp[()]

    return data


def h5_to_index(grp):
    if np.issubdtype(grp.dtype, np.number):
        return grp[()]
    else:
        return soft_list_eval(grp)


def h5_to_dict(grp, **kwargs):
    """Converts h5py group to dictionary. See h5_to_data for how
    different datatypes are handled.

    args:
        grp: h5py group object

    returns:
        data: dictionary of data from h5py group
    """
    data = {}
    for key in grp.keys():
        try:
            e_key = eval(key, {})
        except:
            e_key = key

        data[e_key] = h5_to_data(grp[key], **kwargs)

    return data


def h5_to_attributes(obj, grp, lst_attr=None, **kwargs):
    if lst_attr is None:
        lst_attr = grp.keys()
    for attr in lst_attr:
        if attr in obj.__dict__.keys():
            data = h5_to_data(grp[attr], **kwargs)
            setattr(obj, attr, data)


def div0( a, b ):
    """ ignore / 0, div0( [-1, 0, 1], 0 ) -> [0, 0, 0] """
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.true_divide( a, b )
        c[ ~ np.isfinite( c )] = 0  # -inf inf NaN
    return c


def soft_list_eval(data):
    """Tries to create list of evaluated items in data. If exception
    is thrown by eval, it just adds the element as is to the list.

    args:
        data: list or array-like, input data to be evaluated

    returns:
        out: list of values in data with eval applied if possible
    """
    out = []
    for x in data:
        try:
            out.append(eval(x, {}))
        except:
            try:
                out.append(x.decode())
            except (AttributeError, SyntaxError):
                out.append(x)

    return out


def catch_h5py_file(filename, *args, **kwargs):
    while True:
        try:
            hdf5_file = h5py.File(filename, *args, **kwargs)
            break  # Success!
        except OSError:
            pass
    return hdf5_file


def query_yes_no(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.
    
    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")