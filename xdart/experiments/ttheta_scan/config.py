from collections import OrderedDict
from pyFAI import units
import pandas as pd


user = "b_stone"
spec_name = "pd_LaB6"
image_dir = r"C:\Users\walroth\OneDrive - SLAC National Accelerator Laboratory\out_dir"
lsf_inputs = OrderedDict(
        spec_file_path=r"C:\Users\walroth\OneDrive - SLAC National Accelerator Laboratory\out_dir",
        spec_file_name="pd_LaB6_out"
        )
mp_inputs = OrderedDict(
    rotations = {
        "rot1": None,
        "rot2": 'TwoTheta',
        "rot3": None
    },
    calib_rotations = {
        "rot1": 0,
        "rot2": 0,
        "rot3": 0
    },
    poni_file = r"C:\Users\walroth\OneDrive - SLAC National Accelerator Laboratory\out_dir\poni.poni",
    spec_dict = {}
)
data_file = r"C:\Users\walroth\OneDrive - SLAC National Accelerator Laboratory\out_dir\test.h5"
sphere_args = OrderedDict(
    arches=[], 
    data_file='scan0',
    scan_data=pd.DataFrame(), 
    mg_args={'wavelength': 1e-10},
    bai_1d_args={
        "numpoints":18000, 
        "radial_range":[0,180],
        "monitor":'I0',
        "unit":units.TTH_DEG, 
        "correctSolidAngle":False
    }, 
    bai_2d_args={}
)
