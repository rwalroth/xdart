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
import multiprocessing as mp

# Other imports
import numpy as np
from paws.operations.SPEC import LoadSpecFile, MakePONI
from paws.containers import PONI
from paws.plugins.ewald import EwaldSphere, EwaldArch
from paws.pawstools import catch_h5py_file as catch

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .liveSpecUI import Ui_Form
from .....gui.gui_utils import NamedActionParameter, commandLine
from .....pySSRL_bServer.watcher import Watcher
from .....pySSRL_bServer.helper_funcs import get_from_pdi
from .....pySSRL_bServer.bServer_funcs import specCommand

params = [
    {'name': 'Image Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_dir_browse', title= 'Browse...'),
    {'name': 'PDI Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='pdi_dir_browse', title= 'Browse...'),
    {'name': 'File Types', 'type': 'str', 'default': "raw, pdi"},
    {'name': 'Polling Period', 'type': 'float', 'limits': [0.01, 100], 'default': 0.1},
    {'name': 'Calibration PONI File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='poni_file_browse', title= 'Browse...'),
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

class liveSpecWrangler(wranglerWidget):
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, fname, file_lock, parent=None):
        super().__init__(fname, file_lock, parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.sigStart.emit)
        self.ui.stopButton.clicked.connect(self.stop_watching)
        self.specCommandLine = commandLine(self)
        self.specCommandLine.send_command = self.send_command
        self.ui.commandLayout.addWidget(self.specCommandLine)
        self.buttonSend = QtWidgets.QPushButton(self)
        self.buttonSend.setText('Send')
        self.buttonSend.clicked.connect(self.send_command)
        self.ui.commandLayout.addWidget(self.buttonSend)
        self.commands = ['']
        self.current = -1
        self.keep_trying = True

        self.tree = ParameterTree()
        self.parameters = Parameter.create(
            name='live_spec_wrangler', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.tree)
        self.parameters.child('image_dir_browse').sigActivated.connect(
            self.set_image_dir
        )
        self.parameters.child('pdi_dir_browse').sigActivated.connect(
            self.set_pdi_dir
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        self.parameters.sigTreeStateChanged.connect(self.update)
        self.showLabel.connect(self.ui.specLabel.setText)
        
        self.thread = liveSpecThread(
            command_queue=self.command_queue, 
            sphere_args=self.sphere_args, 
            fname=self.fname, 
            file_lock=self.file_lock,
            mp_inputs=self._get_mp_inputs(),
            img_dir=self.parameters.child('Image Directory').value(),
            pdi_dir=self.parameters.child('PDI Directory').value(),
            filetypes=self.parameters.child('File Types').value().split(),
            pollingperiod=self.parameters.child('Polling Period').value(),
            parent=self
        )
        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.update_file)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.setup()
    
    def setup(self):
        self.thread.sphere_args.update(self.sphere_args)
        self.thread.fname = self.fname
        self.thread.mp_inputs.update(self._get_mp_inputs())
        self.thread.img_dir = self.parameters.child('Image Directory').value()
        self.thread.pdi_dir = self.parameters.child('PDI Directory').value()
        self.thread.filetypes = self.parameters.child('File Types').value().split()
        self.thread.set_queues() 
        self.thread.pollingperiod = self.parameters.child('Polling Period').value()
    
    def send_command(self):
        command = self.specCommandLine.text()
        if not (command.isspace() or command == ''):
            specCommand(command, queue=True)
        commandLine.send_command(self.specCommandLine)
    
    def set_image_dir(self):
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('Image Directory').setValue(dname)
    
    def set_pdi_dir(self):
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('PDI Directory').setValue(dname)
    
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
    
    def update_file(self, name):
        self.scan_name = name
        self.sigUpdateFile.emit(name)

    def enabled(self, enable):
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)
    
    def stop_watching(self):
        self.command_queue.put('stop')
    

class liveSpecThread(wranglerThread):
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, 
            command_queue, 
            sphere_args, 
            fname, 
            file_lock,
            mp_inputs,
            img_dir,
            pdi_dir,
            filetypes,
            pollingperiod,
            parent=None):
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)
        self.sphere_args = sphere_args
        self.mp_inputs = mp_inputs
        self.img_dir = img_dir
        self.pdi_dir = pdi_dir
        self.filetypes = filetypes
        self.queues = {fp: mp.Queue() for fp in filetypes}
    
    def set_queues(self):
        for _, q in self.queues.items():
            self._empty_q(q)
        self.queues = {fp: mp.Queue() for fp in self.filetypes}
        
    
    def run(self):   
        watcher = Watcher( # Process
            watchPaths=[
                self.img_dir,
                self.pdi_dir,
            ],
            filetypes=self.filetypes,
            pollingPeriod=self.pollingperiod,
            queues=self.queues,
            command_q = self.command_q,
            daemon=True
        )
        integrator = liveSpecProcess(
            command_q=self.command_q, 
            signal_q=self.signal_q, 
            sphere_args=self.sphere_args, 
            fname=self.fname, 
            file_lock=self.file_lock, 
            queues=self.queues, 
            mp_inputs=self.mp_inputs
        )
        last=False
        integrator.start()
        watcher.start()
        while True:
            if not self.input_q.empty():
                command = self.input_q.get()
                print(command)
                if command == 'stop':
                    self.command_q.put(command)
            if not self.signal_q.empty():
                signal, data = self.signal_q.get()
                if signal == 'update':
                    self.sigUpdate.emit(data)
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    self.scan_name = data
                    self.sigUpdateFile.emit(self.scan_name)
                elif signal == 'TERMINATE':
                    last = True
            if last:
                break
        for _, q in self.queues.items():
            self._empty_q(q)
        self._empty_q(self.signal_q)
        self._empty_q(self.command_q)
        watcher.join()
        integrator.join()
    
    def _empty_q(self, q):
        while not q.empty():
            _ = q.get()



