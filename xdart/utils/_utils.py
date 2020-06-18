# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import time
import sys

# Other imports
import numpy as np
import re
from datetime import datetime

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
from .lmfit_models import PlaneModel, Gaussian2DModel, LorentzianSquared2DModel, Pvoigt2DModel, update_param_hints


def write_xye(fname, xdata, ydata):
    """Saves data to an xye file. Variance is the square root of the
    signal.
    
    args:
        fname: str, path to file
        xdata: angle or q data
        ydata: intensity
    """
    with open(fname, "w") as file:
        for i in range(0, len(xdata)):
            file.write(
                str(xdata[i]) + "\t" +
                str(ydata[i]) + "\t" +
                str(np.sqrt(ydata[i])) + "\n"
            )


def write_csv(fname, xdata, ydata):
    """Saves data to a csv file.
    
    args:
        fname: str, path to file
        xdata: angle or q data
        ydata: intensity
    """
    with open(fname, 'w') as file:
        for i in range(0, len(xdata)):
            file.write(str(xdata[i]) + ', ' + str(ydata[i]) + '\n')


def check_encoded(grp, name):
    """Checks grp attributes for encoded, checks resulting attribute
    against name. If encoded not an attribute, returns False.
    """
    return grp.attrs.get("encoded", "not_found") == name


def find_between( s, first, last ):
    """find first occurence of substring in string s
     between two substrings (first and last)

    Args:
        s (str): input string
        first (str): first substring
        last (str): second substring

    Returns:
        str: substring between first and last
    """
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def find_between_r( s, first, last ):
    """find last occurence of substring in string s
     between two substrings (first and last)

    Args:
        s (str): input string
        first (str): first substring
        last (str): second substring

    Returns:
        str: substring between first and last
    """
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

    
def get_image_meta_data(meta_file, BL='2-1'):
    """Get image meta data from pdi/txt files for different beamlines

    Args:
        meta_file (str): Meta file name with path
        BL (str, optional): Beamline. Defaults to '2-1'.

    Returns:
        [dict]: Dictionary with all the meta data
    """

    with open(meta_file, 'r') as f:
        data = f.read()

    image_meta_data = {}
    if BL == '2-1':
        data = data.replace('\n', ';')

        try:
            counters = re.search('All Counters;(.*);;# All Motors', data).group(1)
            cts = re.split(';|=', counters)
            Counters = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

            motors = re.search('All Motors;(.*);#', data).group(1)
            cts = re.split(';|=', motors)
            Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
        except:
            ss1 = '# Diffractometer Motor Positions for image;# '
            ss2 = ';# Calculated Detector Calibration Parameters for image:'

            motors = re.search(f'{ss1}(.*){ss2}', data).group(1)
            cts = re.split(';|=', motors)
            Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
            Motors['TwoTheta'] = Motors['2Theta']
            Counters = {}
        
        image_meta_data['epoch'] = data[data.rindex(';')+1:]

    elif BL == '11-3':

        counters = re.search('# Counters\n(.*)\n', data).group(1)
        cts = re.split(',|=', counters)
        Counters = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

        motors = re.search('# Motors\n(.*)\n', data).group(1)
        cts = re.split(',|=', motors)
        Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
        
        # image_meta_data['User'] = (data[data.index('User: ')+5: data.index(', time')]).strip()
        # image_meta_data['Time'] = (data[data.index('time: ')+5: data.index('# Temp')-2]).strip()
        Time = (data[data.index('time: ')+5: data.index('# Temp')-2]).strip()
        
        # d = datetime.strptime(image_meta_data['Time'], "%a %b %d %H:%M:%S %Y")
        d = datetime.strptime(Time, "%a %b %d %H:%M:%S %Y")
        image_meta_data['epoch'] = time.mktime(d.timetuple())

    image_meta_data.update(Counters)
    image_meta_data.update(Motors)
    
    return image_meta_data


