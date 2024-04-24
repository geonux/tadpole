# GUI imports
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtCore import Qt

from utils.image_utils import load_as_qimage, get_bytes_from_qimage


class ImageChangeDialog(QDialog):

    def __init__(
        self, title: str, image_fp: any, image_size: tuple[int, int], image_format: int
    ):
        """Dialog used to change Frog images

        Args:
            title (str): Dialog title
            image_fp (any): Current image
            image_size (tuple[int,int]): Image size (width, height)
        """
        super().__init__()

        self.image_format = image_format
        self.image_size = image_size

        self.setWindowTitle(title)
        self.setWindowIcon(
            QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        )

        # Setup Main Layout
        layout_main = QVBoxLayout()
        self.setLayout(layout_main)

        # set up current image viewer
        layout_main.addWidget(QLabel("Current Image"))
        current_viewer = QLabel()
        current_viewer.setMinimumSize(*image_size)
        current_viewer.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        current_viewer.setText("Current image is invalid or unsupported")
        layout_main.addWidget(current_viewer)

        if isinstance(image_fp, QImage):
            self.current_img = image_fp
        else:
            self.current_img = load_as_qimage(image_fp, image_size, image_format)
        
        if not self.current_img.isNull():
            current_viewer.setPixmap(QPixmap().fromImage(self.current_img))

        layout_main.addWidget(QLabel(" "))  # spacer

        # set up new image viewer
        layout_main.addWidget(QLabel("New Image"))
        self.new_viewer = QClickableLabel(self._new_viewer_clicked)
        self.new_viewer.setMinimumSize(*image_size)
        self.new_viewer.setStyleSheet("background-color: white;")
        self.new_viewer.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.new_viewer.setText("Click to Select New Image")
        layout_main.addWidget(self.new_viewer)

        # Main Buttons Layout (Save/Cancel)
        layout_buttons = QHBoxLayout()
        layout_main.addLayout(layout_buttons)

        # Save Existing Cover To File Button
        self.button_write = QPushButton("Export current")
        self.button_write.clicked.connect(self._save_current_as)
        self.button_write.setDisabled(self.current_img.isNull())
        layout_buttons.addWidget(self.button_write)

        # Save Button
        # set disabled by default; need to wait for user to select new image
        self.button_save = QPushButton("Save")
        self.button_save.setDefault(True)
        self.button_save.setDisabled(True)
        self.button_save.clicked.connect(self.accept)
        layout_buttons.addWidget(self.button_save)

        # Cancel Button
        button_cancel = QPushButton("Cancel")
        button_cancel.clicked.connect(self.reject)
        layout_buttons.addWidget(button_cancel)

    def get_bytes_for_new_image(self):
        return get_bytes_from_qimage(self.new_viewer.pixmap().toImage(), self.image_format)
    
    def get_new_image(self) -> QImage:
        return self.new_viewer.pixmap().toImage()

    def _save_current_as(self):
        newCoverFileName = QFileDialog.getSaveFileName(
            self, "Save Cover", "c:\\", "Image files (*.png)"
        )[0]

        if newCoverFileName:
            self.current_img.save(newCoverFileName)
            QMessageBox.about(self, "Save ROM Cover", "ROM cover saved successfully")

    def _new_viewer_clicked(self):
        # Prompts user for image path and loads same.
        file_name = QFileDialog.getOpenFileName(
            self,
            "Open file",
            None,
            "Images (*.jpg *.png *.webp);;RAW (RGB565 Little Endian) Images (*.*)",
        )[0]
        if len(file_name) > 0:  # confirm if user selected a file
            img = load_as_qimage(file_name, self.image_size, self.image_format)
            self.new_viewer.setPixmap(QPixmap().fromImage(img))
            self.button_save.setDisabled(False)


class QClickableLabel(QLabel):
    """
    QLabel subclass that emits a signal when clicked.

    Args:
        on_click (callable): A function or method to call when the label is clicked.
    """

    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click

    def mousePressEvent(self, ev):
        """
        Overrides built-in function to handle mouse click events.
        """
        self.on_click()
