import numpy as np
from pyqtgraph import Qt

def return_no_zero(x, y):
    return x[y > 0], y[y > 0]

def get_rect(x, y, force_1=True):
    left = x[0]
    top = y[0]
    width = max(x) - min(x)
    height = max(y) - min(y)
    if force_1:
        if width < 1:
            width = 1
        if height < 1:
            height = 1
    return Qt.QtCore.QRectF(left, top, width, height)

def to_rgba(arr, cmap, alpha=1):
    img = cmap(
        (arr - arr.min()) / (arr.max() - arr.min())
    )
    img[:, :, 3] = alpha

    return img