class liveSpecProcess(wranglerProcess):
    def __init__(self, command_q, signal_q, sphere_args, fname, file_lock, 
                 queues, mp_inputs):
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock)
        self.queues = queues
        self.mp_inputs = mp_inputs
        self.scan_number = None
    
    def run(self):
        self.scan_number = None
        make_poni = MakePONI()
        make_poni.inputs.update(self.mp_inputs)
        # image file names formed as predictable pattern
        while True:
            for key, q in self.queues.items():
                added = q.get()
                print(added)
                self.signal_q.put(('message', added))
                if added == 'BREAK':
                    self.signal_q.put(('TERMINATE', None))
                    break
                elif key == 'pdi':
                    pdi_file = added
                elif key == 'raw':
                    raw_file = added
            
            scan_number, i = self.parse_file(raw_file)
            if scan_number != self.scan_number:
                self.scan_number = scan_number
                sphere = EwaldSphere(
                    name='scan' + str(self.scan_number).zfill(2),
                    **self.sphere_args
                )
                with self.file_lock:
                    with catch(self.fname, 'a') as file:
                        sphere.save_to_h5(file)
                self.signal_q.put(('new_scan', sphere.name))
            while True:
                # Looks for relevant data, loops until it is found or a
                # timeout occurs
                try:
                    arr = self.read_raw(raw_file)

                    image_meta = self.read_pdi(pdi_file)

                    make_poni.inputs['spec_dict'] = copy.deepcopy(image_meta)

                    poni = copy.deepcopy(make_poni.run())
                    break

                except (KeyError, FileNotFoundError, AttributeError, ValueError) as e:
                    print(type(e))
                    traceback.print_tb(e.__traceback__)
                    
            arch = EwaldArch(
                i, arr, PONI.from_yamdict(poni), scan_info=image_meta
            )
            sphere.add_arch(
                arch=arch.copy(), calculate=True, update=True, 
                get_sd=True, set_mg=False
            )
            with self.file_lock:
                with catch(self.fname, 'a') as file:
                    sphere.save_to_h5(
                        file, arches=[i], data_only=True, replace=False
                    )
            self.signal_q.put(('update', i))
    
    def parse_file(self, path):
        _, name = os.path.split(path)
        name = name.split('.')[0]
        args = name.split('_')
        scan_name = args[-2]
        scan_number = int(scan_name[4:])
        idx = int(args[-1])
        return scan_number, idx
    
    def read_pdi(self, pdi_file):
        counters, motors = get_from_pdi(pdi_file)
        image_meta = {}
        image_meta.update(counters)
        image_meta.update(motors)
        return image_meta
    
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
