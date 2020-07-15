# -*- coding: utf-8 -*-
"""
ROI.py -  Interactive graphics items for GraphicsView (ROI widgets)
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more information.

Implements a series of graphics items which display movable/scalable/rotatable shapes
for use as region-of-interest markers. ROI class automatically handles extraction 
of array data from ImageItems.

The ROI class is meant to serve as the base for more specific types; see several examples
of how to build an ROI at the bottom of the file.
"""

from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
#from numpy.linalg import norm
from pyqtgraph.Point import *
from pyqtgraph.SRTTransform import SRTTransform
from math import cos, sin
from pyqtgraph import functions as fn
from pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject
from pyqtgraph.graphicsItems.UIGraphicsItem import UIGraphicsItem
from pyqtgraph import getConfigOption
from pyqtgraph.graphicsItems.ROI import *

def rectStr(r):
    return "[%f, %f] + [%f, %f]" % (r.x(), r.y(), r.width(), r.height())

def place_on_circle(angle, x=0.5, y=0.5, r=0.5):
    return x + r*np.cos(angle), y + r*np.sin(angle)

def maskCoordinates(coords, mask, flag=-1):
    """
    Applies the mask to the coordinates, setting any 0 values in mask
    to -1.

    Parameters
    ----------
    coords : numpy.ndarray, coordinates returned from getArrayRegion
    mask : numpy.ndarray, mask to be applied
    flag : int, value to represent 0 values in mask

    Returns
    -------
    m_coords : numpy.ndarray, masked coordinates

    """
    m_coords = coords.copy()
    m_coords[0] *= mask
    m_coords[1] *= mask
    m_coords[0][mask == 0] = flag
    m_coords[1][mask == 0] = flag

    return m_coords


class XDEllipseROI(EllipseROI):
    r"""
    Elliptical ROI subclass with one scale handle and one rotation handle.


    ============== =============================================================
    **Arguments**
    pos            (length-2 sequence) The position of the ROI's origin.
    size           (length-2 sequence) The size of the ROI's bounding rectangle.
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================
    
    """
    def __init__(self, pos, size, **args):
        self.path = None
        ROI.__init__(self, pos, size, **args)
        self.sigRegionChanged.connect(self._clearPath)
        self._addHandles()
        
    def _addHandles(self):
        self.addScaleHandle([1, 0.5], [0, 0.5])
        self.addScaleHandle([0, 0.5], [1, 0.5])
        self.addScaleHandle([0.5, 0], [0.5, 1])
        self.addScaleHandle([0.5, 1], [0.5, 0])

        self.addScaleHandle(place_on_circle(np.pi / 4),
                           place_on_circle(5 * np.pi / 4))
        self.addScaleHandle(place_on_circle(3 * np.pi / 4),
                           place_on_circle(7 * np.pi / 4))
        self.addScaleHandle(place_on_circle(5 * np.pi / 4),
                           place_on_circle(np.pi / 4))
        self.addScaleHandle(place_on_circle(7 * np.pi / 4),
                           place_on_circle(3 * np.pi / 4))
        
    def getArrayRegion(self, arr, img=None, axes=(0, 1), **kwds):
        """
        Return the result of :meth:`~pyqtgraph.ROI.getArrayRegion` masked by the
        elliptical shape of the ROI. Regions outside the ellipse are set to 0.

        See :meth:`~pyqtgraph.ROI.getArrayRegion` for a description of the
        arguments.

        Note: ``returnMappedCoords`` is not yet supported for this ROI type.
        """
        # Note: we could use the same method as used by PolyLineROI, but this
        # implementation produces a nicer mask.
        if kwds.get("returnMappedCoords", False):
            arr, coords = ROI.getArrayRegion(self, arr, img, axes, **kwds)
        else:
            arr = ROI.getArrayRegion(self, arr, img, axes, **kwds)
            coords = None
        if arr is None or arr.shape[axes[0]] == 0 or arr.shape[axes[1]] == 0:
            return arr
        w = arr.shape[axes[0]]
        h = arr.shape[axes[1]]

        ## generate an ellipsoidal mask
        mask = np.fromfunction(lambda x,y: (((x+0.5)/(w/2.)-1)**2+ ((y+0.5)/(h/2.)-1)**2)**0.5 < 1, (w, h))
        
        # reshape to match array axes
        if axes[0] > axes[1]:
            mask = mask.T
        shape = [(n if i in axes else 1) for i,n in enumerate(arr.shape)]
        mask = mask.reshape(shape)

        if coords is not None:
            coords = maskCoordinates(coords, mask)
            return arr * mask, coords

        return arr * mask


class XDPolyLineROI(PolyLineROI):
    r"""
    Container class for multiple connected LineSegmentROIs.

    This class allows the user to draw paths of multiple line segments.

    ============== =============================================================
    **Arguments**
    positions      (list of length-2 sequences) The list of points in the path.
                   Note that, unlike the handle positions specified in other
                   ROIs, these positions must be expressed in the normal
                   coordinate system of the ROI, rather than (0 to 1) relative
                   to the size of the ROI.
    closed         (bool) if True, an extra LineSegmentROI is added connecting 
                   the beginning and end points.
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================
    
    """
    def __init__(self, positions, closed=False, pos=None, **args):
        super().__init__(positions, closed, pos, **args)

    def getArrayRegion(self, data, img, axes=(0,1), **kwds):
        """
        Return the result of :meth:`~pyqtgraph.ROI.getArrayRegion`, masked by
        the shape of the ROI. Values outside the ROI shape are set to 0.

        See :meth:`~pyqtgraph.ROI.getArrayRegion` for a description of the
        arguments.

        Note: ``returnMappedCoords`` is not yet supported for this ROI type.
        """
        br = self.boundingRect()
        if br.width() > 1000:
            raise Exception()
        if kwds.get("returnMappedCoords", False):
            sliced, coords = ROI.getArrayRegion(self, data, img, axes=axes, fromBoundingRect=True, **kwds)

        else:
            sliced = ROI.getArrayRegion(self, data, img, axes=axes, fromBoundingRect=True, **kwds)
            coords = None
        
        if img.axisOrder == 'col-major':
            mask = self.renderShapeMask(sliced.shape[axes[0]], sliced.shape[axes[1]])
        else:
            mask = self.renderShapeMask(sliced.shape[axes[1]], sliced.shape[axes[0]])
            mask = mask.T
            
        # reshape mask to ensure it is applied to the correct data axes
        shape = [1] * data.ndim
        shape[axes[0]] = sliced.shape[axes[0]]
        shape[axes[1]] = sliced.shape[axes[1]]
        mask = mask.reshape(shape)

        if coords is not None:
            coords = maskCoordinates(coords, mask)
            return sliced * mask, coords

        return sliced * mask

