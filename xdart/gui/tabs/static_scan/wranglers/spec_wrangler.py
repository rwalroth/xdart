# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
import copy
import time
import inspect

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from xdart.modules.ewald import EwaldArch, EwaldSphere
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .ui.specUI import Ui_Form
from ....gui_utils import NamedActionParameter
from xdart.utils import read_image_file, get_image_meta_data

from ....widgets import commandLine
from xdart.modules.pySSRL_bServer.bServer_funcs import specCommand

debug = True

def_img_fname = '/Users/v/SSRL_Data/RDA/static_det_test_data/test_xfc_data/images/images_0001.tif'
poni = '/Users/v/SSRL_Data/RDA/static_det_test_data/test_xfc_data/test_xfc.poni'

params = [
    # {'name': 'Image File', 'type': 'str', 'default': img_fname},
    {'name': 'Image File', 'type': 'str', 'value': def_img_fname},
    NamedActionParameter(name='image_file_browse', title='Browse...'),
    # {'name': 'PONI File', 'type': 'str', 'default': poni},
    {'name': 'Single Image', 'type': 'bool', 'value': False},
    {'name': 'PONI File', 'type': 'str', 'value': poni},
    NamedActionParameter(name='poni_file_browse', title='Browse...'),
    {'name': 'Grazing Incidence', 'type': 'bool', 'value': False},
    {'name': 'Theta Motor', 'type': 'str', 'value': 'th'},
    {'name': 'Timeout', 'type': 'float', 'value': 1},
]


