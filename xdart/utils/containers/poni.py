from pyFAI.detectors import Detector
from pyFAI import detector_factory
from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
import pygix, pyFAI
import yaml
import numpy as np


class PONI(object):
    """Container for values needed in AzimuthalIntegrator of pyFAI.
    Also provides some utility functions for reading and writing data
    
    attributes:
        detector: pyFAI Detector, detector object
        dist: float, distance to detector, meters
        poni1: float, location of point of nearest incidence 1, meters
        poni2: float, location of point of nearest incidence 2, meters
        rot1: float, angle of rotation 1, radians
        rot2: float, angle of rotation 2, radians
        rot3: float, angle of rotation 3, radians
        wavelength: float, wavelength of energy, used for
            collecting data, meters
    """
    _poni_keys = {
        'Distance': 'dist',
        'Poni1': 'poni1',
        'Poni2': 'poni2',
        'Rot1': 'rot1',
        'Rot2': 'rot2',
        'Rot3': 'rot3',
        'Wavelength': 'wavelength'
    }

    def __init__(self, dist=0, poni1=0, poni2=0, rot1=0, rot2=0, rot3=0, 
                 wavelength=1e-10, detector=Detector(100e-6, 100e-6)):
        """
        dist: float, distance to detector, meters
        poni1: float, location of point of nearest incidence 1, meters
        poni2: float, location of point of nearest incidence 2, meters
        rot1: float, angle of rotation 1, radians
        rot2: float, angle of rotation 2, radians
        rot3: float, angle of rotation 3, radians
        wavelength: float, wavelength of energy, used for
            collecting data, meters
        detector: pyFAI Detector, detector object
        """
        self.dist = dist
        self.poni1 = poni1 
        self.poni2 = poni2 
        self.rot1 = rot1 
        self.rot2 = rot2 
        self.rot3 = rot3 
        self.wavelength = wavelength
        self.detector = detector

    def to_dict(self):
        """Converts all attributes to dictionary with pyFAI names
        """
        return {
            'Distance': self.dist,
            'Poni1': self.poni1,
            'Poni2': self.poni2,
            'Rot1': self.rot1,
            'Rot2': self.rot2,
            'Rot3': self.rot3,
            'Wavelength': self.wavelength,
            'Detector': self.detector.name,
            'Detector_config': {
                'pixel1': self.detector.pixel1,
                'pixel2': self.detector.pixel2,
                'max_shape': self.detector.max_shape
            }
        }

    @classmethod
    def from_dict(cls, input):
        """Creates PONI object from a dictionary.
        """
        out = cls()
        for key in input:
            setattr(out, key, input[key])
        return out
    
    @classmethod
    def from_yamdict(cls, input):
        """Creates a PONI object from the yaml dictionary returned
        from reading a .poni file
        """
        out = cls()
        for key in input:
            if key == 'Detector':
                if 'Detector_config' in input:
                    if 'max_shape' in input['Detector_config']:
                        if not (input['Detector_config']['max_shape'] is None or 
                                type(input['Detector_config']['max_shape']) == str):
                            input['Detector_config']['max_shape'] = list(input['Detector_config']['max_shape'])
                    out.detector = detector_factory(
                        input['Detector'], config=input['Detector_config']
                    )
                elif 'PixelSize1' in input and 'PixelSize2' in input:
                    out.detector = detector_factory(
                        input['Detector'], 
                        config={
                            'pixel1': input['PixelSize1'],
                            'pixel2': input['PixelSize2'],
                        }
                    )
                else:
                    out.detector = detector_factory(input['Detector'])
            elif key == 'Wavelength':
                if type(input[key]) == str:
                    out.wavelength = eval(input[key])
                else:
                    out.wavelength = input[key]
            else:
                try:
                    setattr(out, cls._poni_keys[key], input[key])
                except KeyError:
                    pass
        return out
    
    @classmethod
    def from_yaml(cls, stream):
        """Creates a PONI object from a yaml stream.
        """
        input = yaml.safe_load(stream)
        return cls.from_yamdict(input)
    
    @classmethod
    def from_ponifile(cls, file):
        """Creates a PONI object from a .poni file.
        """
        if type(file) == str:
            with open(file, 'r') as f:
                out = cls.from_yaml(f)
        else:
            out = cls.from_yaml(file)
        return out


def get_poni_dict(poni_file):
    """ Read Poni File and convert to Dictionary"""
    ai = pyFAI.load(poni_file)
    poni_keys = ['_dist', '_rot1', '_rot2', '_rot3', '_poni1', '_poni2', 'detector', '_wavelength']

    try:
        poni_dict = {k: ai.__getattribute__(k) for k in poni_keys}
        return poni_dict
    except KeyError:
        return None


def create_ai_from_dict(poni_dict, gi=False):
    """Create Azimuthal Integrator object from Dictionary"""
    ai = AzimuthalIntegrator()
    for k, v in poni_dict.items():
        ai.__setattr__(k, v)

    if not gi:
        if 'MX225' in ai.detector.name:
            ai._rot3 -= np.deg2rad(90)
    else:
        calib_pars = dict(
            dist=ai._dist, poni1=ai._poni1, poni2=ai._poni2,
            rot1=ai._rot1, rot2=ai._rot2, rot3=ai._rot3,
            wavelength=ai._wavelength, detector=ai.detector)
        ai = pygix.Transform(**calib_pars)
        ai.sample_orientation = 3  # 1 is horizontal, 2 is vertical

    return ai
