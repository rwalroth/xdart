import h5py

from PyQt5.QtWidgets import QWidget
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

class H5Viewer(QWidget):
    def __init__(self, file, fname, parent=None):
        super().__init__(parent)
        self.file = file
        self.fname = fname
        self.layout = QtWidgets.QVBoxLayout(self)
        self.toolbar = QtWidgets.QToolBar('Tools')
        self.toolbar.addAction('Open')
        self.toolbar.addAction('Save')
        self.layout.addWidget(self.toolbar)
        self.tree = QTreeWidget()
        self.tree_top = QTreeWidgetItem()
        self.tree.addTopLevelItem(self.tree_top)
        self.update_tree(self.file)
        self.layout.addWidget(self.tree)
        self.show()

    def update_tree(self, file):
        if isinstance(self.file, h5py.File):
            self._h5_to_tree(self.tree_top, file)
    
    def _h5_to_tree(self, tree, file):
        for key in file:
            item = QTreeWidgetItem(tree)
            item.setText(0, key)
            if isinstance(file[key], h5py.Group):
                self._h5_to_tree(item, file[key])
            self.tree_top.addChild(item)