def get_from_pdi(pdi_file):
    """Get motor and counter names and values from PDI file

    Args:
        pdi_file (str): PDI file name with path

    Returns:
        [dict]: Tupe of two dictionaries containing Counters and Motors
    """

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
    """Return position of a particular motor from PDI file

    Args:
        pdi_file (str): PDI file name with path
        motor (str): Motor name

    Returns:
        float: Motor position
    """
    _, Motors = get_from_pdi(pdi_file)

    return Motors[motor]


def read_image_file(fname, orientation='horizontal', flip=False,
                    shape_100K=(195, 487), shape_300K=(195,1475),
                    return_float=False, verbose=False):
    """Read image file and return numpy array

    Args:
        fname (str): File Name with path
        orientation (str, optional): Orientation of detector. Defaults to 'horizontal'.
        flip (bool, optional): Flag to flip the image (required by pyFAI at times). Defaults to False.
        shape_100K (tuple, optional): Shape of numpy array for Pilatus 100K. Defaults to (195, 487).
        shape_300K (tuple, optional): Shape of numpy array for Pilatus 300K. Defaults to (195,1475).
        return_float (bool, optional): Convert array to float. Defaults to False.
        verbose (bool, optional): Print debug messages. Defaults to False.

    Returns:
        ndarray: Image data read into numpy array
    """
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
    """Apply a Gaussian filter to smooth image

    Args:
        img (ndarray): 2D numpy array for image
        kernel_size (int, optional): Gaussian filter kernel. Defaults to 3.
        window_size (int, optional): Gaussian filter window (should be odd). Defaults to 3.
        order (int, optional): Order of the filter. Defaults to 0.

    Returns:
        ndarray: Smoothed image
    """
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
    """Custom function to perform 2D fit (using lmfit) on an image

    Args:
        im (ndarray): 2D array representing the image
        function (str, optional): Fitting function to use. Defaults to 'gaussian'.

    Returns:
        tuple: Fit result (lmfit Model object), fit parameters, and evaluated fit
    """
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
    """Wrapper function aroung get_fit function

    Args:
        fname (str): Image file name
        tth (float): Value of 2th (used as key for returned dictionary)
        function (str, optional): Fitting function. Defaults to 'gaussian'.
        kernel_size (int, optional): Gaussian smoothing kernel size. Defaults to 3.
        window_size (int, optional): Gaussian smoothing window size. Defaults to 3.
        order (int, optional): Order of Gaussian filter. Defaults to 0.
        Fit_Results (dict, optional): Dictionary with tth as key containing fit result. Defaults to {}.
        FNames (dict, optional): Dictionary containing file names for each tth. Defaults to {}.
        Img_Fits (dict, optional): Dictionary containing the evaluated fits for each tth. Defaults to {}.
        Init_Params (dict, optional): Dictionary containing initial fit parameters for each tth. Defaults to {}.
        verbose (bool, optional): Flag to print debug messages. Defaults to False.

    Returns:
        tuple: tth value and fit result
    """
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
    """Saves data to hdf5 file. Global function, calls other functions
    based on data type. If data type can't be determined, tries to
    save as a dataset, and ultimately defaults to a string
    representation.
    
    args:
        data: object to be saved
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        key: str, name of new Group or Dataset
        encoder: str, 'yaml' or 'json', how to encode stubborn data
            types.
        compression: str, compression algorithm to use. See h5py docs.
    """
    if data is None:
        none_to_h5(grp, key)

    elif type(data) == dict:
        dict_to_h5(data, grp, key, compression=compression)
    
    elif type(data) == str:
        str_to_h5(data, grp, key)
    
    elif type(data) == pd.core.series.Series:
        series_to_h5(data, grp, key, compression)
    
    elif type(data) == pd.core.frame.DataFrame:
        dataframe_to_h5(data, grp, key, compression)
    
    else:
        try:
            if np.array(data).shape == ():
                scalar_to_h5(data, grp, key)
            else:
                arr_to_h5(data, grp, key, compression)

        except TypeError:
            print(f"TypeError, encoding {key} using {encoder}")
            try:
                encoded_h5(data, grp, key, encoder)
            except Exception as e:
                print(e)
                try:
                    if key in grp:
                        if check_encoded(grp[key], 'unknown'):
                            grp[key][()] = np.string_(data)
                            return
                        else:
                            del(grp[key])
                    grp.create_dataset(key, data=np.string_(data),
                                    dtype=h5py.string_dtype())
                    grp[key].attrs['encoded'] = 'unknown'
                except Exception as e:
                    print(e)
                    print(f"Unable to dump {key}")


