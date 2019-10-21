import h5py

from PyQt5.QtWidgets import QWidget
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

class H5Viewer(QWidget):
    def __init__(self, file, fname, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = QtWidgets.QToolBar('Tools')
        self.toolbar.addAction('Open')
        self.toolbar.addAction('Save')
        self.layout.addWidget(self.toolbar)
        self.tree = QTreeWidget()
        self.tree_top = QTreeWidgetItem()
        self.tree.addTopLevelItem(self.tree_top)
        self.update(file)
        self.layout.addWidget(self.tree)
        self.show()

    def update(self, file):
        if isinstance(file, h5py.File):
            self._h5_to_tree(self.tree_top, file)
    
    def _h5_to_tree(self, item, file):
        for key in file:
            new_item = QTreeWidgetItem(item)
            new_item.setText(0, key)
            if isinstance(file[key], h5py.Group):
                if 'arches' in file[key]:
                    for arc in file[key]['arches']:
                        arch_item = QTreeWidgetItem(new_item)
                        arch_item.setData(0, 0, int(arc))
                    new_item.sortChildren(0, QtCore.Qt.AscendingOrder)
                        
                        

