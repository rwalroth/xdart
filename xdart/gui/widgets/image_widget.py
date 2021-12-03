# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports
import numpy as np
from matplotlib import cm

# This module imports
from ..gui_utils import RectViewBox
from .imageWidgetUI import Ui_Form
from .imageWidgetUI_static import Ui_Form as Ui_Form_static

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt, QtGui, QtCore
from pyqtgraph import PColorMeshItem
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import ColorMap
from pyqtgraph import functions as fn
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject
from pyqtgraph import getConfigOption

# from icecream import ic; ic.configureOutput(prefix='', includeContext=True)

QFileDialog = QtWidgets.QFileDialog


class XDImageWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # Setup range slider
        #self.rangeSlider = RangeSlider(self)
        #self.sliderLayout = Qt.QtWidgets.QVBoxLayout(self.ui.sliderFrame)
        #self.sliderLayout.addWidget(self.rangeSlider)

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.histogram = pg.HistogramLUTWidget(self.image_win)
        self.ui.toolLayout.addWidget(self.histogram, 1, 0, 1, 2)
        self.imageViewBox = RectViewBox()
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        self.imageItem = pg.ImageItem(colormap=cm.get_cmap('viridis'))

        self.image_plot.addItem(self.imageItem)
        self.histogram.setImageItem(self.imageItem)
        self.histogram.vb.setMouseEnabled(x=False, y=False)
        self.raw_image = np.array(0)
        self.norm_image = np.array(0)
        self.displayed_image = np.array(0)
        starter = np.random.normal(50, 10, 256*256)
        starter.sort()
        self.setImage(starter.reshape((256, 256)))

        self.ui.logButton.toggled.connect(self.update_image)
        self.ui.cmapBox.currentIndexChanged.connect(self.set_cmap)
        self.set_cmap(0)

        self.show()

    def setImage(self, image, rect=None):
        self.raw_image = image[()]
        self.norm_image = normalize(self.raw_image)
        self.displayed_image = self.norm_image[()]
        self.update_image()
        if rect is not None:
            self.imageItem.setRect(rect)

    def setRect(self, rect):
        self.imageItem.setRect(rect)

    def update_image(self, q=None):
        self.displayed_image = np.copy(self.raw_image)
        if self.ui.logButton.isChecked():
            self.displayed_image[self.displayed_image < 0] = 0
            minval = self.displayed_image[self.displayed_image > 0].min()
            self.displayed_image = np.log10(self.displayed_image/minval + 1)
            self.imageItem.setImage(self.displayed_image)
            self.histogram.item.axis.setScale(self.raw_image.max() /
                                              self.displayed_image.max())
        else:
            self.imageItem.setImage(self.displayed_image)
            self.histogram.item.axis.setScale(None)

    def set_cmap(self, index):
        self.histogram.item.gradient.loadPreset(
            self.ui.cmapBox.itemText(index)
        )


class pgImageWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None, lockAspect=False, raw=False):
        super().__init__(parent)
        self.ui = Ui_Form_static()
        self.ui.setupUi(self)

        # Some options for Raw Images
        self.raw = raw

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)

        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.imageViewBox = RectViewBox(lockAspect=lockAspect)
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        self.imageItem = pgXDImageItem(raw=self.raw)
        self.image_plot.addItem(self.imageItem)

        # Make Label Item for showing position
        self.make_pos_label()

        self.histogram = pg.ColorBarItem(width=15)
        # Have ColorBarItem control colors of img and appear in 'plot':
        self.histogram.setImageItem(self.imageItem, insert_in=self.image_plot)

        self.raw_image = np.zeros(0)
        self.displayed_image = np.zeros(0)
        self.show()

    def make_pos_label(self, itemPos=(1, 0), parentPos=(1, 1), offset=(0, -20)):
        self.image_win.addItem(self.imageItem.pos_label)
        self.imageItem.pos_label.anchor(itemPos=itemPos, parentPos=parentPos, offset=offset)
        self.imageItem.pos_label.setFixedWidth(1)

    def setImage(self, image, rect=None,
                 scale='Linear', cmap='viridis',
                 **kwargs):
        self.raw_image = image[()]
        self.update_image(scale, cmap, **kwargs)
        if rect is not None:
            self.imageItem.setRect(rect)

    def setRect(self, rect):
        self.imageItem.setRect(rect)

    def update_image(self, scale='Linear', cmap='viridis', **kwargs):
        self.displayed_image = np.asarray(np.copy(self.raw_image), dtype=float)

        cmap = 'viridis' if cmap == 'Default' else cmap
        cm = pg.colormap.getFromMatplotlib(cmap)  # prepare a linear color map
        self.histogram.axis.setLogMode(False)

        if scale == 'Log':
            min_val = np.nanmin(self.displayed_image)
            if min_val < 1:
                self.displayed_image -= (min_val - 1)
            self.displayed_image = np.log10(self.displayed_image)

            levels = np.nanpercentile(self.displayed_image, (0.1, 99.9))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            self.histogram.axis.setLogMode(True)
        elif scale == 'Sqrt':
            min_val = np.nanmin(self.displayed_image)
            if min_val < 0:
                img = np.sqrt(np.abs(self.displayed_image))
                img[self.displayed_image < 0] *= -1
                self.displayed_image = img
            else:
                self.displayed_image = np.sqrt(self.displayed_image)

            levels = np.nanpercentile(self.displayed_image, (0.5, 99.9))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

        else:
            levels = np.nanpercentile(self.displayed_image, (1, 99))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            self.histogram.axis.setLogMode(False)

        self.histogram.setColorMap(cm)
        low, high = np.min(self.displayed_image), np.max(self.displayed_image)
        self.histogram.lo_lim, self.histogram.hi_lim = low, high
        self.histogram.setLevels(values=levels)


class pgXDImageItem(pg.ImageItem):
    def __init__(self, parent=None, raw=False):
        super().__init__(parent)

        self.pos_label = pg.LabelItem(justify='right')
        self.raw = raw

    def hoverEvent(self, ev):
        """Show the position, pixel, and value under the mouse cursor.
        """
        if ev.isExit():
            self.pos_label.setText('')
            return

        data = self.image
        pos = ev.pos()
        # i, j = pos.y(), pos.x()
        i, j = pos.x(), pos.y()
        i = int(np.clip(i, 0, data.shape[0] - 1))
        j = int(np.clip(j, 0, data.shape[1] - 1))
        val = data[i, j]
        ppos = self.mapToParent(pos)
        x, y = ppos.x(), ppos.y()
        if self.raw:
            self.pos_label.setText(f'{x:0.0f}, {y:0.0f} [{val:.2e}]')
        else:
            self.pos_label.setText(f'{x:0.2f}, {y:0.2f} [{val:.2e}]')


def normalize(arr):
    """

    Parameters
    ----------
    arr : numpy.ndarray
    """
    minval = arr.min()
    maxval = arr.max()
    if maxval > minval:
        return (arr - minval) / (maxval - minval)
    else:
        return np.ones_like(arr)


def sliced(arr, ceiling):
    out = np.copy(arr)
    maxval = arr.max() * (ceiling/100)
    out[out > maxval] = maxval
    return out


class pmeshImageWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None, lockAspect=False, raw=False):
        super().__init__(parent)
        self.ui = Ui_Form_static()
        self.ui.setupUi(self)

        # Some options for Raw Images
        self.raw = raw

        # Image pane setup
        self.image_layout = Qt.QtWidgets.QHBoxLayout(self.ui.imageFrame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)

        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.imageViewBox = RectViewBox(lockAspect=lockAspect)
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        # self.imageItem = PColorMeshItem()
        self.imageItem = PColorMeshItemLevels()
        self.image_plot.addItem(self.imageItem)

        # Make Label Item for showing position
        # self.make_pos_label()

        # self.histogram = pg.ColorBarItem(width=15)
        # Have ColorBarItem control colors of img and appear in 'plot':
        # self.histogram.setImageItem(self.imageItem, insert_in=self.image_plot)

        self.raw_image = np.zeros(0)
        self.displayed_image = np.zeros(0)
        self.show()

    def make_pos_label(self, itemPos=(1, 0), parentPos=(1, 1), offset=(0, -20)):
        self.image_win.addItem(self.imageItem.pos_label)
        self.imageItem.pos_label.anchor(itemPos=itemPos, parentPos=parentPos, offset=offset)
        self.imageItem.pos_label.setFixedWidth(1)

    def setImage(self, image, rect=None,
                 scale='Linear', cmap='viridis',
                 **kwargs):
        self.raw_image = image[()]
        self.update_image(scale, cmap, **kwargs)
        if rect is not None:
            self.imageItem.setRect(rect)

    def setRect(self, rect):
        self.imageItem.setRect(rect)

    def update_image(self, scale='Linear', cmap='viridis', **kwargs):
        self.displayed_image = np.asarray(np.copy(self.raw_image), dtype=float)

        cmap = 'viridis' if cmap == 'Default' else cmap
        cm = pg.colormap.getFromMatplotlib(cmap)  # prepare a linear color map
        # self.histogram.axis.setLogMode(False)

        if scale == 'Log':
            min_val = np.min(self.displayed_image)
            if min_val < 1:
                self.displayed_image -= (min_val - 1)
            self.displayed_image = np.log10(self.displayed_image)

            levels = np.nanpercentile(self.displayed_image, (0.1, 99.9))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            # self.histogram.axis.setLogMode(True)
        elif scale == 'Sqrt':
            min_val = np.min(self.displayed_image)
            if min_val < 0:
                img = np.sqrt(np.abs(self.displayed_image))
                img[self.displayed_image < 0] *= -1
                self.displayed_image = img
            else:
                self.displayed_image = np.sqrt(self.displayed_image)

            levels = np.nanpercentile(self.displayed_image, (0.5, 99.9))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

        else:
            levels = np.nanpercentile(self.displayed_image, (1, 99))
            self.imageItem.setImage(self.displayed_image, levels=levels, **kwargs)

            # self.histogram.axis.setLogMode(False)

        self.imageItem.setLevels(levels)
        # self.histogram.setCmap(cm)

        # self.histogram.setLevels(values=levels)
        # low, high = np.min(self.displayed_image), np.max(self.displayed_image)
        # self.histogram.lo_lim, self.histogram.hi_lim = low, high