def none_to_h5(grp, key):
    if key in grp:
        del(grp[key])
    grp.create_dataset(key, data=h5py.Empty("f"))
    grp[key].attrs['encoded'] = 'None'


def dict_to_h5(data, grp, key, **kwargs):
    """Adds dictionary data to hdf5 group with same keys as dictionary.
    See data_to_h5 for how datatypes are handled.

    args:
        data: dict, dictionary to add to hdf5
        grp: h5py Group or File, where to add the data to
        key: str, name of new group
        **kwargs: passed on to data_to_h5.
    """
    if key in grp:
        if not check_encoded(grp[key], "dict"):
            del(grp[key])
            new_grp = grp.create_group(key)
            new_grp.attrs["encoded"] = "dict"
        else:
            new_grp = grp[key]
    else:
        new_grp = grp.create_group(key)
    
    for jey in data:
        s_key = str(jey)
        sub_data = data[jey]
        data_to_h5(sub_data, new_grp, s_key, **kwargs)


def str_to_h5(data, grp, key):
    """Saves string to hdf5 file. Saved as h5py.string_dtype, if
    key exists will overwrite.
    
    args:
        data: str, object to be saved
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        key: str, name of new Group or Dataset
    """
    if key in grp:
        if check_encoded(grp[key], "str"):
            grp[key][()] = data
        else:
            del(grp[key])
            grp.create_dataset(key, data=data, dtype=h5py.string_dtype())
    else:
            grp.create_dataset(key, data=data, dtype=h5py.string_dtype())


def series_to_h5(data, grp, key, compression):
    """Saves pandas Series to hdf5 file.
    
    args:
        data: Series, object to be saved
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        key: str, name of new Group or Dataset
        compression: str, compression algorithm to use. See h5py docs.
    """
    if key in grp:
        if check_encoded(grp[key], "Series"):
            new_grp = grp[key]
            new_grp['data'][()] = np.array(data)
            index_to_h5(data.index, 'index', new_grp, compression)
            new_grp.attrs['name'] = data.name
            return
        else:
            del(grp[key])
    
    new_grp = grp.create_group(key)
    new_grp.attrs['encoded'] = 'Series'
    new_grp.create_dataset('data', data=np.array(data), compression=compression,
                           chunks=True)
    index_to_h5(data.index, 'index', new_grp, compression)
    new_grp.attrs['name'] = data.name


def dataframe_to_h5(data, grp, key, compression):
    """Saves pandas DataFrame to hdf5 file.
    
    args:
        data: DataFrame, object to be saved
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        key: str, name of new Group or Dataset
        compression: str, compression algorithm to use. See h5py docs.
    """
    if key in grp:
        if check_encoded(grp[key], "DataFrame"):
            new_grp = grp[key]
        else:
            del(grp[key])
            new_grp = grp.create_group(key)
            new_grp.attrs['encoded'] = 'DataFrame'
    else:
        new_grp = grp.create_group(key)
        new_grp.attrs['encoded'] = 'DataFrame'
    index_to_h5(data.index, 'index', new_grp, compression)
    index_to_h5(data.columns, 'columns', new_grp, compression)
    if 'data' in new_grp:
        new_grp['data'].resize(np.array(data).shape)
        new_grp['data'][()] = np.array(data)[()]
    else:
        new_grp.create_dataset('data', data=np.array(data), compression=compression,
                                chunks=True, maxshape=(None,None))


