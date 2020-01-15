import os
import copy
import numpy as np
from ....classes.spec import LoadSpecFile, MakePONI
import time
from ....containers import PONI

class SpecPreProcessor(object):
    """Process which watches for new image files and changes to spec
    file. Passes information on to analyzer in generic format, future
    servers can stand in as long as they provide the same data.
    """
    def __init__(self, data_queue, command_queue, spec_name, user, image_dir, 
                 data_points, scan_number, lsf_inputs, mp_inputs, timeout=5):
        self.user = user
        self.data_q = data_queue
        self.command_q = command_queue
        self.spec_name = spec_name
        self.image_dir = image_dir
        self.data_points = data_points
        self.scan_number = scan_number
        self.lsf_inputs = lsf_inputs
        self.mp_inputs = mp_inputs
        self.timeout = timeout
    
    def run(self):
        # Operation instantiated within process to avoid conflicts with locks
        print("Processor launched")
        make_poni = MakePONI()
        make_poni.inputs.update(self.mp_inputs)

        # Operation instantiated within process to avoid conflicts with locks
        spec_reader = LoadSpecFile()
        spec_reader.inputs.update(self.lsf_inputs)

        for i in range(self.data_points):
            print(f'Checking for {i}')
            if not self.command_q.empty():
                # Checks for any commands from main process
                command = self.command_q.get()
                if command == 'TERMINATE':
                    break
            
            end_early = False # flag that a timeout has occurred

            # image file names formed as predictable pattern
            raw_file = self.get_raw_path(i)

            start = time.time()
            while True:
                # Looks for relevant data, loops until it is found or a
                # timeout occurs
                try:
                    # reads in spec data file
                    outputs = spec_reader.run()

                    if self.scan_number in outputs['scans'].keys():
                        image_meta = outputs['scans']\
                                         [self.scan_number].loc[i].to_dict()
                    
                    else:
                        image_meta = outputs['current_scan'].loc[i].to_dict()
                    make_poni.inputs['spec_dict'] = \
                        copy.deepcopy(image_meta)
                    poni = copy.deepcopy(make_poni.run())
                    arr = self.read_raw(raw_file)
                    self.data_q.put(('image', (i, arr, image_meta, poni)))
                    print(f'Image {i} added to queue')
                    break
                except (KeyError, FileNotFoundError, AttributeError, ValueError):
                    elapsed = time.time() - start
                if elapsed > self.timeout:
                    print("Timeout occurred")
                    end_early = True
                    break
            if end_early:
                break
        self.data_q.put(('TERMINATE', None))

    def get_raw_path(self, i):
        im_base = '_'.join([
            self.user,
            self.spec_name,
            'scan' + str(self.scan_number),
            str(i).zfill(4)
        ])
        return os.path.join(self.image_dir, im_base + '.raw')
    
    
    def read_raw(self, file, mask=True):
        with open(file, 'rb') as im:
            arr = np.fromstring(im.read(), dtype='int32')
            arr.shape = (195, 487)
            if mask:
                for i in range(0, 10):
                    arr[:,i] = -2.0
                for i in range(477, 487):
                    arr[:,i] = -2.0
            return arr.T

