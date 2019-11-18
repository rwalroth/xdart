# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
from collections import OrderedDict
import time
import copy
import traceback

# Other imports
import numpy as np
from paws.operations.SPEC import LoadSpecFile, MakePONI
from paws.containers import PONI
from paws.plugins.ewald import EwaldArch, EwaldSphere
from paws.pawstools import catch_h5py_file as catch

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .specUI import *
from .....gui.gui_utils import NamedActionParameter

params = [
    {'name': 'Scan Number', 'type': 'int', 'value': 0},
    {'name': 'Spec File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='spec_file_browse', title= 'Browse...'),
    {'name': 'Image Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_dir_browse', title= 'Browse...'),
    {'name': 'Calibration PONI File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='poni_file_browse', title= 'Browse...'),
    {'name': 'Timeout', 'type': 'float', 'value': 5},
    {'name': 'Rotation Motors', 'type': 'group', 'children': [
        {'name': 'Rot1', 'type': 'str', 'default': ''},
        {'name': 'Rot2', 'type': 'str', 'default': ''},
        {'name': 'Rot3', 'type': 'str', 'default': ''}
    ]},
    {'name': 'Calibration Angles', 'type': 'group', 'children': [
        {'name': 'Rot1', 'type': 'float', 'value': 0},
        {'name': 'Rot2', 'type': 'float', 'value': 0},
        {'name': 'Rot3', 'type': 'float', 'value': 0}
    ]},

]

class specWrangler(wranglerWidget):
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.sigStart.emit)
        self.ui.pauseButton.clicked.connect(self.pause)
        self.ui.stopButton.clicked.connect(self.stop)
        self.ui.continueButton.clicked.connect(self.cont)

        self.tree = ParameterTree()
        self.parameters = Parameter.create(
            name='spec_wrangler', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.tree)
        self.parameters.child('spec_file_browse').sigActivated.connect(
            self.set_spec_file
        )
        self.parameters.child('image_dir_browse').sigActivated.connect(
            self.set_image_dir
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        self.scan_number = 0
        self.timeout = 5
        self.parameters.sigTreeStateChanged.connect(self.setup)
        self.thread = specThread(
            self.command_queue, 
            self.sphere_args, 
            self.fname, 
            self.file_lock, 
            self.scan_name, 
            0, {}, {}, None, 5, self
        )
        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.sigUpdateFile.emit)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.setup()

    def setup(self):
        self.thread.mp_inputs.update(self._get_mp_inputs())
        self.thread.lsf_inputs.update(self._get_lsf_inputs())
        self.scan_number = self.parameters.child('Scan Number').value()
        self.scan_name = 'scan' + str(self.scan_number).zfill(2)
        self.thread.scan_name = self.scan_name
        self.thread.scan_number = self.scan_number
        self.thread.img_dir = self.parameters.child('Image Directory').value()
        self.timeout = self.parameters.child('Timeout').value()
        self.thread.timeout = self.parameters.child('Timeout').value()

    def pause(self):
        if self.thread.isRunning():
            self.command_queue.put('pause')

    def cont(self):
        if self.thread.isRunning():
            self.command_queue.put('continue')

    def stop(self):
        if self.thread.isRunning():
            self.command_queue.put('stop')
    
    def set_spec_file(self):
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Spec File').setValue(fname)
    
    def set_image_dir(self):
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('Image Directory').setValue(dname)
    
    def set_poni_file(self):
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Calibration PONI File').setValue(fname)
    
    def _get_mp_inputs(self):
        mp_inputs = OrderedDict(
            rotations = {
                "rot1": None,
                "rot2": None,
                "rot3": None
            },
            calib_rotations = {
                "rot1": 0,
                "rot2": 0,
                "rot3": 0
            },
            poni_file = None,
            spec_dict = {}
        )
        rot_mot = self.parameters.child('Rotation Motors')
        for child in rot_mot:
            if child.value() == "":
                mp_inputs['rotations'][child.name().lower()] = None
            else:
                mp_inputs['rotations'][child.name().lower()] = child.value()
        
        cal_rot = self.parameters.child('Calibration Angles')
        for child in cal_rot:
            if child.value() == 0:
                pass
            else:
                mp_inputs['calib_rotations'][child.name().lower()] = child.value()
        
        mp_inputs['poni_file'] = self.parameters.child(
                                     'Calibration PONI File').value()

        return mp_inputs

    def _get_lsf_inputs(self):
        dirname, fname = os.path.split(self.parameters.child('Spec File').value())
        lsf_inputs = OrderedDict(
            spec_file_path=dirname,
            spec_file_name=fname
        )

        return lsf_inputs

    def enabled(self, enable):
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)
                