def index_to_h5(index, key, grp, compression):
    """Saves index from Series or DataFrame to hdf5 file. If not a
    scalar index, saves data as strings.
    
    args:
        index: object to be saved
        key: str, name of new Group or Dataset
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        compression: str, compression algorithm to use. See h5py docs.
    """
    if key in grp:
        if grp[key].shape == (0,):
            del(grp[key])
        
    if index.dtype == 'object':
        if len(index) > 0:
            strindex = np.array([np.string_(str(x)) for x in index])
            if key in grp:
                grp[key].resize(strindex.shape)
                grp[key][()] = strindex[()]
            else:
                grp.create_dataset(
                    key, data=strindex, dtype=h5py.string_dtype(),
                    chunks=True, maxshape=(None,)
                )
        else:
            if key in grp:
                del(grp[key])
            grp.create_dataset(key, data=np.array([]))
    else:
        arrindex = np.array(index)
        if key in grp:
            grp[key].resize(arrindex.shape)
            grp[key][()] = arrindex[()]
        else:
            grp.create_dataset(
                key, data=np.array(index), compression=compression,
                chunks=True, maxshape=(None,)
            )


def scalar_to_h5(data, grp, key):
    """Saves scalar to hdf5 file.
    
    args:
        data: scalar, object to be saved
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        key: str, name of new Group or Dataset
    """
    if key in grp:
        if check_encoded(grp[key], 'scalar'):
            if grp[key].dtype == np.array(data).dtype:
                grp[key][()] = data
                return
        del(grp[key])
    grp.create_dataset(key, data=data)
    grp[key].attrs['encoded'] = 'scalar'


def arr_to_h5(data, grp, key, compression):
    """Saves numpy array or list to hdf5 file. Ensures resizability, and
    overwrites data present without deleting data.
    
    args:
        data: numpy array or list, object to be saved
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        key: str, name of new Group or Dataset
        compression: str, compression algorithm to use. See h5py docs.
    """
    arr = np.array(data)
    if key in grp:
        if check_encoded(grp[key], 'arr'):
            if grp[key].dtype == arr.dtype:
                grp[key].resize(arr.shape)
                grp[key][()] = arr[()]
                return
        del(grp[key])
    grp.create_dataset(key, data=arr, compression=compression, chunks=True,
                       maxshape=tuple(None for x in arr.shape))
    grp[key].attrs['encoded'] = 'arr'


def encoded_h5(data, grp, key, encoder):
    """Saves data of unparsed type to hdf5 file. Uses the encoder to
    represent the data as a string.
    
    args:
        data: data to be saved, unknown type.
        grp: h5py File or Group, where data will be saved.
        key: str, name of new Dataset
        encoder: str, 'yaml' or 'json', how to encode stubborn data
            types.
    """
    if encoder == 'yaml':
        string = np.string_(yaml.dump(data))
    elif encoder == 'json':
        string = np.string_(json.dumps(data))
    if key in grp:
        if check_encoded(grp[key], encoder):
            grp[key][()] = string
            return
        else:
            del(grp[key])
    grp.create_dataset(key, data=string, dtype=h5py.string_dtype())
    grp[key].attrs['encoded'] = encoder


def attributes_to_h5(obj, grp, lst_attr=None, priv=False, dpriv=False,
                     **kwargs):
    """Function which takes a list of class attributes and stores them
    in a provided h5py group. See data_to_h5 for how datatypes are
    handled.
    
    args:
        obj: object to store
        grp: h5py File or Group, where data will be saved. Creates new
            Group or Dataset in grp.
        lst_attr: list or None, if list only the listed attributes are
            stored.
        priv: bool, if True and lst_attr is None, stores functions
            beginning with single _
        drpiv: bool, if True and lst_attr is None, stores attributes
            beginning with double _
        kwargs: passed to data_to_h5
    """
    if lst_attr is None:
        if dpriv:
            lst_attr = list(obj.__dict__.keys())
        elif priv:
            lst_attr = [x for x in obj.__dict__.keys() if '__' not in x]
        else:
            lst_attr = [x for x in obj.__dict__.keys() if '_' not in x]
    for attr in lst_attr:
        data = getattr(obj, attr)
        data_to_h5(data, grp, attr, **kwargs)


