# -*- coding: utf-8 -*-

# Standard Library imports
import time
import os
import unittest
import traceback

# Other imports
import numpy as np
import h5py

# add xdart to path
import sys
if __name__ == "__main__":
    from config import xdart_dir
else:
    from .config import xdart_dir

if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.containers import nzarray1d, nzarray2d
from xdart.utils import div0

def paint_circle(shape, center, rad, val=1):
    arr = np.zeros(shape)
    for r in range(arr.shape[0]):
        for c in range(arr.shape[1]):
            y = r - center[0]
            x = c - center[1]
            if y**2 + x**2 < rad**2:
                arr[r,c] = val
    return arr

#@unittest.skip("Not testing these now")
class Test1D(unittest.TestCase):
    def setUp(self):
        self.arrays = {}
        
        arr1 = np.zeros(100)
        arr1[20:70] = 1
        
        self.arrays['arr1'] = arr1
        
        arr2 = np.zeros(100)
        arr2[50:80] = 1
        
        self.arrays['arr2'] = arr2
        
        arr3 = np.zeros(100)
        arr3[75:95] = 1
        
        self.arrays['arr3'] = arr3
        
        arr4 = np.arange(100)**2
        arr4[:23] = 0
        arr4[55:] = 0
        self.arrays['arr4'] = arr4
        
        self.arrays['all_zero'] = np.zeros(100)
        self.arrays['all_ones'] = np.ones(100)
        
        arrl = np.zeros(100)
        arrl[50:] = 1
        self.arrays['left_ones'] = arrl
        
        arrr = np.zeros(100)
        arrr[:51] = 1
        self.arrays['right_ones'] = arrr
    
    def test_init(self):
        for key, arr in self.arrays.items():
            nzarr = nzarray1d(arr)
            self.assertEqual(nzarr.shape, arr.shape, f"{key} failed")
            self.assertTrue((nzarr.full() == arr).all(), f"{key} failed")
    
    def test_sum(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray1d(arr)
                nzarr2 = nzarray1d(arr2)
                sumnp = arr + arr2
                sumnz = nzarr1 + nzarr2
                summix = nzarr1 + arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 + 2).full() == arr + 2).all(), f"{key} failed"
                        )
        
    def test_mul(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray1d(arr)
                nzarr2 = nzarray1d(arr2)
                sumnp = arr * arr2
                sumnz = nzarr1 * nzarr2
                summix = nzarr1 * arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 * 2).full() == arr * 2).all(), f"{key} failed"
                        )
    
    def test_div(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray1d(arr)
                nzarr2 = nzarray1d(arr2)
                sumnp = div0(arr, arr2)
                sumnz = nzarr1 / nzarr2
                summix = nzarr1 / arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 / 2).full() == arr / 2).all(), f"{key} failed"
                        )
    
    def test_sub(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray1d(arr)
                nzarr2 = nzarray1d(arr2)
                sumnp = arr - arr2
                sumnz = nzarr1 - nzarr2
                summix = nzarr1 - arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 - 2).full() == arr - 2).all(), f"{key} failed"
                        )
    
    def test_floordiv(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray1d(arr)
                nzarr2 = nzarray1d(arr2)
                sumnp = div0(arr, arr2).astype(int)
                sumnz = nzarr1 // nzarr2
                summix = nzarr1 // arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 // 2).full() == arr // 2).all(), f"{key} failed"
                        )
    
    def test_slice(self):
        for key, arr in self.arrays.items():
            nzarr1 = nzarray1d(arr)
            print(f"key: {key}, corners: {nzarr1.corners}")
            self.assertEqual(nzarr1[0], arr[0], f"{key} failed")
            self.assertEqual(nzarr1[-1], arr[-1], f"{key} failed")
            self.assertEqual(nzarr1[50], arr[50], f"{key} failed")
            self.assertEqual(nzarr1[25], arr[25], f"{key} failed")
            self.assertEqual(nzarr1[66], arr[66], f"{key} failed")
            self.assertTrue((nzarr1[30:50] == arr[30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[30:-50] == arr[30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:50] == arr[-30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:-50] == arr[-30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:] == arr[:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[50:] == arr[50:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:30] == arr[:30]).all(), f"{key} failed")
            self.assertTrue((nzarr1[arr > 1] == arr[arr > 1]).all(), f"{key} failed")


#@unittest.skip("Not testing these now")
class Test2D(unittest.TestCase):
    def setUp(self):
        self.arrays = {}
        
        arr1 = np.zeros((100,120))
        arr1[20:70,30:80] = 1
        self.arrays['arr1'] = arr1
        
        arr2 = np.zeros((100,120))
        arr2[50:80,20:75] = 1
        self.arrays['arr2'] = arr2
        
        arr3 = np.zeros((100,120))
        arr3[75:95,5:25] = 1
        self.arrays['arr3'] = arr3
        
        arr4 = np.arange(100*120, dtype='float64').reshape((100,120))**2
        arr4[93:, :] = 0
        arr4[:23, :] = 0
        arr4[:, 87:] = 0
        arr4[:, :37] = 0
        self.arrays['arr4'] = arr4
        
        self.arrays['all_zero'] = np.zeros((100,120))
        self.arrays['all_ones'] = np.ones((100,120))
        
        arrl = np.zeros((100,120))
        arrl[50:] = 1
        self.arrays['left_ones'] = arrl
        
        arrr = np.zeros((100,120))
        arrr[:51] = 1
        self.arrays['right_ones'] = arrr

        arrc = np.zeros((100,120))
        arrc[:50,:50] = 1
        self.arrays['corner'] = arrc
        
        arrcircle = paint_circle((100,120), (43,62), 35)
        self.arrays['circle'] = arrcircle
    
    def test_init(self):
        for key, arr in self.arrays.items():
            nzarr = nzarray2d(arr)
            self.assertEqual(nzarr.shape, arr.shape, f"{key} failed")
            self.assertTrue((nzarr.full() == arr).all(), f"{key} failed")
    
    def test_sum(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray2d(arr)
                nzarr2 = nzarray2d(arr2)
                sumnp = arr + arr2
                sumnz = nzarr1 + nzarr2
                summix = nzarr1 + arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 + 2).full() == arr + 2).all(), f"{key} failed"
                        )
        
    def test_mul(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray2d(arr)
                nzarr2 = nzarray2d(arr2)
                sumnp = arr * arr2
                sumnz = nzarr1 * nzarr2
                summix = nzarr1 * arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed with {key2}")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed with {key2}")
                self.assertTrue(
                        ((nzarr1 * 2).full() == arr * 2).all(), f"{key} failed with {key2}"
                        )
    
    def test_div(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray2d(arr)
                nzarr2 = nzarray2d(arr2)
                sumnp = div0(arr, arr2)
                sumnz = nzarr1 / nzarr2
                summix = nzarr1 / arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 / 2).full() == arr / 2).all(), f"{key} failed"
                        )
    
    def test_sub(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray2d(arr)
                nzarr2 = nzarray2d(arr2)
                sumnp = arr - arr2
                sumnz = nzarr1 - nzarr2
                summix = nzarr1 - arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 - 2).full() == arr - 2).all(), f"{key} failed"
                        )
    
    def test_floordiv(self):
        for key, arr in self.arrays.items():
            for key2, arr2 in self.arrays.items():
                nzarr1 = nzarray2d(arr)
                nzarr2 = nzarray2d(arr2)
                sumnp = div0(arr, arr2).astype(int)
                sumnz = nzarr1 // nzarr2
                summix = nzarr1 // arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 // 2).full() == arr // 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Slicing not implemented yet")
    def test_slice(self):
        for key, arr in self.arrays.items():
            nzarr1 = nzarray2d(arr)
            print(f"key: {key}, corners: {nzarr1.corners}")
            self.assertEqual(nzarr1[0,0], arr[0,0], f"{key} failed")
            self.assertEqual(nzarr1[-1,0], arr[-1,0], f"{key} failed")
            self.assertEqual(nzarr1[50,50], arr[50,50], f"{key} failed")
            self.assertEqual(nzarr1[25, 25], arr[25, 25], f"{key} failed")
            self.assertEqual(nzarr1[66, 32], arr[66, 32], f"{key} failed")
            self.assertTrue((nzarr1[30:50] == arr[30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[30:-50] == arr[30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:50] == arr[-30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:-50] == arr[-30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:] == arr[:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[50:] == arr[50:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:30] == arr[:30]).all(), f"{key} failed")
            self.assertTrue((nzarr1[arr > 1] == arr[arr > 1]).all(), f"{key} failed")
            self.assertTrue((nzarr1[10:30, 20:50] == arr[10:30, 20:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[60:70, 30:50] == arr[60:70, 30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[60:70, 40:50] == arr[60:70, 40:50]).all(), f"{key} failed")


class Test1DLazy(unittest.TestCase):
    
    def prep_nzarray(self, arr, key):
        nzarr1 = nzarray1d(arr=arr)
        self.file.create_group(key)
        nzarr1.to_hdf5(self.file[key])
        self.arrays.append(key)
    
    def get_arrs(self, key):
        arrnz = nzarray1d()
        arrnz.from_hdf5(self.file[key])
        arr = arrnz.full()
        nzarr = nzarray1d(grp=self.file[key], lazy=True)
        return arr, nzarr
        
    
    def setUp(self):
        self.arrays = []
        file_path = os.path.join(xdart_dir, 'tests/test_data/nzarray_tests.hdf5')
        self.file = h5py.File(file_path, 'w')
        
        arr1 = np.zeros(100)
        arr1[20:70] = 1
        self.prep_nzarray(arr1, 'arr1')
        
        arr2 = np.zeros(100)
        arr2[50:80] = 1
        self.prep_nzarray(arr2, 'arr2')
        
        arr3 = np.zeros(100)
        arr3[75:95] = 1
        self.prep_nzarray(arr3, 'arr3')
        
        arr4 = np.arange(100)**2
        arr4[:23] = 0
        arr4[55:] = 0
        self.prep_nzarray(arr4, 'arr4')
        
        self.prep_nzarray(np.zeros(100), 'all_zero')
        self.prep_nzarray(np.ones(100), 'all_one')
        
        arrl = np.zeros(100)
        arrl[50:] = 1
        self.prep_nzarray(arrl, 'arr_left')
        
        arrr = np.zeros(100)
        arrr[:51] = 1
        self.prep_nzarray(arrr, 'arr_right')
    
    def tearDown(self):
        self.file.close()
    
    #@unittest.skip("Not testing these now")
    def test_init(self):
        for key in self.arrays:
            arr, nzarr = self.get_arrs(key)
            self.assertEqual(nzarr.shape, arr.shape, f"{key} failed")
            self.assertTrue((nzarr.full() == arr).all(), f"{key} failed")
    
    #@unittest.skip("Not testing these now")
    def test_sum(self):
        for key in self.arrays:
            arr, nzarr1 = self.get_arrs(key)
            for key2 in self.arrays:
                arr2, nzarr2 = self.get_arrs(key2)
                sumnp = arr + arr2
                sumnz = nzarr1 + nzarr2
                summix = nzarr1 + arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 + 2).full() == arr + 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Not testing these now")
    def test_mul(self):
        for key in self.arrays:
            arr, nzarr1 = self.get_arrs(key)
            for key2 in self.arrays:
                arr2, nzarr2 = self.get_arrs(key2)
                sumnp = arr * arr2
                sumnz = nzarr1 * nzarr2
                summix = nzarr1 * arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 * 2).full() == arr * 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Not testing these now")
    def test_div(self):
        for key in self.arrays:
            arr, nzarr1 = self.get_arrs(key)
            for key2 in self.arrays:
                arr2, nzarr2 = self.get_arrs(key2)
                sumnp = div0(arr, arr2)
                sumnz = nzarr1 / nzarr2
                summix = nzarr1 / arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 / 2).full() == arr / 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Not testing these now")
    def test_sub(self):
        for key in self.arrays:
            arr, nzarr1 = self.get_arrs(key)
            for key2 in self.arrays:
                arr2, nzarr2 = self.get_arrs(key2)
                sumnp = arr - arr2
                sumnz = nzarr1 - nzarr2
                summix = nzarr1 - arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 - 2).full() == arr - 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Not testing these now")
    def test_floordiv(self):
        for key in self.arrays:
            arr, nzarr1 = self.get_arrs(key)
            for key2 in self.arrays:
                arr2, nzarr2 = self.get_arrs(key2)
                sumnp = div0(arr, arr2).astype(int)
                sumnz = nzarr1 // nzarr2
                summix = nzarr1 // arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 // 2).full() == arr // 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Not testing these now")
    def test_slice(self):
        for key in self.arrays:
            arr, nzarr1 = self.get_arrs(key)
            print(f"key: {key}, corners: {nzarr1.corners}")
            self.assertEqual(nzarr1[0], arr[0], f"{key} failed")
            self.assertEqual(nzarr1[-1], arr[-1], f"{key} failed")
            self.assertEqual(nzarr1[50], arr[50], f"{key} failed")
            self.assertEqual(nzarr1[25], arr[25], f"{key} failed")
            self.assertEqual(nzarr1[66], arr[66], f"{key} failed")
            self.assertTrue((nzarr1[30:50] == arr[30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[30:-50] == arr[30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:50] == arr[-30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:-50] == arr[-30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:] == arr[:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[50:] == arr[50:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:30] == arr[:30]).all(), f"{key} failed")
            self.assertTrue((nzarr1[arr > 1] == arr[arr > 1]).all(), f"{key} failed")

#@unittest.skip("Not testing these now")
class Test2DLazy(unittest.TestCase):
    
    def prep_nzarray(self, arr, key):
        nzarr1 = nzarray2d(arr=arr)
        self.file.create_group(key)
        nzarr1.to_hdf5(self.file[key])
        self.arrays.append(key)
    
    def get_arrs(self, key):
        arrnz = nzarray2d()
        arrnz.from_hdf5(self.file[key])
        arr = arrnz.full()
        nzarr = nzarray2d(grp=self.file[key], lazy=True)
        return nzarr, arr

    def setUp(self):
        self.arrays = []
        file_path = os.path.join(xdart_dir, 'tests/test_data/nzarray_tests.hdf5')
        self.file = h5py.File(file_path, 'w')
        
        arr1 = np.zeros((100,120))
        arr1[20:70,30:80] = 1
        self.prep_nzarray(arr1, 'arr1')
        
        arr2 = np.zeros((100,120))
        arr2[50:80,20:75] = 1
        self.prep_nzarray(arr2, 'arr2')
        
        arr3 = np.zeros((100,120))
        arr3[75:95,5:25] = 1
        self.prep_nzarray(arr3, 'arr3')
        
        arr4 = np.arange(100*120, dtype='float64').reshape((100,120))**2
        arr4[93:, :] = 0
        arr4[:23, :] = 0
        arr4[:, 87:] = 0
        arr4[:, :37] = 0
        self.prep_nzarray(arr4, 'arr4')
        
        self.prep_nzarray(np.zeros((100,120)), 'all_zero')
        self.prep_nzarray(np.ones((100,120)), 'all_one')
        
        arrl = np.zeros((100,120))
        arrl[50:] = 1
        self.prep_nzarray(arrl, 'arr_left')
        
        arrr = np.zeros((100,120))
        arrr[:51] = 1
        self.prep_nzarray(arrr, 'arr_right')

        arrc = np.zeros((100,120))
        arrc[:50,:50] = 1
        self.prep_nzarray(arrc, 'arrc')
        
        arrcircle = paint_circle((100,120), (43,62), 35)
        self.prep_nzarray(arrcircle, 'arrcircle')
    
    def tearDown(self):
        self.file.close()
    
    def test_init(self):
        for key in self.arrays:
            nzarr, arr = self.get_arrs(key)
            self.assertTrue(all(nzarr.shape == arr.shape), f"{key} failed")
            self.assertTrue((nzarr.full() == arr).all(), f"{key} failed")
    
    def test_sum(self):
        for key in self.arrays:
            nzarr1, arr = self.get_arrs(key)
            for key2 in self.arrays:
                nzarr2, arr2 = self.get_arrs(key2)
                sumnp = arr + arr2
                sumnz = nzarr1 + nzarr2
                summix = nzarr1 + arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 + 2).full() == arr + 2).all(), f"{key} failed"
                        )
        
    def test_mul(self):
        for key in self.arrays:
            nzarr1, arr = self.get_arrs(key)
            for key2 in self.arrays:
                nzarr2, arr2 = self.get_arrs(key2)
                sumnp = arr * arr2
                sumnz = nzarr1 * nzarr2
                summix = nzarr1 * arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed with {key2}")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed with {key2}")
                self.assertTrue(
                        ((nzarr1 * 2).full() == arr * 2).all(), f"{key} failed with {key2}"
                        )
    
    def test_div(self):
        for key in self.arrays:
            nzarr1, arr = self.get_arrs(key)
            for key2 in self.arrays:
                nzarr2, arr2 = self.get_arrs(key2)
                sumnp = div0(arr, arr2)
                sumnz = nzarr1 / nzarr2
                summix = nzarr1 / arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 / 2).full() == arr / 2).all(), f"{key} failed"
                        )
    
    def test_sub(self):
        for key in self.arrays:
            nzarr1, arr = self.get_arrs(key)
            for key2 in self.arrays:
                nzarr2, arr2 = self.get_arrs(key2)
                sumnp = arr - arr2
                sumnz = nzarr1 - nzarr2
                summix = nzarr1 - arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 - 2).full() == arr - 2).all(), f"{key} failed"
                        )
    
    def test_floordiv(self):
        for key in self.arrays:
            nzarr1, arr = self.get_arrs(key)
            for key2 in self.arrays:
                nzarr2, arr2 = self.get_arrs(key2)
                sumnp = div0(arr, arr2).astype(int)
                sumnz = nzarr1 // nzarr2
                summix = nzarr1 // arr2
                self.assertTrue((sumnz.full() == sumnp).all(), f"{key} failed")
                self.assertTrue((summix.full() == sumnp).all(), f"{key} failed")
                self.assertTrue(
                        ((nzarr1 // 2).full() == arr // 2).all(), f"{key} failed"
                        )
    
    #@unittest.skip("Slicing not implemented yet")
    def test_slice(self):
        for key in self.arrays:
            nzarr1, arr = self.get_arrs(key)
            print(f"key: {key}, corners: {nzarr1.corners}")
            self.assertEqual(nzarr1[0,0], arr[0,0], f"{key} failed")
            self.assertEqual(nzarr1[-1,0], arr[-1,0], f"{key} failed")
            self.assertEqual(nzarr1[50,50], arr[50,50], f"{key} failed")
            self.assertEqual(nzarr1[25, 25], arr[25, 25], f"{key} failed")
            self.assertEqual(nzarr1[66, 32], arr[66, 32], f"{key} failed")
            self.assertTrue((nzarr1[30:50] == arr[30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[30:-50] == arr[30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:50] == arr[-30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[-30:-50] == arr[-30:-50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:] == arr[:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[50:] == arr[50:]).all(), f"{key} failed")
            self.assertTrue((nzarr1[:30] == arr[:30]).all(), f"{key} failed")
            self.assertTrue((nzarr1[arr > 1] == arr[arr > 1]).all(), f"{key} failed")
            self.assertTrue((nzarr1[10:30, 20:50] == arr[10:30, 20:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[60:70, 30:50] == arr[60:70, 30:50]).all(), f"{key} failed")
            self.assertTrue((nzarr1[60:70, 40:50] == arr[60:70, 40:50]).all(), f"{key} failed")

if __name__ == '__main__':
    unittest.main()