class specWrangler(wranglerWidget):
    """Widget for integrating data associated with spec file. Can be
    used "live", will continue to poll data folders until image data
    and corresponding spec data are available.
    
    attributes:
        command_queue: Queue, used to send commands to thread
        file_lock, mp.Condition, process safe lock for file access
        fname: str, path to data file
        parameters: pyqtgraph Parameter, stores parameters from user
        scan_name: str, current scan name, used to handle syncing data
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        thread: wranglerThread or subclass, QThread for controlling
            processes
        timeout: int, how long before thread stops looking for new
            data.
        tree: pyqtgraph ParameterTree, stores and organizes parameters
        ui: Ui_Form from qtdesigner
    
    methods:
        cont, pause, stop: functions to pass continue, pause, and stop
            commands to thread via command_queue 
        enabled: Enables or disables interactivity
        set_image_dir: sets the image directory
        set_poni_file: sets the calibration poni file
        set_spec_file: sets the spec data file
        set_fname: Method to safely change file name
        setup: Syncs thread parameters prior to starting
    
    signals:
        finished: Connected to thread.finished signal
        sigStart: Tells tthetaWidget to start the thread and prepare
            for new data.
        sigUpdateData: int, signals a new arch has been added.
        sigUpdateFile: (str, str, bool, str, bool), sends new scan_name, file name
            GI flag (grazing incidence), theta motor for GI, and
             single_image flag to static_scan_Widget.
        sigUpdateGI: bool, signals the grazing incidence condition has changed.
        showLabel: str, connected to thread showLabel signal, sets text
            in specLabel
    """
    showLabel = Qt.QtCore.Signal(str)

    def __init__(self, fname, file_lock, parent=None):
        """fname: str, file path
        file_lock: mp.Condition, process safe lock
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        super().__init__(fname, file_lock, parent)
        self.img_fname = ''
        self.img_dir = '.'
        self.img_ext = 'tif'
        self.first_img = 1

        # Setup gui elements
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.sigStart.emit)
        self.ui.pauseButton.clicked.connect(self.pause)
        self.ui.stopButton.clicked.connect(self.stop)
        self.ui.continueButton.clicked.connect(self.cont)

        # SpecCommand Line
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

        # Setup parameter tree
        self.tree = ParameterTree()
        self.parameters = Parameter.create(
            name='spec_wrangler', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.tree)

        # Wire signals from parameter tree based buttons
        self.parameters.child('image_file_browse').sigActivated.connect(
            self.set_image_file
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )

        # Set attributes
        self.single_img = self.parameters.child('Single Image').value()
        self.poni_file = self.parameters.child('PONI File').value()
        self.timeout = self.parameters.child('Timeout').value()
        self.gi = self.parameters.child('Grazing Incidence').value()
        self.th_mtr = self.parameters.child('Theta Motor').value()
        self.parameters.sigTreeStateChanged.connect(self.setup)

        # Setup thread
        self.thread = specThread(
            self.command_queue,
            self.sphere_args,
            self.fname,
            self.file_lock,
            self.scan_name,
            self.single_img,
            self.poni_file,
            self.img_fname,
            self.img_dir,
            self.img_ext,
            self.first_img,
            self.timeout,
            self.gi,
            self.th_mtr,
            self
        )
        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.sigUpdateFile.emit)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.thread.sigUpdateArch.connect(self.sigUpdateArch.emit)
        self.thread.sigUpdateGI.connect(self.sigUpdateGI.emit)
        self.setup()

    def setup(self):
        """Sets up the child thread, syncs all parameters.
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        self.img_fname = self.parameters.child('Image File').value()
        self.thread.img_fname = self.img_fname
        print(f'spec_wrangler > img_fname: {self.img_fname}')

        img_dir, scan_name, img_ext, first_img = self.split_image_name()
        self.img_dir, self.scan_name, self.img_ext = img_dir, scan_name, img_ext
        self.thread.img_dir, self.thread.scan_name, self.thread.img_ext = img_dir, scan_name, img_ext
        self.thread.first_img = self.first_img = first_img
        print(f'spec_wrangler > img_dir, scan_name, img_ext : {self.img_dir} {self.scan_name} {self.img_ext}')

        self.poni_file = self.parameters.child('PONI File').value()
        self.thread.poni_file = self.poni_file

        self.thread.scan_name = self.scan_name
        self.single_img = self.parameters.child('Single Image').value()
        print(f'spec_wrangler > setup: first_img = {self.first_img}')
        if (self.first_img is None) and (self.img_ext not in ['.h5', 'hdf5']):
            self.single_img = True
        self.thread.single_img = self.single_img

        self.fname = os.path.join(self.img_dir, self.scan_name + '.hdf5')
        self.thread.fname = self.fname

        self.timeout = self.parameters.child('Timeout').value()
        self.thread.timeout = self.timeout

        self.gi = self.parameters.child('Grazing Incidence').value()
        self.thread.gi = self.gi

        self.th_mtr = self.parameters.child('Theta Motor').value()
        self.thread.th_mtr = self.th_mtr

        self.thread.file_lock = self.file_lock
        self.thread.sphere_args = self.sphere_args

    def send_command(self):
        """Sends command in command line to spec, and calls
        commandLine send_command method to add command to list of
        commands.
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        command = self.specCommandLine.text()
        if not (command.isspace() or command == ''):
            try:
                specCommand(command, queue=True)
            except Exception as e:
                print(e)
                print(f"Command '{command}' not sent")

        commandLine.send_command(self.specCommandLine)

    def pause(self):
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        if self.thread.isRunning():
            self.command_queue.put('pause')

    def cont(self):
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        if self.thread.isRunning():
            self.command_queue.put('continue')

    def stop(self):
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        if self.thread.isRunning():
            self.command_queue.put('stop')

    def set_image_file(self):
        """Opens file dialogue and sets the spec data file
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Image File').setValue(fname)
        self.img_fname = fname

    def set_poni_file(self):
        """Opens file dialogue and sets the calibration file
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('PONI File').setValue(fname)
        self.poni_file = fname

    def split_image_name(self):
        """Splits image filename to get directory, file root and extension

        Arguments:
            fname {str} -- full image file name with path
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        directory = os.path.dirname(self.img_fname)
        root, ext = os.path.splitext(os.path.basename(self.img_fname))

        try:
            first_img = root[root.rindex('_')+1:]
            first_img = int(first_img)
            root = root[:root.rindex('_')]
        except ValueError:
            first_img = None

        return directory, root, ext, first_img

    def enabled(self, enable):
        """Sets tree and start button to enable.

        args:
            enable: bool, True for enabled False for disabled.
        """
        if debug:
            print(f'- spec_wrangler > specWrangler: {inspect.currentframe().f_code.co_name} -')
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)


