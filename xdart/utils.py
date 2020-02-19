# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import time

# Other imports
import numpy as np
import pandas as pd
import yaml
import json
import h5py

# This module imports


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


def check_encoded(grp, name):
    """Checks grp attributes for encoded, checks resulting attribute
    against name. If encoded not an attribute, returns False.
    """
    return grp.attrs.get("encoded", "not_found") == name


def data_to_h5(data, grp, key, encoder='yaml', compression='lzf'):
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
        data: dictionary to add to hdf5
        grp: h5py group object to add the data to
    
    returns:
        None
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
    if key in grp:
        if check_encoded(grp[key], "str"):
            grp[key][()] = data
        else:
            del(grp[key])
            grp.create_dataset(key, data=data, dtype=h5py.string_dtype())
    else:
            grp.create_dataset(key, data=data, dtype=h5py.string_dtype())


def series_to_h5(data, grp, key, compression):
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
    if key in grp:
        if check_encoded(grp[key], 'scalar'):
            if grp[key].dtype == np.array(data).dtype:
                grp[key][()] = data
                return
        del(grp[key])
    grp.create_dataset(key, data=data)
    grp[key].attrs['encoded'] = 'scalar'


def arr_to_h5(data, grp, key, compression):
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


def soft_list_eval(data, scope={}):
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
            out.append(eval(x, scope))
        except:
            try:
                out.append(x.decode())
            except (AttributeError, SyntaxError):
                out.append(x)
    
    return out


def catch_h5py_file(filename, mode='r', tries=100, *args, **kwargs):
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