class PColorMeshItemLevels(PColorMeshItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        GraphicsObject.__init__(self)

        self.qpicture = None  ## rendered picture for display

        self.axisOrder = getConfigOption('imageAxisOrder')

        if 'edgecolors' in kwargs.keys():
            self.edgecolors = kwargs['edgecolors']
        else:
            self.edgecolors = None

        if 'antialiasing' in kwargs.keys():
            self.antialiasing = kwargs['antialiasing']
        else:
            self.antialiasing = False

        if 'cmap' in kwargs.keys():
            if kwargs['cmap'] in Gradients.keys():
                self.cmap = kwargs['cmap']
            else:
                raise NameError('Undefined colormap, should be one of the following: ' + ', '.join(
                    ['"' + i + '"' for i in Gradients.keys()]) + '.')
        else:
            self.cmap = 'viridis'

        # If some data have been sent we directly display it
        if len(args) > 0:
            self.setData(*args)

        self.levels = None

    def _prepareData(self, args):
        """
        Check the shape of the data.
        Return a set of 2d array x, y, z ready to be used to draw the picture.
        """

        # User didn't specified data
        if len(args) == 0:

            self.x = None
            self.y = None
            self.z = None

        # User only specified z
        elif len(args) == 1:
            # If x and y is None, the polygons will be displaced on a grid
            x = np.arange(0, args[0].shape[0] + 1, 1)
            y = np.arange(0, args[0].shape[1] + 1, 1)
            self.x, self.y = np.meshgrid(x, y, indexing='ij')
            self.z = args[0]

        # User specified x, y, z
        elif len(args) == 3:

            # Shape checking
            if args[0].shape[0] != args[2].shape[0] + 1 or args[0].shape[1] != args[2].shape[1] + 1:
                raise ValueError('The dimension of x should be one greater than the one of z')

            if args[1].shape[0] != args[2].shape[0] + 1 or args[1].shape[1] != args[2].shape[1] + 1:
                raise ValueError('The dimension of y should be one greater than the one of z')

            self.x = args[0]
            self.y = args[1]
            self.z = args[2]

        else:
            ValueError('Data must been sent as (z) or (x, y, z)')

    def setData(self, *args):
        """
        Set the data to be drawn.

        Parameters
        ----------
        x, y : np.ndarray, optional, default None
            2D array containing the coordinates of the polygons
        z : np.ndarray
            2D array containing the value which will be maped into the polygons
            colors.
            If x and y is None, the polygons will be displaced on a grid
            otherwise x and y will be used as polygons vertices coordinates as::

                (x[i+1, j], y[i+1, j])           (x[i+1, j+1], y[i+1, j+1])
                                    +---------+
                                    | z[i, j] |
                                    +---------+
                    (x[i, j], y[i, j])           (x[i, j+1], y[i, j+1])

            "ASCII from: <https://matplotlib.org/3.2.1/api/_as_gen/
                         matplotlib.pyplot.pcolormesh.html>".
        """

        # Prepare data
        cd = self._prepareData(args)

        # Has the view bounds changed
        shapeChanged = False
        if self.qpicture is None:
            shapeChanged = True
        elif len(args) == 1:
            if args[0].shape[0] != self.x[:, 1][-1] or args[0].shape[1] != self.y[0][-1]:
                shapeChanged = True
        elif len(args) == 3:
            if np.any(self.x != args[0]) or np.any(self.y != args[1]):
                shapeChanged = True

        self.qpicture = QtGui.QPicture()
        p = QtGui.QPainter(self.qpicture)
        # We set the pen of all polygons once
        if self.edgecolors is None:
            p.setPen(fn.mkPen(QtGui.QColor(0, 0, 0, 0)))
        else:
            p.setPen(fn.mkPen(self.edgecolors))
            if self.antialiasing:
                p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        ## Prepare colormap
        # First we get the LookupTable
        pos = [i[0] for i in Gradients[self.cmap]['ticks']]
        color = [i[1] for i in Gradients[self.cmap]['ticks']]
        cmap = ColorMap(pos, color)
        lut = cmap.getLookupTable(0.0, 1.0, 256)
        # Second we associate each z value, that we normalize, to the lut

        vmin, vmax = self.z.min(), self.z.max()
        if self.levels is not None:
            vmin, vmax = self.levels
            vmin = max(vmin, self.z.min())
            vmax = min(vmax, self.z.max())

        norm = self.z - vmin
        norm_max = vmax - vmin
        norm = norm / norm_max
        norm = (norm * (len(lut) - 1)).astype(int)
        norm[norm < 0] = 0
        norm[norm > 255] = 255

        # Go through all the data and draw the polygons accordingly
        for xi in range(self.z.shape[0]):
            for yi in range(self.z.shape[1]):
                # Set the color of the polygon first
                c = lut[norm[xi][yi]]
                p.setBrush(fn.mkBrush(QtGui.QColor(c[0], c[1], c[2])))

                polygon = QtGui.QPolygonF(
                    [QtCore.QPointF(self.x[xi][yi], self.y[xi][yi]),
                     QtCore.QPointF(self.x[xi + 1][yi], self.y[xi + 1][yi]),
                     QtCore.QPointF(self.x[xi + 1][yi + 1], self.y[xi + 1][yi + 1]),
                     QtCore.QPointF(self.x[xi][yi + 1], self.y[xi][yi + 1])]
                )

                # DrawConvexPlygon is faster
                p.drawConvexPolygon(polygon)

        p.end()
        self.update()

        self.prepareGeometryChange()
        if shapeChanged:
            self.informViewBoundsChanged()

    def setLevels(self, levels):
        self.levels = levels
        self.update()

    def paint(self, p, *args):
        try:
            if self.z is None:
                return
        except AttributeError:
            return

        p.drawPicture(0, 0, self.qpicture)

    def setRect(self, *args):
        """
        setRect(rect) or setRect(x,y,w,h)

        Sets translation and scaling of this ImageItem to display the current image within the rectangle given
        as ``QtCore.QRect`` or ``QtCore.QRectF`` `rect`, or described by parameters `x, y, w, h`, defining starting
        position, width and height.

        This method cannot be used before an image is assigned.
        See the :ref:`examples <ImageItem_examples>` for how to manually set transformations.
        """
        if len(args) == 0:
            self.resetTransform()  # reset scaling and rotation when called without argument
            return
        if isinstance(args[0], (QtCore.QRectF, QtCore.QRect)):
            rect = args[0]  # use QRectF or QRect directly
        else:
            if hasattr(args[0], '__len__'):
                args = args[0]  # promote tuple or list of values
            rect = QtCore.QRectF(*args)  # QRectF(x,y,w,h), but also accepts other initializers
        tr = QtGui.QTransform()
        tr.translate(rect.left(), rect.top())
        tr.scale(rect.width() / self.width(), rect.height() / self.height())
        self.setTransform(tr)