class specThread(wranglerThread):
    """Thread for controlling the specProcessor process. Receives
    manages a command and signal queue to pass commands from the main
    thread and communicate back relevant sisingle_img=self.single_img,

    attributes:
        command_q: mp.Queue, queue to send commands to process
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        fname: str, path to data file.
        img_fname: str, path to image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        poni_file: str, Poni File name
        input_q: mp.Queue, queue for commands sent from parent
        signal_q: mp.Queue, queue for commands sent from process
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        timeout: float or int, how long to continue checking for new
            data.

    signals:
        showLabel: str, sends out text to be used in specLabel

    methods:
        run: Main method, called by start
    """
    showLabel = Qt.QtCore.Signal(str)

    def __init__(
            self,
            command_queue,
            sphere_args,
            fname,
            file_lock,
            scan_name,
            single_img,
            poni_file,
            img_fname,
            img_dir,
            img_ext,
            first_img,
            timeout,
            gi,
            th_mtr,
            parent=None):
        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        single_img: bool, True if there is only one image
        poni_file: str, poni file name
        img_fname: str, path to input image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        timeout: float or int, how long to continue checking for new
            data.
        gi: bool, grazing incidence flag to determine if pyGIX is to be used
        th_mtr: float, incidence angle
        """
        if debug:
            print(f'- spec_wrangler > specThread: {inspect.currentframe().f_code.co_name} -')
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)
        self.scan_name = scan_name
        self.single_img = single_img
        self.poni_file = poni_file
        self.img_fname = img_fname
        self.img_dir = img_dir
        self.img_ext = img_ext
        self.first_img = first_img
        self.timeout = timeout
        self.gi = gi
        self.th_mtr = th_mtr

    def run(self):
        """Initializes specProcess and watches for new commands from
        parent or signals from the process.
        """
        if debug:
            print(f'- spec_wrangler > specThread: {inspect.currentframe().f_code.co_name} -')
        process = specProcess(
            self.command_q,
            self.signal_q,
            self.sphere_args,
            self.scan_name,
            self.single_img,
            self.fname,
            self.file_lock,
            self.poni_file,
            self.img_fname,
            self.img_dir,
            self.img_ext,
            self.first_img,
            self.timeout,
            self.gi,
            self.th_mtr,
        )
        process.start()
        last = False
        # Main loop
        while True:
            # Check for new commands
            if not self.input_q.empty():
                command = self.input_q.get()
                print(command)
                self.command_q.put(command)

            # Check for new updates
            if not self.signal_q.empty():
                signal, data = self.signal_q.get()
                if signal == 'update':
                    self.sigUpdate.emit(data)
                elif signal == 'updateArch':
                    self.sigUpdateArch.emit(data)
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    print(f'\nspec_wrangler > news_scan, single_img: {self.scan_name}, {self.single_img}\n')
                    self.sigUpdateFile.emit(self.scan_name, self.fname,
                                            self.gi, self.th_mtr,
                                            self.single_img)
                elif signal == 'TERMINATE':
                    last = True

            # Breaks on signal from process
            if last:
                break

        # Empty queues of any other items after main loop ends.
        self._empty_q(self.signal_q)
        self._empty_q(self.command_q)
        process.join()

    def _empty_q(self, q):
        """Empties out a given queue.
        args:
            q: Queue
        """
        if debug:
            print(f'- spec_wrangler > specThread: {inspect.currentframe().f_code.co_name} -')
        while not q.empty():
            _ = q.get()


class specProcess(wranglerProcess):
    """Process for integrating scanning area detector data. Checks for
    a specified scan in a spec file, and then searches for associated
    raw files. Data is stored with an EwaldSphere object, saving all
    data to an hdf5 file.

    attributes:
        command_q: mp.Queue, queue for commands from parent thread.
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        img_ext : str, extension of image file
        signal_q: queue to place signals back to parent thread.
        fname: str, path to data file
        single_img: bool, True if there is only one image
        poni_file: str, poni file name
        img_fname: str, path to input image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        timeout: float or int, how long to continue checking for new
            data.
        user: str, user name from spec file

    methods:
        _main: Controls flow of integration, checking for commands,
            providing updates, and catching errors.
        read_raw: method for reading in binary .raw files and returning
            data as a numpy array.
        wrangle: Method which handles data loading from files.
    """

    def __init__(self, command_q, signal_q, sphere_args,
                 scan_name, single_img,
                 fname, file_lock, poni_file,
                 img_fname, img_dir, img_ext, first_img, timeout,
                 gi, th_mtr, *args, **kwargs):
        """command_q: mp.Queue, queue for commands from parent thread.
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        scan_name: str, name of current scan
        single_img: bool, True if there is only one image
        fname: str, path to data file
        file_lock: mp.Condition, process safe lock for file access
        poni_file: str, poni file name
        img_dir: str, path to image directory
        timeout: float or int, how long to continue checking for new
            data.
        """
        if debug:
            print(f'- spec_wrangler > specProcess: {inspect.currentframe().f_code.co_name} -')
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock,
                         *args, **kwargs)
        self.poni_file = poni_file
        self.scan_name = scan_name
        self.single_img = single_img
        self.img_fname = img_fname
        self.img_dir = img_dir
        self.img_ext = img_ext
        self.first_img = first_img
        self.user = None
        self.timeout = timeout
        self.gi = gi
        self.th_mtr = th_mtr

    def _main(self):
        """Checks for commands in queue, sends back updates through
        signal queue, and catches errors. Calls wrangle method for
        reading in data, then performs integration.
        """
        if debug:
            print(f'- spec_wrangler > specProcess: {inspect.currentframe().f_code.co_name} -')

        print(f'spec_wrangler > _main: first_img = {self.first_img}')
        if (self.first_img is None) and (self.img_ext not in ['.h5', 'hdf5']):
            self.single_img = True

        # Initialize sphere and save to disk, send update for new scan
        print(f'\nspec_wrangler > self.fname, self.scan_name: {self.fname}, {self.scan_name}')
        print(f'spec_wrangler > self.single_img, self.gi: {self.single_img}, {self.gi}')
        sphere = EwaldSphere(self.scan_name,
                             data_file=self.fname,
                             static=True,
                             gi=self.gi,
                             th_mtr=self.th_mtr,
                             single_img=self.single_img,
                             **self.sphere_args)
        print(f'spec_wrangler: _main: sphere_args = {self.sphere_args}')
        with self.file_lock:
            sphere.save_to_h5(replace=True)
            self.signal_q.put(('new_scan', None))
        print(f'spec_wrangler > sphere name: {sphere.name}\n')

        # Enter main loop
        i = 1
        if not self.single_img:
            i = self.first_img
        pause = False
        start = time.time()
        while True:
            # Check for commands, or wait if paused
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

            # if self.single_img and (i > 1):
            #     self.signal_q.put(('TERMINATE', None))
            #     break

            # Get result from wrangle
            try:
                print(f'wrangle: {i}')
                flag, data = self.wrangle(i)
            # Errors associated with image not yet taken
            except (KeyError, FileNotFoundError, AttributeError, ValueError):
                elapsed = time.time() - start
                if elapsed > self.timeout:
                    self.signal_q.put(('message', "Timeout occurred"))
                    self.signal_q.put(('TERMINATE', None))
                    break
                else:
                    continue
            start = time.time()

            # Unpack data and load into sphere
            # TODO: Test how long integrating vs io takes
            if flag == 'image':
                idx, map_raw, scan_info = data
                arch = EwaldArch(
                    idx, map_raw, poni_file=self.poni_file,
                    scan_info=scan_info, static=True, gi=self.gi,
                    th_mtr=self.th_mtr,
                )

                # integrate image to 1d and 2d arrays
                arch.integrate_1d(**sphere.bai_1d_args)
                arch.integrate_2d(**sphere.bai_2d_args)

                print(f'spec_wrangler: _main: sphere_args = {sphere.bai_1d_args}')
                print(f'spec_wrangler: _main: sphere_args = {sphere.bai_2d_args}')

                # Add arch copy to sphere, save to file
                with self.file_lock:
                    arch_copy = arch.copy()
                    sphere.add_arch(
                        arch=arch_copy, calculate=False, update=True,
                        get_sd=True, set_mg=False, static=True, gi=self.gi,
                        th_mtr=self.th_mtr
                    )
                    sphere.save_to_h5(data_only=True, replace=False)

                self.signal_q.put(('message', f'Image {i} integrated'))
                self.signal_q.put(('update', idx))
                if self.single_img:
                    self.signal_q.put(('TERMINATE', None))
                    print(f'spec_wrangler: _main: Breaking')
                    break

                # arch_data = {
                #     'idx': arch_copy.idx,
                #     'map_raw': arch_copy.map_raw,
                #     'mask': arch_copy.mask,
                #     'scan_info': arch_copy.scan_info,
                #     'poni_file': arch_copy.poni_file,
                #     'map_norm': arch_copy.map_norm,
                #     'int_1d': arch_copy.int_1d,
                #     'int_2d': arch_copy.int_2d
                # }
                # self.signal_q.put(('updateArch', arch_data))

                i += 1

            # Check if terminate signal sent
            elif flag == 'TERMINATE' and data is None:
                self.signal_q.put(('TERMINATE', None))
                break

        # If loop ends, signal terminate to parent thread.
        self.signal_q.put(('TERMINATE', None))

    def wrangle(self, i):
        """Method for reading in data from raw files and spec file.

        args:
            i: int, index of image to check

        returns:
            flag: str, signal for what kind of data to expect.
            data: tuple (int, numpy array, dict, dict), the
                index of the data, raw image array, metadata
                dict associated with the image.
        """
        if debug:
            print(f'- spec_wrangler > specProcess: {inspect.currentframe().f_code.co_name} -')
        self.signal_q.put(('message', f'Checking for {i}'))

        # Construct raw_file path from attributes and index
        # if self.img_ext not in ['.h5', '.hdf5', '.mar3450']:
        if (not self.single_img) and (self.img_ext not in ['.h5', '.hdf5']):
            image_file = self._get_image_path(i)
        else:
            image_file = self.img_fname
        print(f'\nspec_wrangler > Image File Name: {image_file}')

        # Read raw file into numpy array
        arr = read_image_file(image_file, im=i-1)

        meta_file = image_file[:-3] + 'txt'
        if os.path.exists(meta_file):
            image_meta = get_image_meta_data(meta_file, BL='11-3')
        else:
            image_meta = {}
        print(f'spec_wrangler > Image Meta Data: {image_meta}')

        self.signal_q.put(('message', f'Image {i} wrangled'))

        return 'image', (i, arr, image_meta)

    def _get_image_path(self, i):
        """Creates raw path name from attributes, following spec
        convention.

        args:
            i: int, index of image

        returns:
            image_file: str, absolute path to image file.
        """
        if debug:
            print(f'- spec_wrangler > specProcess: {inspect.currentframe().f_code.co_name} -')
        im_base = '_'.join([
            self.scan_name,
            str(i).zfill(4)
        ])
        return os.path.join(self.img_dir, im_base + self.img_ext)
