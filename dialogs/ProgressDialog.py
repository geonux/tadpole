# GUI imports
import typing

from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class ProgressDialog(QProgressDialog):
    def __init__(
        self,
        title: str,
        maximum: int,
        parent: typing.Optional[QWidget] = ...,
    ):
        super().__init__(None, "Abord", 0, maximum, parent)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.processEvents_step = max(maximum / 100, 1)

    def setValue(self, progressValue):
        pe = (progressValue - self.value()) >= self.processEvents_step
        super().setValue(progressValue)
        if pe:
            QApplication.processEvents()