class specThread(wranglerThread):
    showLabel = Qt.QtCore.Signal(str)
    def __init__(
            self, 
            command_queue, 
            sphere_args, 
            fname, 
            file_lock,
            scan_name, 
            scan_number,
            mp_inputs, 
            lsf_inputs,
            img_dir, 
            timeout,
            parent=None):
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)
        self.scan_name = scan_name
        self.scan_number = scan_number
        self.mp_inputs = mp_inputs
        self.lsf_inputs = lsf_inputs
        self.img_dir = img_dir
        self.timeout = timeout

    def run(self):
        process = specProcess(
            self.command_q, 
            self.signal_q, 
            self.sphere_args, 
            self.scan_name,
            self.scan_number,
            self.fname, 
            self.file_lock,
            self.lsf_inputs, 
            self.mp_inputs,
            self.img_dir,
            self.timeout
        )
        process.start()
        last = False
        while True:
            if not self.input_q.empty():
                command = self.input_q.get()
                print(command)
                self.command_q.put(command)
            if not self.signal_q.empty():
                signal, data = self.signal_q.get()
                if signal == 'update':
                    self.sigUpdate.emit(data)
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    self.sigUpdateFile.emit(self.fname)
                elif signal == 'TERMINATE':
                    last = True
            if last:
                break

        process.join()
    

class specProcess(wranglerProcess):
    def __init__(self, command_q, signal_q, sphere_args, scan_name, 
                 scan_number, fname, file_lock, lsf_inputs, mp_inputs, img_dir, timeout):
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock)
        self.lsf_inputs = lsf_inputs
        self.mp_inputs = mp_inputs
        self.scan_name = scan_name
        self.scan_number = scan_number
        self.img_dir = img_dir
        self.specFile = {}
        self.user = None
        self.spec_name = None
        self.timeout = timeout
    
    def run(self):
        sphere = EwaldSphere(self.scan_name, **self.sphere_args)
        with self.file_lock:
            with catch(self.fname, 'a') as file:
                sphere.save_to_h5(file, replace=True)
                self.signal_q.put(('new_scan', None))
        
        # Operation instantiated within process to avoid conflicts with locks
        make_poni = MakePONI()
        make_poni.inputs.update(self.mp_inputs)

        # Operation instantiated within process to avoid conflicts with locks
        spec_reader = LoadSpecFile()
        spec_reader.inputs.update(self.lsf_inputs)

        i = 0
        pause = False
        start = time.time()
        while True:
            if not self.command_q.empty() or pause:
                command = self.command_q.get()
                print(command)
                if command == 'stop':
                    break
                elif command == 'continue':
                    pause = False
                elif command == 'pause':
                    pause = True
                    continue
            try:
                flag, data = self.wrangle(i, spec_reader, make_poni)
            except (KeyError, FileNotFoundError, AttributeError, ValueError) as e:
                print(type(e))
                print(e.args)
                traceback.print_tb(e.__traceback__)
                elapsed = time.time() - start
                if elapsed > self.timeout:
                    self.signal_q.put(('message', "Timeout occurred"))
                    self.signal_q.put(('TERMINATE', None))
                    break
                else:
                    continue
            start = time.time()

            if flag == 'image':
                idx, map_raw, scan_info, poni = data
                arch = EwaldArch(
                    idx, map_raw, PONI.from_yamdict(poni), scan_info=scan_info
                )
                sphere.add_arch(
                    arch=arch.copy(), calculate=True, update=True, get_sd=True, 
                    set_mg=False
                )
                with self.file_lock:
                    with catch(self.fname, 'a') as file:
                        sphere.save_to_h5(file, arches=[idx], data_only=True, replace=False)
                self.signal_q.put(('update', idx))
                i += 1
            
            elif flag == 'TERMINATE' and data is None:
                self.signal_q.put(('TERMINATE', None))
                break


    def wrangle(self, i, spec_reader, make_poni):
        self.signal_q.put(('message', f'Checking for {i}'))

        # image file names formed as predictable pattern
        # reads in spec data file
        self.specFile = spec_reader.run()

        if self.user is None:
            self.user = self.specFile['header']['meta']['User']
        if self.spec_name is None:
            self.spec_name = self.specFile['header']['meta']['File'][0]

        raw_file = self._get_raw_path(i)

        if self.scan_number in self.specFile['scans'].keys():
            image_meta = self.specFile['scans']\
                                [self.scan_number].loc[i].to_dict()
        
        else:
            image_meta = self.specFile['current_scan'].loc[i].to_dict()
        make_poni.inputs['spec_dict'] = copy.deepcopy(image_meta)
        poni = copy.deepcopy(make_poni.run())
        arr = self.read_raw(raw_file)
        self.signal_q.put(('message', f'Image {i} wrangled'))

        return 'image', (i, arr, image_meta, poni)

    def _get_raw_path(self, i):
        im_base = '_'.join([
            self.user,
            self.spec_name,
            'scan' + str(self.scan_number),
            str(i).zfill(4)
        ])
        return os.path.join(self.img_dir, im_base + '.raw')
    
    def read_raw(self, file, mask=True):
        with open(file, 'rb') as im:
            arr = np.fromstring(im.read(), dtype='int32')
            arr = arr.reshape((195, 487))
            if mask:
                for i in range(0, 10):
                    arr[:,i] = -2.0
                for i in range(477, 487):
                    arr[:,i] = -2.0
            return arr.T



    

