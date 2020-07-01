# -*- coding: utf-8 -*-

# Standard Library imports
import time
import os
import unittest
import traceback

# Other imports
import numpy as np
import pyFAI
from pyFAI import units
import h5py

# add xdart to path
import sys
if __name__ == "__main__":
    from config import xdart_dir
else:
    from .config import xdart_dir

if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.modules.ewald import EwaldArch, EwaldSphere
from xdart.utils.containers import PONI

def read_RAW(file, mask = True):
    #print("Reading RAW file here...")
    try:
        with open(file, 'rb') as im:
            arr = np.frombuffer(im.read(), dtype='int32').copy()
        arr.shape = (195, 487)
        #arr = np.fliplr(arr)               # for the way mounted at BL2-1
        if mask:
            for i in range(0, 10):
                arr[:,i] = -2.0
            for i in range(477, 487):
                arr[:,i] = -2.0
        return arr
    except:
        traceback.print_exc()
        print("Error reading file: %s" % file)
        return None

def SPECread(filename, scan_number):
    print("Reading SPEC file here...")
    tth = []
    i0 = []
    spec = open(filename)
    for line in spec:
        if "#O" in line and "TwoTheta" in line: 
            temp = line.split()
            tth_line = temp[0][2]
            for i in range(0, len(temp)):
                if temp[i] == "TwoTheta":	
                    tth_pos = i
                    break
            break
    for line in spec:
        if "#S" in line:
            temp = line.split()
            if int(temp[1]) == scan_number:
                break
    for line in spec:
        if "#P" + str(tth_line) in line:
            temp = line.split()
            tth_start = float(temp[tth_pos])
            break
    for line in spec:
        if "#L" in line:
            motors = line.split()[1:]
            if "TwoTheta" not in line:
                tth_motor_bool = False
                print("2theta is not scanned...")
            else:
                tth_motor_bool = True
                tth_motor = motors.index("TwoTheta")
            i0_motor = motors.index("Monitor")
            break
    for line in spec:
        try:
            temp = line.split()
            if tth_motor_bool:
                tth = np.append(tth, float(temp[tth_motor]))
            else:
                tth = np.append(tth, tth_start)
            i0 = np.append(i0, float(temp[i0_motor]))
        except:
            break
    spec.close()
    return tth, i0


def make_sphere(calib_path, poni_file, stepsize, user, image_path, spec_path, 
                spec_name, scan_number):
    tth, i0 = SPECread(spec_path + spec_name, scan_number)
    xmax_global = 0.0  
    xmin_global = 180.0
    times = {'overall':[], 'creation':[], 'int':[], 'add':[]}
    detector = pyFAI.detectors.Detector(172e-6, 172e-6)
    data_file_path = os.path.join(xdart_dir, "tests/test_data/spec_pd100k/test_save.h5")
    sphere = EwaldSphere(data_file=data_file_path)
    sphere.save_to_h5(replace=True)
    poni = PONI.from_ponifile(os.path.join(calib_path, poni_file))
    for k in range(1, len(tth)):
        start = time.time()
        filename = (image_path + user + spec_name + "_scan" + str(scan_number) +
                    "_" + str(k).zfill(4) + ".raw")
        map_raw = read_RAW(filename)
        map_raw = map_raw.T
        mask = np.where(map_raw < 0, 1, 0)
        rot2 = np.radians(-tth[k])
        poni.rot2 = rot2
        start_c = time.time()
        arch = EwaldArch(idx=k, map_raw=map_raw, poni=poni, scan_info={'i0':i0[k]})
        times['creation'].append(time.time() - start_c)
        start_i = time.time()
        arch.integrate_1d(numpoints=18000, monitor='i0', radial_range=[0,180], 
                        unit=units.TTH_DEG, correctSolidAngle=False, 
                        method='csr')
        arch.integrate_2d(npt_rad=1000, npt_azim=1000, monitor='i0', radial_range=[0,30], azimuth_range=[70,110], method='csr')
        times['int'].append(time.time() - start_i)
        start_a = time.time()
        sphere.add_arch(arch.copy(), calculate=False, set_mg=False)
        sphere.save_to_h5(arches=[k], data_only=True, replace=False)
        times['add'].append(time.time() - start_a)
        
        times['overall'].append(time.time() - start)
    return sphere


class TestEwaldSphere(unittest.TestCase):
    def setUp(self):
        self.sphere = make_sphere(
            calib_path=os.path.join(xdart_dir, "tests/test_data/spec_pd100k/"),
            poni_file="poni.poni",
            stepsize=0.01,
            user="b_stone_",
            image_path=os.path.join(xdart_dir, "tests/test_data/spec_pd100k/images/"),
            spec_path=os.path.join(xdart_dir, "tests/test_data/spec_pd100k/"),
            spec_name = "LaB6_2",
            scan_number = 1
        )
        
        self.true_1d_ttheta = np.load(
            os.path.join(xdart_dir, "tests/test_data/spec_pd100k/1d_ttheta.npy")
        )
        self.true_1d_norm = np.load(
            os.path.join(xdart_dir, "tests/test_data/spec_pd100k/1d_norm.npy")
        )
        
        self.true_2d_ttheta = np.load(
            os.path.join(xdart_dir, "tests/test_data/spec_pd100k/2d_ttheta.npy")
        )
        self.true_2d_norm = np.load(
            os.path.join(xdart_dir, "tests/test_data/spec_pd100k/2d_norm.npy")
        )
        self.true_2d_chi = np.load(
            os.path.join(xdart_dir, "tests/test_data/spec_pd100k/2d_chi.npy")
        )
    
    #@unittest.skip("Known to pass")
    def test_1d(self):
        self.assertTrue(np.isclose(self.true_1d_ttheta, 
                                   self.sphere.bai_1d.ttheta).all())
        self.assertTrue(np.isclose(self.true_1d_norm, 
                                   self.sphere.bai_1d.norm.full(),
                                   rtol=1e-3, atol=1e-4).all())
    
    #@unittest.skip("Known to pass")
    def test_2d(self):
        self.assertTrue(np.isclose(self.true_2d_ttheta, 
                                   self.sphere.bai_2d.ttheta).all())
        self.assertTrue(np.isclose(self.true_2d_norm, 
                                   self.sphere.bai_2d.norm.full(),
                                   rtol=1e-3, atol=1e-4).all())
        self.assertTrue(np.isclose(self.true_2d_chi, 
                                   self.sphere.bai_2d.chi).all())
    
    def test_save(self):
        self.sphere.save_to_h5(arches=[])
        self.sphere.save_to_h5(arches=[1], data_only=True, replace=False)
    
    def test_bai(self):
        self.sphere.by_arch_integrate_1d(numpoints=18000, monitor='i0', radial_range=[0,180], 
                        unit=units.TTH_DEG, correctSolidAngle=False, 
                        method='csr')
        self.assertEqual(self.sphere.bai_1d_args['method'], 'csr')
        self.assertTrue(np.isclose(self.true_1d_norm, 
                                   self.sphere.bai_1d.norm.full(),
                                   rtol=1e-3, atol=1e-4).all())


if __name__ == '__main__':
    unittest.main()
    # sphere = make_sphere(
    #         calib_path="test_data/spec_pd100k/",
    #         poni_file="poni.poni",
    #         stepsize=0.01,
    #         user="b_stone_",
    #         image_path="test_data/spec_pd100k/images/",
    #         spec_path="test_data/spec_pd100k/",
    #         spec_name = "LaB6_2",
    #         scan_number = 1
    #     )

