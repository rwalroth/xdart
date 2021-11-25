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

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from xdart.modules.spec import LoadSpecFile, MakePONI
from xdart.utils.containers import PONI
from xdart.modules.ewald import EwaldArch, EwaldSphere
from xdart.utils import catch_h5py_file as catch
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .liveSpecUI import Ui_Form
from ....gui_utils import NamedActionParameter
from ....widgets import commandLine
from xdart.modules.pySSRL_bServer.watcher import Watcher
from xdart.modules.pySSRL_bServer.bServer_funcs import specCommand
from xdart.utils import get_meta_from_pdi

from .spec_wrangler import DETECTOR_DICT, MaskWidget

params = [
    {'name': 'Image Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_dir_browse', title= 'Browse...'),
    {'name': 'PDI Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='pdi_dir_browse', title= 'Browse...'),
    {'name': 'File Types', 'type': 'str', 'default': "raw, pdi"},
    {'name': 'Polling Period', 'type': 'float', 'limits': [0.01, 100], 'default': 0.1},
    {'name': 'Calibration PONI File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='poni_file_browse', title= 'Browse...'),
    {'name': 'Out Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='out_dir_browse', title= 'Browse...'),
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
    {'name': 'Detector', 'type': 'list', 'values': [
            "Pilatus100k"
        ],
     'value':'Pilatus100k'},
    NamedActionParameter(name='set_mask', title= 'Set mask...'),

]

class liveSpecWrangler(wranglerWidget):
    """Widget for controlling spec and reading in data as it is being
    collected. 
    
    attributes:
        fname: str, file path for data storage
        file_lock: multiprocessing Condition, multiprocess safe lock
            to ensure only one process accesses data file at a time.
        ui: Qt Ui_Form, holds all gui widgets made with qtdesigner
        specCommandLine: commandLine, widget to simulate terminal line
        commands: list, set of previously entered commands
        command_queue: Queue, used to send commands to thread
        current: int, index of current command
        file_lock, mp.Condition, process safe lock for file access
        fname: str, path to data file
        keep_trying: bool, unused
        parameters: pyqtgraph Parameter, set of parameters for
            controling widget
        scan_name: str, current scan name, used to handle syncing data
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        tree: pyqtgraph ParameterTree, tree which holds parameters
        thread: liveSpecThread, thread which controls processes to
            watch for new data and to run integration
    
    methods:
        enabled: enables or disables all gui elements.
        send_command: sends command through to spec via the bServer
        set_fname: Method to safely change file name
        set_image_dir: sets the image directory
        set_out_dir: sets the output directory for new data files
        set_pdi_dir: sets the pdi directory
        set_poni_file: sets the calibration poni file
        setup: sets up the thread attribute to ensure all parameters
            are properly synced.
        stop_watching: end the watcher process.
        update_file: update the current scan name and file path 
            attributes
    
    signals:
        finished: Should be connected to thread.finished signal
        showLabel: str, text to be set as specLabel.
        sigStart: Tells tthetaWidget to start the thread and prepare
            for new data.
        sigUpdateData: int, signals a new arch has been added.
        sigUpdateFile: (str, str), sends new scan_name and file name
            to tthetaWidget.
    """
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, fname, file_lock, parent=None):
        """fname: str, path to data file. 
        file_lock: Condition, process safe lock.
        """
        super().__init__(fname, file_lock, parent)
        
        # Setup gui elements
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
        self.showLabel.connect(self.ui.specLabel.setText)

        # Setup the parameter tree
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
        self.parameters.child('out_dir_browse').sigActivated.connect(
            self.set_out_dir
        )
        self.parameters.sigTreeStateChanged.connect(self.update)
        
        # Setup the liveSpecThread
        self.thread = liveSpecThread(
            command_queue=self.command_queue, 
            sphere_args=self.sphere_args, 
            fname=self.fname, 
            file_lock=self.file_lock,
            mp_inputs=self._get_mp_inputs(),
            img_dir=self.parameters.child('Image Directory').value(),
            pdi_dir=self.parameters.child('PDI Directory').value(),
            out_dir=self.parameters.child('Out Directory').value(),
            filetypes=self.parameters.child('File Types').value().split(),
            pollingperiod=self.parameters.child('Polling Period').value(),
            parent=self
        )
        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.update_file)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.setup()

        self.mask = None
        self.mask_widget = MaskWidget()
        key = self.parameters.child("Detector").value()
        data = np.zeros(DETECTOR_DICT[key]["shape"])
        data[0, 0] = 1
        self.mask_widget.set_data(data.T)
        self.mask_widget.hide()
        self.parameters.child('set_mask').sigActivated.connect(
            self.launch_mask_widget
        )

        self.mask_widget.newMask.connect(self.set_mask)

        self.setup()
    
    def setup(self):
        """Syncs all attributes of liveSpecThread with parameters
        """
        self.thread.sphere_args.update(self.sphere_args)
        self.thread.fname = self.fname
        self.thread.mp_inputs.update(self._get_mp_inputs())
        self.thread.img_dir = self.parameters.child('Image Directory').value()
        self.thread.pdi_dir = self.parameters.child('PDI Directory').value()
        self.thread.out_dir = self.parameters.child('Out Directory').value()
        self.thread.filetypes = self.parameters.child('File Types').value().split()
        self.thread.set_queues() 
        self.thread.pollingperiod = self.parameters.child('Polling Period').value()
        self.thread.mask = self.mask
    
    def send_command(self):
        """Sends command in command line to spec, and calls
        commandLine send_command method to add command to list of
        commands.
        """
        command = self.specCommandLine.text()
        if not (command.isspace() or command == ''):
            try:
                specCommand(command, queue=True)
            except Exception as e:
                print(e)
                print(f"Command '{command}' not sent")
        
        commandLine.send_command(self.specCommandLine)
    
    def set_image_dir(self):
        """Opens file dialogue and sets the image directory
        """
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('Image Directory').setValue(dname)
    
    def set_pdi_dir(self):
        """Opens file dialogue and sets the pdi directory
        """
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('PDI Directory').setValue(dname)
    
    def set_out_dir(self):
        """Opens file dialogue and sets the output directory
        """
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('Out Directory').setValue(dname)
    
    def set_poni_file(self):
        """Opens file dialogue and sets the calibration file
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Calibration PONI File').setValue(fname)

    def set_mask(self, idx, mask):
        self.mask = np.arange(mask.size)[mask.ravel() == 1]
        self.thread.mask = self.mask

    def launch_mask_widget(self):
        key = self.parameters.child("Detector").value()
        data = np.zeros(DETECTOR_DICT[key]["shape"])
        data[0, 0] = 1
        if self.mask is not None:
            _mask = np.zeros_like(data)
            _mask.ravel()[self.mask] = 1
            self.mask_widget.set_data(data.T, base=_mask)
        else:
            self.mask_widget.set_data(data.T)
        self.mask_widget.show()
    
    def _get_mp_inputs(self):
        """Organizes inputs for MakePONI from parameters.
        """
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
    
    def update_file(self, name, fname):
        """updates the current scan name and file path attributes, emits
        them back to main widget.
        
        args:
            name: str, scan name
            fname: str, path to data file
        """
        self.scan_name = name
        self.fname = fname
        self.sigUpdateFile.emit(name, fname)

    def enabled(self, enable):
        """Sets tree and start button to enable.
        
        args:
            enable: bool, True for enabled False for disabled.
        """
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)
    
    def stop_watching(self):
        """Sends stop command to thread.
        """
        self.command_queue.put('stop')
    

class liveSpecThread(wranglerThread):
    """Thread for controlling watcher and integrator processes. Watcher
    checks for new data, passes paths on to integrator process for
    integration.
    
    attributes:
        command_q: mp.Queue, queue to send commands to process
        file_lock: mp.Condition, process safe lock for file access
        filetypes: list, file endings to check for in watch folder
        fname: str, path to data file.
        img_dir: str, path to image directory
        mp_inputs: dict, input parameters for MakePONI
        out_dir: str, directory to output scans
        pdi_dir: str, directory for pdi files
        pollingperiod: float, how often to check folder for updates
        queues: dict, dictionary of queues for each filetype
        scan_name: str, name of current scan
        scan_number: int, number of current scan
        input_q: mp.Queue, queue for commands sent from parent
        signal_q: mp.Queue, queue for commands sent from process
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
    
    signals:
        showLabel: str, sends out text to be used in specLabel
    
    methods:
        run: Main method, called by start
        set_queues: empties out queues in self.queues and creates new
            ones
    """
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, 
            command_queue, 
            sphere_args, 
            fname, 
            file_lock,
            mp_inputs,
            img_dir,
            pdi_dir,
            out_dir,
            filetypes,
            pollingperiod,
            parent=None):
        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        file_lock: mp.Condition, process safe lock for file access
        mp_inputs: dict, input parameters for MakePONI
        img_dir: str, path to image directory
        pdi_dir: str, path to pdi directory
        out_dir: str, directory to save scans
        filetypes: list, file types to be watched in watch folder
        pollingperiod: float, how often to check for updates in
            watch folder.
        """
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)
        self.sphere_args = sphere_args
        self.mp_inputs = mp_inputs
        self.img_dir = img_dir
        self.pdi_dir = pdi_dir
        self.out_dir = out_dir
        self.filetypes = filetypes
        self.pollingperiod = pollingperiod
        self.queues = {fp: mp.Queue() for fp in filetypes}
        self.mask = None
    
    def set_queues(self):
        """Empty all current file queues, recreate them based on current
        file types.
        """
        for _, q in self.queues.items():
            self._empty_q(q)
        self.queues = {fp: mp.Queue() for fp in self.filetypes}
        
    
    def run(self):
        """Initializes watcher and integrator processes, and passes
        commands from parent. Also passes updates to parent widget.
        """
        
        # Initialize watcher
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
        
        # Initialize integrator
        integrator = liveSpecProcess(
            command_q=self.command_q, 
            signal_q=self.signal_q, 
            sphere_args=self.sphere_args, 
            fname=self.fname, 
            file_lock=self.file_lock, 
            queues=self.queues, 
            mp_inputs=self.mp_inputs,
            pdi_dir=self.pdi_dir,
            out_dir=self.out_dir,
            global_mask = self.mask
        )
        last=False
        integrator.start()
        watcher.start()
        
        # Main loop
        while True:
            # Check for commands from main thread
            if not self.input_q.empty():
                command = self.input_q.get()
                print(command)
                if command == 'stop':
                    self.command_q.put(command)
            
            # Check for signals from integrator
            if not self.signal_q.empty():
                signal, data = self.signal_q.get()
                if signal == 'update':
                    self.sigUpdate.emit(data)
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    self.scan_name = data[0]
                    self.fname = data[1]
                    self.sigUpdateFile.emit(data[0], data[1])
                elif signal == 'TERMINATE':
                    last = True
            if last:
                break
        
        # Cleanup processes at end of loop.
        for _, q in self.queues.items():
            self._empty_q(q)
        self._empty_q(self.signal_q)
        self._empty_q(self.command_q)
        watcher.join()
        integrator.join()
    
    def _empty_q(self, q):
        """Empty out queues.
        """
        while not q.empty():
            _ = q.get()



