import numpy as np
from pyqtgraph import Qt

def return_no_zero(x, y):
    return x[y > 0], y[y > 0]

def get_rect(x, y):
    left = x[0]
    top = y[0]
    width = max(x) - min(x)
    height = max(y) - min(y)
    return Qt.QtCore.QRectF(left, top, width, height)

def to_rgba(arr, cmap, alpha=1):
    img = cmap(
        (arr - arr.min()) / (arr.max() - arr.min())
    )
    img[:, :, 3] = alpha

    return img