def h5_to_data(grp, encoder=True, Loader=yaml.UnsafeLoader):
    """Reads data from hdf5 file and returns appropriate datatype.
    
    args:
        grp: h5py File or Group, where the data is stored
        encoder: bool, if True checks the 'encoded' attribute to know
            the type
        Loader: yaml Loader, passed to yaml if encoded with yaml.
    
    returns:
        data: unknown type, the data in grp.
    """
    if encoder and 'encoded' in grp.attrs:
        encoded = grp.attrs['encoded']
        if encoded == 'None':
            data = None

        elif encoded == 'dict':
            data = h5_to_dict(grp, encoder=encoder, Loader=Loader)

        elif encoded == 'str':
            try:
                data = grp[...].item().decode()
            except AttributeError:
                data = grp[()]
        
        elif encoded == 'Series':
            data = pd.Series(
                data = grp['data'][()],
                index = h5_to_index(grp['index']),
                name = grp.attrs['name']
            )

        elif encoded == 'DataFrame':
            data = pd.DataFrame(
                data = grp['data'][()],
                index = h5_to_index(grp['index']),
                columns = h5_to_index(grp['columns']),
            )

        elif encoded in ['data', 'arr', 'scalar']:
            data = grp[()]

        elif encoded == 'yaml':
            data = yaml.load(grp[...].item(), Loader=Loader)

        elif encoded == 'json':
            data = json.loads(grp[...].item())

        elif encoded == 'unknown':
            try:
                data = eval(grp[...].item())
            except:
                try:
                    data = grp[...].item().decode()
                except AttributeError:
                    data = grp[...].item()
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
    """Gets index from grp for Series or DataFrame. Uses soft_list_eval
    to handle object index types.
    
    args:
        grp: h5py File or Group, where the data is stored
        
    returns:
        list or array to be used as index
    """
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
    """Sets attributes of obj using data in an hdf5 file. See h5_to_data
    for how data types are handled.
    
    args:
        obj: object to set attributes to
        grp: h5py File or Group, where the data is stored
        lst_attr: list of attributes to set. If not provided, sets
            all keys in grp
        kwargs: Passed to h5_to_data
    """
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


def soft_list_eval(data, scope={}):
    """Tries to create list of evaluated items in data. If exception
    is thrown by eval, it just adds the element as is to the list.

    args:
        data: list or array-like, input data to be evaluated
        scope: dict, scope of functions passed to eval. See eval
            documentation

    returns:
        out: list of values in data with eval applied if possible
    """
    out = []
    for x in data:
        try:
            out.append(eval(x, scope))
        except:
            try:
                out.append(x.decode())
            except (AttributeError, SyntaxError):
                out.append(x)

    return out


def catch_h5py_file(filename, mode='r', tries=100, *args, **kwargs):
    """Forces an h5py object to be opened. Catches OSErrors which can
    be thrown. Will try a set number of times before giving up.
    
    args:
        filename: str, path to file
        mode: str, mode to open file. See h5py docs
        tries: int, how many times to try opening the file
        args, kwargs: passed to h5py.File
    """
    failed = True
    for i in range(tries):
        if i % 10 == 0 and i > 0:
            print(f"Tried catching {i} times.")
        try:
            hdf5_file = h5py.File(filename, mode, *args, **kwargs)
            failed = False
            break  # Success!
        except OSError:
            time.sleep(0.05)
            pass
    if failed:
        hdf5_file = h5py.File(filename, mode, *args, **kwargs)
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