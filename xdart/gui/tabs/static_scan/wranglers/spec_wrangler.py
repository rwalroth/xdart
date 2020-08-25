# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
from collections import OrderedDict
import time

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from xdart.modules.ewald import EwaldArch, EwaldSphere
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .ui.specUI import Ui_Form
from ....gui_utils import NamedActionParameter
from xdart.utils import read_image_file, get_image_meta_data

img_fname = '/Users/v/SSRL_Data/RDA/static_det_test_data/test_xfc_data/images/images_0001.tif'
poni = '/Users/v/SSRL_Data/RDA/static_det_test_data/test_xfc_data/test_xfc.poni'

params = [
    # {'name': 'Image File', 'type': 'str', 'default': img_fname},
    {'name': 'Image File', 'type': 'str', 'value': img_fname},
    NamedActionParameter(name='image_file_browse', title='Browse...'),
    # {'name': 'PONI File', 'type': 'str', 'default': poni},
    {'name': 'PONI File', 'type': 'str', 'value': poni},
    NamedActionParameter(name='poni_file_browse', title='Browse...'),
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
        sigUpdateFile: (str, str), sends new scan_name and file name
            to tthetaWidget.
        showLabel: str, connected to thread showLabel signal, sets text
            in specLabel
    """
    showLabel = Qt.QtCore.Signal(str)

    def __init__(self, fname, file_lock, parent=None):
        """fname: str, file path
        file_lock: mp.Condition, process safe lock
        """
        super().__init__(fname, file_lock, parent)
        self.img_fname = ''
        self.img_dir = '.'
        self.img_ext = 'tif'

        # Setup gui elements
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.sigStart.emit)
        self.ui.pauseButton.clicked.connect(self.pause)
        self.ui.stopButton.clicked.connect(self.stop)
        self.ui.continueButton.clicked.connect(self.cont)

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
        self.poni_file = self.parameters.child('PONI File').value()
        self.timeout = self.parameters.child('Timeout').value()
        self.parameters.sigTreeStateChanged.connect(self.setup)

        # Setup thread
        self.thread = specThread(
            self.command_queue,
            self.sphere_args,
            self.fname,
            self.file_lock,
            self.scan_name,
            None,
            None,
            None,
            1,
            self
        )
        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.sigUpdateFile.emit)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.setup()

    def setup(self):
        """Sets up the child thread, syncs all parameters.
        """
        self.img_fname = self.parameters.child('Image File').value()
        self.thread.img_fname = self.img_fname
        print(f'spec_wrangler > img_fname: {self.img_fname}')

        img_dir, scan_name, img_ext = self.split_image_name()
        self.img_dir, self.scan_name, self.img_ext = img_dir, scan_name, img_ext
        self.thread.img_dir, self.thread.scan_name, self.thread.img_ext = img_dir, scan_name, img_ext
        print(f'spec_wrangler > img_dir, scan_name, ing_ext : {self.img_dir} {self.scan_name} {self.img_ext}')

        self.poni_file = self.parameters.child('PONI File').value()
        self.thread.poni_file = self.poni_file

        self.thread.scan_name = self.scan_name

        self.fname = os.path.join(self.img_dir, self.scan_name + '.hdf5')
        self.thread.fname = self.fname

        self.timeout = self.parameters.child('Timeout').value()
        self.thread.timeout = self.parameters.child('Timeout').value()

        self.thread.file_lock = self.file_lock
        self.thread.sphere_args = self.sphere_args

    def pause(self):
        if self.thread.isRunning():
            self.command_queue.put('pause')

    def cont(self):
        if self.thread.isRunning():
            self.command_queue.put('continue')

    def stop(self):
        if self.thread.isRunning():
            self.command_queue.put('stop')

    def set_image_file(self):
        """Opens file dialogue and sets the spec data file
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Image File').setValue(fname)
        self.img_fname = fname

    def set_poni_file(self):
        """Opens file dialogue and sets the calibration file
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('PONI File').setValue(fname)
        self.poni_file = fname

    def split_image_name(self):
        """Splits image filename to get directory, file root and extension

        Arguments:
            fname {str} -- full image file name with path
        """
        dir = os.path.dirname(self.img_fname)
        root, ext = os.path.splitext(os.path.basename(self.img_fname))

        try:
            root = root[:root.rindex('_')]
        except:
            pass

        return dir, root, ext

    def enabled(self, enable):
        """Sets tree and start button to enable.

        args:
            enable: bool, True for enabled False for disabled.
        """
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)


class specThread(wranglerThread):
    """Thread for controlling the specProcessor process. Receives
    manages a command and signal queue to pass commands from the main
    thread and communicate back relevant signals.

    attributes:
        command_q: mp.Queue, queue to send commands to process
        file_lock: mp.Condition, process safe lock for file access
        fname: str, path to data file.
        img_dir: str, path to image directory
        poni_file: str, Poni File name
        scan_name: str, name of current scan
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
            poni_file,
            img_dir,
            img_ext,
            timeout,
            parent=None):
        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        poni_file: str, poni file name
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        timeout: float or int, how long to continue checking for new
            data.
        """
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)
        self.scan_name = scan_name
        self.poni_file = poni_file
        self.img_dir = img_dir
        self.img_ext = img_ext
        self.timeout = timeout

    def run(self):
        """Initializes specProcess and watches for new commands from
        parent or signals from the process.
        """
        process = specProcess(
            self.command_q,
            self.signal_q,
            self.sphere_args,
            self.scan_name,
            self.fname,
            self.file_lock,
            self.poni_file,
            self.img_dir,
            self.img_ext,
            self.timeout
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
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    print(f'\nspec_wrangler > news_scan: {self.scan_name}\n')
                    self.sigUpdateFile.emit(self.scan_name, self.fname)
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
        fname: str, path to data file
        img_dir: str, path to image directory
        poni_file: str, poni file name
        scan_name: str, name of current scan
        signal_q: queue to place signals back to parent thread.
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

    def __init__(self, command_q, signal_q, sphere_args, scan_name,
                 fname, file_lock, poni_file,
                 img_dir, img_ext, timeout, *args, **kwargs):
        """command_q: mp.Queue, queue for commands from parent thread.
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        scan_name: str, name of current scan
        fname: str, path to data file
        file_lock: mp.Condition, process safe lock for file access
        poni_file: str, poni file name
        img_dir: str, path to image directory
        timeout: float or int, how long to continue checking for new
            data.
        """
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock,
                         *args, **kwargs)
        self.poni_file = poni_file
        self.scan_name = scan_name
        self.img_dir = img_dir
        self.img_ext = img_ext
        self.user = None
        self.timeout = timeout

    def _main(self):
        """Checks for commands in queue, sends back updates through
        signal queue, and catches errors. Calls wrangle method for
        reading in data, then performs integration.
        """
        # Initialize sphere and save to disk, send update for new scan
        print(f'\nspec_wrangler > self.fname: {self.fname}')
        print(f'spec_wrangler > self.scan_name: {self.scan_name}')
        sphere = EwaldSphere(self.scan_name,
                             data_file=self.fname,
                             keep_in_memory=True,
                             **self.sphere_args)
        with self.file_lock:
            sphere.save_to_h5(replace=True)
            self.signal_q.put(('new_scan', None))
        print(f'spec_wrangler > sphere name: {sphere.name}\n')

        # Enter main loop
        i = 1
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
                    idx, map_raw, poni_file=self.poni_file, scan_info=scan_info
                )

                # integrate image to 1d and 2d arrays
                arch.integrate_1d(**sphere.bai_1d_args)
                arch.integrate_2d(**sphere.bai_2d_args)

                # Add arch copy to sphere, save to file
                with self.file_lock:
                    sphere.add_arch(
                        arch=arch.copy(), calculate=False, update=True,
                        get_sd=True, set_mg=False
                    )
                    sphere.save_to_h5(data_only=True, replace=False)

                self.signal_q.put(('message', f'Image {i} integrated'))
                self.signal_q.put(('update', idx))
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
        self.signal_q.put(('message', f'Checking for {i}'))

        # Construct raw_file path from attributes and index
        image_file = self._get_image_path(i)
        print(f'\nspec_wrangler > Image File Name: {image_file}')

        # Read raw file into numpy array
        arr = read_image_file(image_file)

        meta_file = image_file[:-3] + 'txt'
        image_meta = get_image_meta_data(meta_file, BL='11-3')
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
        im_base = '_'.join([
            self.scan_name,
            str(i).zfill(4)
        ])
        return os.path.join(self.img_dir, im_base + self.img_ext)
