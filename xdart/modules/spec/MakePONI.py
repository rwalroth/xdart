from collections import OrderedDict
from pyFAI.detectors import Detector
import numpy as np

from xdart.utils.containers import PONI
from ..operation import Operation

inputs = OrderedDict(
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

outputs = {
    'Distance': 0,
    'Poni1': 0,
    'Poni2': 0,
    'Rot1': 0,
    'Rot2': 0,
    'Rot3': 0,
    'Wavelength': 0,
    'Detector': 'Detector',
    'Detector_config': {
        'pixel1': 100e-6,
        'pixel2': 100e-6,
        'max_shape': None
    }
}

class MakePONI(Operation):
    """Operation for creating PONI objects. Uses a calibration poni file
    and adds in rotation values from motor positions to yield a
    dictionary with new values for a PONI object.
    """
    def __init__(self):
        super(MakePONI, self).__init__(inputs, outputs)
        self.base = None
    
    def run(self):
        """Main method of operation, calculates values for new PONI
        object.
        
        returns:
            outputs: dict, values to create a PONI object.
        """
        if self.base is None:
            self._set_base()
        poni = PONI.from_ponifile(self.inputs['poni_file'])
        
        for key, val in self.inputs['rotations'].items():
            if val is not None:
                r = np.radians(-self.inputs['spec_dict'][val]) + getattr(self.base, key)
                setattr(poni, key, r)
        
        self.outputs.update(poni.to_dict())

        return self.outputs
    
    def _set_base(self):
        """Adjusts base calibration based on where calibration was
        performed.
        """
        base = PONI.from_ponifile(self.inputs['poni_file'])
        for key, val in self.inputs['calib_rotations'].items():
            try:
                r = getattr(base, key) - val
            except TypeError:
                r = getattr(base, key)
            setattr(base, key, r)
        self.base = base

