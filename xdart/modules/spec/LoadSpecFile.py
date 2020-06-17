# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 16:39:57 2019

@author: walroth
"""
import os
from collections import OrderedDict
import pandas as pd
from copy import deepcopy

from xdart.utils import soft_list_eval
from ..operation import Operation



inputs = OrderedDict(
        spec_file_path=None,
        spec_file_name=None
        )

outputs = OrderedDict(
        header=dict(
                meta={},
                motors={},
                motors_r={},
                detectors={},
                detectors_r={}
                ),
        scans={},
        scans_meta={},
        last_line_read=dict(
                number=0,
                text=''
                ),
        current_scan={
            'num': 0,
            'data': None,
            'meta': None
        }
    )

class LoadSpecFile(Operation):
    """Operation for loading in data from a spec file. Currently
    unused, will be expanded on later for future analysis toolkit.
    """
    date_format = '%a %b %d %H:%M:%S %Y'

    def __init__(self):
        super(LoadSpecFile, self).__init__(inputs, outputs)
    
    def run(self):
        full_path = os.path.join(self.inputs['spec_file_path'],
                                 self.inputs['spec_file_name'])
        with open(full_path, 'r') as file:
            self._read_spec(file)
        
        return self.outputs
    
    
    def _read_spec(self, file):
        # iterate lines and assign to either head or scan lists
        state = 'beginning'
        head = []

        for lin_num, lin in enumerate(file):
            line = lin.split()
            self.outputs['last_line_read']['number'] = lin_num
            self.outputs['last_line_read']['text'] = lin
            # blank lines are used as breaks separating scans
            if line == []:
                # state flag used to control how lines are parsed
                if state == 'beginning':
                    continue

                elif state == 'head':
                    self._parse_header(head)
                    head = []

                elif state == 'scan':
                    continue

            else:
                # first item defines what type of info it is
                key = line[0]
                if '#F' in key:
                    state = 'head'
                elif '#S' in key:
                    state = 'scan'
                    scan_num = int(line[1])

                if state == 'head':
                    head.append(line)

                elif state == 'scan':
                    self._parse_scan(line, scan_num)
    
    
    def _parse_header(self, head):
        if head == []:
            return None
        
        else:
            meta = {}
            motors = {}
            motors_r = {}
            detectors = {}
            detectors_r = {}
            for line in head:
                key = line[0][1:]
                if key == 'F': 
                    meta['File'] = line[1:]

                elif key == 'E':
                    meta['Epoch'] = eval(line[1])

                elif key == 'D':
                    meta['Date'] = ' '.join(line[1:])

                elif key == 'C':
                    meta['Comment'] = ' '.join(line[1:])
                    for i, val in enumerate(line):
                        if val == 'User' and line[i + 1] == '=':
                            meta['User'] = line[i+2]
                
                elif 'O' in key:
                    num = int(key[1:])
                    motors[num] = line[1:]
                
                elif 'o' in key:
                    num = int(key[1:])
                    motors_r[num] = line[1:]
                
                elif 'J' in key:
                    num = int(key[1:])
                    detectors[num] = line[1:]
                
                elif 'j' in key:
                    num = int(key[1:])
                    detectors_r[num] = line[1:]
            
            self.outputs['header']['meta'].update(meta)
            self.outputs['header']['motors'].update(motors)
            self.outputs['header']['motors_r'].update(motors_r)
            self.outputs['header']['detectors'].update(detectors)
            self.outputs['header']['detectors_r'].update(detectors_r)
    
    def _parse_scan(self, line, scan_num):
        if line == []:
            return None

        flag = line[0]
        if '#' in flag:
            if 'S' in flag:
                self.outputs['scans_meta'][scan_num] = \
                    {'Goniometer': {}, 'Motors': {}}
                self.outputs['scans_meta'][scan_num]['Command'] = \
                    ' '.join(line[2:])
                self.outputs['scans_meta'][scan_num]['Type'] = line[2]

            elif 'D' in flag:
                self.outputs['scans_meta'][scan_num]['Date'] = \
                    ' '.join(line[1:])

            elif 'T' in flag or 'M' in flag:
                self.outputs['scans_meta'][scan_num]['Counter'] = \
                    {'Amount': eval(line[1]), 'Type': line[2]}

            elif 'G' in flag:
                key = int(flag[2:])
                self.outputs['scans_meta'][scan_num]['Goniometer'][key] = \
                    soft_list_eval(line[1:])

            elif 'Q' in flag:
                self.outputs['scans_meta'][scan_num]['HKL'] = \
                    soft_list_eval(line[1:])

            elif 'P' in flag:
                motor_num = int(flag[2:])
                names = self.outputs['header']['motors'][motor_num]
                positions = [eval(x) for x in line[1:]]
                self.outputs['scans_meta'][scan_num]['Motors'].update(
                    {name: position for name, position in 
                    zip(names, positions)}
                )
            # TODO: decide what to do with N;

            elif 'L' in flag:
                self.outputs['scans'][scan_num] = pd.DataFrame(columns=line[1:])

        else:
            vals = soft_list_eval(line)
            try:
                idx = self.outputs['scans'][scan_num].index[-1] + 1
                self.outputs['scans'][scan_num].loc[idx] = vals
            except IndexError:
                self.outputs['scans'][scan_num].loc[0] = vals
    