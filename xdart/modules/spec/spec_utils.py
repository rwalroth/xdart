# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports
import pandas as pd

# Qt imports

# This module imports
from xdart.utils import soft_list_eval


def get_spec_header(file_path):
    """Gets the header information of a spec data file.
    
    args:
        file_path: str, path to spec data file.
    
    returns:
        header: dict, header information including metadata and motor
            and detector names.
    """
    cont = True
    header = {
        'meta': {},
        'motors': {},
        'motors_r': {},
        'detectors': {},
        'detectors_r': {},
    }
    with open(file_path, 'r') as file:
        for lin in file:
            line = lin.split()
            if line:
                key = line[0]
                if '#S' in key:
                    break
                code = line[0][1:]
                if code == 'F': 
                    header['meta']['File'] = line[1:]

                elif code == 'E':
                    header['meta']['Epoch'] = eval(line[1])

                elif code == 'D':
                    header['meta']['Date'] = ' '.join(line[1:])

                elif code == 'C':
                    header['meta']['Comment'] = ' '.join(line[1:])
                    for i, val in enumerate(line):
                        if val == 'User' and line[i + 1] == '=':
                            header['meta']['User'] = line[i+2]
                
                elif 'O' in code:
                    num = int(code[1:])
                    header['motors'][num] = line[1:]
                
                elif 'o' in code:
                    num = int(code[1:])
                    header['motors_r'][num] = line[1:]
                
                elif 'J' in code:
                    num = int(code[1:])
                    header['detectors'][num] = line[1:]
                
                elif 'j' in code:
                    num = int(code[1:])
                    header['detectors_r'][num] = line[1:]
    return header


def get_spec_scan(file_path, scan_number, header):
    """Reads a spec data file and returns a specified scan as a
    pandas DataFrame.
    
    args:
        file_path: str, path to spec data file.
        scan_number: int, scan to look for.
        header: dict, header information returned from get_header.
    
    returns:
        df: pandas DataFrame, the data from the scan.
        meta: dict, metadata associated with scan.
    """
    cont = True
    df = None
    
    with open(file_path, 'r') as file:
        for lin in file:
            line = lin.split()
            if not line:
                if cont:
                    continue
                else:
                    break
            else:
                if line[0] == '#S' and str(scan_number) == line[1]:
                    cont = False
                    df, meta = _parse_scan(line, header)
                elif not cont:
                    df, meta = _parse_scan(line, header, df, meta)
    if df is None:
        raise KeyError("Scan not found")
    return df, meta


def _parse_scan(line, header, df=None, meta=None):
    """Helper function to parse information from spec file into scan
    data.
    
    args:
        header: dict, header information returned from get_header.
        df: pandas DataFrame, scan data read to this point in scan.
        meta: dict, metadata associated with the scan.
    
    returns:
        df: pandas DataFrame, the data from the scan.
        meta: dict, metadata associated with scan.
    """
    if meta is None:
        meta = {}
        
    flag = line[0]
    if '#' in flag:
        if 'S' in flag:
            meta.update({'Goniometer': {}, 'Motors': {}})
            meta['Command'] = ' '.join(line[2:])
            meta['Type'] = line[2]

        elif 'D' in flag:
            meta['Date'] = ' '.join(line[1:])

        elif 'T' in flag or 'M' in flag:
            meta['Counter'] = {
                'Amount': eval(line[1]), 'Type': line[2]
            }

        elif 'G' in flag:
            key = int(flag[2:])
            meta['Goniometer'][key] = soft_list_eval(line[1:])

        elif 'Q' in flag:
            meta['HKL'] = soft_list_eval(line[1:])

        elif 'P' in flag:
            motor_num = int(flag[2:])
            names = header['motors'][motor_num]
            positions = [eval(x) for x in line[1:]]
            meta['Motors'].update(
                {name: position for name, position in 
                zip(names, positions)}
            )
        # TODO: decide what to do with N;

        elif 'L' in flag:
            df = pd.DataFrame(columns=line[1:])

    else:
        vals = soft_list_eval(line)
        try:
            idx = df.index[-1] + 1
            df.loc[idx] = vals
        except IndexError:
            df.loc[0] = vals
    return df, meta
