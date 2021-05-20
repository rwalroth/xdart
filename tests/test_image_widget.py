# -*- coding: utf-8 -*-

# Standard Library imports
import sys

# Qt imports
from PyQt5 import QtGui

if __name__ == '__main__':
    from config import xdart_dir
else:
    from .config import xdart_dir

if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.gui.widgets.image_widget import XDImageWidget

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    test = XDImageWidget()
    test.show()
    app.exec_()