class liveSpecProcess(wranglerProcess):
    """Process for integrating scanning area detector data, based on
    pdi files instead of spec files. Otherwise operates very similarly
    to specProcess.
    
    attributes:
        command_q: mp.Queue, queue for commands from parent thread.
        file_lock: mp.Condition, process safe lock for file access
        fname: str, path to data file
        mp_inputs: dict, input parameters for MakePONI
        out_dir: str, path to output directory
        pdi_dir: str, path to pdi directory
        queues: dict, set of queues for updates from watcher
        scan_name: str, name of current scan
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
    
    methods:
        parse_file: Determines scan name and image index from file name
        read_pdi: Reads metadata from pdi file
        read_raw: method for reading in binary .raw files and returning
            data as a numpy array.
        run: Controls flow of integration, checking for commands,
            providing updates, and catching errors.
    """
    def __init__(self, command_q, signal_q, sphere_args, fname, file_lock, 
                 queues, mp_inputs, pdi_dir, out_dir, global_mask):
        """command_q: mp.Queue, queue for commands from parent thread.
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file
        file_lock: mp.Condition, process safe lock for file access
        mp_inputs: dict, input parameters for MakePONI
        pdi_dir: str, path to pdi directory
        out_dir: str, path to output directory
        """
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock)
        self.queues = queues
        self.mp_inputs = mp_inputs
        self.scan_name = None
        self.pdi_dir = pdi_dir
        self.out_dir = out_dir
        self.mask = global_mask
    
    def _main(self):
        """Main method. Takes in file paths from queues fed by watcher,
        reads in the metadata from pdi file and image data from raw
        file. Integrates data and stores it in hdf5 file.
        """
        # TODO: This should be _main not run
        
        # Initialize MakePONI
        self.scan_name = None
        make_poni = MakePONI()
        make_poni.inputs.update(self.mp_inputs)
        
        # Main loop.
        while True:
            # Check queues for new file paths
            for key, q in self.queues.items():
                added = q.get()
                self.signal_q.put(('message', added))
                if added == 'BREAK':
                    self.signal_q.put(('TERMINATE', None))
                    return
                elif key == 'pdi':
                    pdi_file = added
                elif key == 'raw':
                    raw_file = added
                    print(added)

            # Parse file for scan name
            scan_name, i = self.parse_file(raw_file)
            
            # If new scan has started, create new sphere object
            if scan_name != self.scan_name:
                self.scan_name = scan_name
                sphere = EwaldSphere(
                    name=scan_name,
                    data_file = os.path.join(
                        self.out_dir, scan_name + ".hdf5"
                    ),
                    **self.sphere_args
                )
                sphere.global_mask = self.mask
                sphere.save_to_h5(replace=True)
                self.signal_q.put(('new_scan', 
                                   (sphere.name, sphere.data_file)))
            while True:
                # Looks for relevant data, loops until it is found or a
                # timeout occurs
                try:
                    arr = self.read_raw(raw_file)
                    
                    # Get pdi name from raw name, ensures one for one
                    raw_fname = os.path.basename(raw_file)
                    #pdi_path = os.path.dirname(pdi_file)
                    pdi_file = os.path.join(self.pdi_dir, f'{raw_fname}.pdi') 
                    
                    print(pdi_file)

                    image_meta = self.read_pdi(pdi_file)

                    make_poni.inputs['spec_dict'] = copy.deepcopy(image_meta)

                    poni = copy.deepcopy(make_poni.run())
                    break

                except (KeyError, FileNotFoundError, AttributeError, ValueError) as e:
                    # Handle exceptions related to files not being
                    # ready yet
                    print(type(e))
                    traceback.print_tb(e.__traceback__)
            
            with self.file_lock:
                # Add data to sphere  
                sphere.add_arch(
                    calculate=True, update=True, 
                    get_sd=True, set_mg=False, idx=i, map_raw=arr, 
                    poni=PONI.from_yamdict(poni), scan_info=image_meta
                )
            self.signal_q.put(('update', i))
    
    def parse_file(self, path):
        """Generate a scan name and image index from a file name.
        
        args:
            path: str, path to be parsed
        
        returns:
            scan_name: str, name of the scan
            idx: int, index of image
        """
        _, name = os.path.split(path)
        name = name.split('.')[0]
        args = name.split('_')
        scan_name = '_'.join(args[:-1])
        idx = int(args[-1])
        return scan_name, idx
    
    def read_pdi(self, pdi_file):
        """Gets the metadata from the pdi file. Uses get_meta_from_pdi, but
        returns a single dictionary rather than two.
        
        args:
            pdi_file: str, path for pdi file
        
        returns:
            image_meta: dict, dictionary with metadata
        """
        counters, motors = get_meta_from_pdi(pdi_file)
        image_meta = {}
        image_meta.update(counters)
        image_meta.update(motors)
        return image_meta
    
    def read_raw(self, file, mask=True):
        """Reads in .raw file and returns a numpy array.
        
        args:
            file: str, path to .raw file
            mask: bool, if True clips the edges of the image
        
        returns:
            map_raw: numpy array, image data.
        """
        with open(file, 'rb') as im:
            arr = np.fromstring(im.read(), dtype='int32')
            arr = arr.reshape((195, 487))
            if mask:
                for i in range(0, 10):
                    arr[:,i] = -2.0
                for i in range(477, 487):
                    arr[:,i] = -2.0
            return arr.T
