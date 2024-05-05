from dataclasses import dataclass
from os.path import splitext
from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QImage


@dataclass
class Size:
    width: int
    height: int


known_image_size = [
    # SF2000
    (640, 480),
    (144, 208),
    (128, 245),
    (400, 192),
    (40, 24),
    (392, 80),
    # SF901
    (853, 480),
    (853, 392),
]

no_thumb_magic_byte = b"\x35\xA8\xF8\x02"


image_exts = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"]


def bytes_per_pixel(qimage_format: int) -> int:
    """
    Compute the number of bytes needed to store a pixel in the given QImage format.
    """
    bpp_dict = {
        QImage.Format_RGB32: 4,
        QImage.Format_RGB16: 2,
    }

    return bpp_dict.get(qimage_format)


def nb_bytes(image_size: Size, image_format: int) -> int:
    """
    Returns the number of bytes required to store an image with the given size and format.
    """
    return image_size[0] * image_size[1] * bytes_per_pixel(image_format)


def match_image_size(file_size: int, image_size: Size, image_format: int):
    # Check if the image we try to open have the right size
    if file_size == nb_bytes(image_size, image_format):
        return image_size

    # Else, try to define the size from known size
    for x in known_image_size:
        if file_size == nb_bytes(x, image_format):
            return x

    return (0, 0)


def resize_qimage(qimage: QImage, size: Size, crop=True) -> QImage:
    """
    Resize a QImage to fit a given area while maintaining the aspect ratio.
    """
    aspect_ratio_mode = Qt.KeepAspectRatioByExpanding if crop else Qt.IgnoreAspectRatio

    # Resize the image
    scaled_image = qimage.scaled(
        size.width, size.height, aspect_ratio_mode, Qt.SmoothTransformation
    )

    # Crop the image to fit the target area
    # Only realy needed when mode is Qt.KeepAspectRatioByExpanding
    crop_x = (scaled_image.width() - size.width) // 2
    crop_y = (scaled_image.height() - size.height) // 2
    return scaled_image.copy(crop_x, crop_y, size.width, size.height)


def load_as_qimage(image_fp: any, image_size: Size, image_format: int) -> QImage:
    """
    Loads a file handler to the image.  Can be a file pointer, a path, or an array of bytes.  Supports .raw or other format.
    """
    image_content = None
    if isinstance(image_fp, bytes):
        image_content = image_fp

    # if image_fp have an unknown extension, read it as bytes
    if (isinstance(image_fp, str) and splitext(image_fp)[1] not in image_exts) or (
        isinstance(image_fp, Path) and image_fp.suffix not in image_exts
    ):
        with open(image_fp, "rb") as f:
            image_content = f.read()

    if image_content:
        # if image_fp is an array of bytes, open it as a RGB16 (RGB565 Little Endian)
        valid_img_size = match_image_size(len(image_content), image_size, image_format)

        img = QImage(image_content, *valid_img_size, image_format)
    else:  # otherwise let QImage autodetection do its thing
        img = QImage(image_fp)

    if not img.isNull() and img.size() != QSize(*image_size):
        img = resize_qimage(img, image_size)

    return img


def get_bytes_from_qimage(qimage: QImage, dest_img_format: int) -> bytes:
    """
    Convert a QImage to bytes using the specified image format.
    """
    img = qimage.convertToFormat(dest_img_format)
    return img.bits().asstring(img.byteCount())


def write_qimage(fp, qimage: QImage, image_size: Tuple[int, int], image_format: int):
    if qimage:
        fp.write(get_bytes_from_qimage(qimage, image_format))
    else:
        fp.write(no_thumb_magic_byte)
        fp.write(bytes(b"\x01" * (nb_bytes(image_size, image_format) - 4)))
