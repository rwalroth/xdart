# -*- coding: utf-8 -*-

# Standard Library imports
import time
import os
import unittest
import traceback

# Other imports
import numpy as np 
import pandas as pd
import pprint

# add xdart to path
import sys

xdart_dir = os.path.dirname(__file__).split('xdart')[0] + 'xdart'

if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.classes.spec import get_spec_header, get_spec_scan, LoadSpecFile

SPEC_PATH = os.path.join(xdart_dir, 'tests/test_data/spec_pd100k/direct_beam_full')

LSF_INPUTS = {
    'spec_file_path': os.path.join(xdart_dir, 'tests/test_data/spec_pd100k/'),
    'spec_file_name': 'direct_beam_full'
}

class TestSpec(unittest.TestCase):
    def setUp(self):
        self.lsf = LoadSpecFile()
        self.lsf.inputs.update(LSF_INPUTS)
        self.outputs = self.lsf.run()
        self.header = get_spec_header(SPEC_PATH)
    
    def test_header(self):
        self.assertDictEqual(self.header, self.outputs['header'])
    
    def test_scan(self):
        for i in range(1,8):
            df, meta = get_spec_scan(SPEC_PATH, i, self.header)
            self.assertEqual(meta, self.outputs['scans_meta'][i])
            self.assertTrue(df.equals(self.outputs['scans'][i]))
        
if __name__ == '__main__':
    lsf = LoadSpecFile()
    lsf.inputs['spec_file_path'] = os.path.join(xdart_dir, 'tests/test_data/spec_pd100k/')
    lsf.inputs['spec_file_name'] = 'direct_beam_full'
    niter = 1
    start = time.time()
    for i in range(niter):
        lsf_outputs = lsf.run()
    print(f"LoadSpecFile took {time.time() - start} seconds for {niter} iterations")
    
    start = time.time()
    for i in range(niter):
        header = get_spec_header(SPEC_PATH)
        df_7, meta_7 = get_spec_scan(SPEC_PATH, 7, header)
    print(f"Loading last scan took {time.time() - start} seconds for {niter} iterations")
    unittest.main(verbosity=3)
