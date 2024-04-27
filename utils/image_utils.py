import io
import logging
import zipfile
from os.path import basename, join, splitext
from typing import Optional, Tuple

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QImage

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

image_exts = [".png", ";jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"]

def bytes_per_pixel(qimage_format: int) -> int:
    """
    Compute the number of bytes needed to store a pixel in the given QImage format.
    """
    bpp_dict = {
        QImage.Format_RGB32: 4,
        QImage.Format_RGB16: 2,
    }

    return bpp_dict.get(qimage_format)


def nb_bytes(size: Tuple[int, int], image_format: int) -> int:
    """
    Returns the number of bytes required to store an image with the given size and format.
    """
    return size[0] * size[1] * bytes_per_pixel(image_format)


def match_image_size(file_size: int, image_size: tuple[int, int], image_format: int):
    # Check if the image we try to open have the right size
    if file_size == nb_bytes(image_size, image_format):
        return image_size

    # Else, try to define the size from known size
    for x in known_image_size:
        if file_size == nb_bytes(x, image_format):
            return x

    return (0, 0)


def resize_qimage(qimage, target_size, crop=True) -> QImage:
    """
    Resize a QImage to fit a given area while maintaining the aspect ratio.
    """
    target_width, target_height = target_size
    aspect_ratio_mode = Qt.KeepAspectRatioByExpanding if crop else Qt.IgnoreAspectRatio

    # Resize the image
    scaled_image = qimage.scaled(
        target_width, target_height, aspect_ratio_mode, Qt.SmoothTransformation
    )

    # Crop the image to fit the target area
    # Only realy needed when mode is Qt.KeepAspectRatioByExpanding
    crop_x = (scaled_image.width() - target_width) // 2
    crop_y = (scaled_image.height() - target_height) // 2
    return scaled_image.copy(crop_x, crop_y, target_width, target_height)


def load_as_qimage(
    image_fp: any, image_size: Tuple[int, int], image_format: int
) -> QImage:
    """
    Loads a file handler to the image.  Can be a file pointer, a path, or an array of bytes.  Supports .raw or other format.
    """
    image_content = None
    if isinstance(image_fp, bytes):
        image_content = image_fp

    # if image_fp have an unknown extension, read it as bytes
    if isinstance(image_fp, str) and splitext(image_fp)[1] not in image_exts:
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


def get_qimage_from_zxx(
    zxx_rom_path: str, image_size: Tuple[int, int], image_format: int
) -> QImage:
    """
    Extracts image from the rom and passes to load image function.
    """
    file_extension = splitext(zxx_rom_path)[1]
    if not file_extension in [".zfb", ".zfc", ".zgb", ".zmd", ".zsf"]:
        raise ValueError(f"File extension {file_extension} not supported.")

    with open(zxx_rom_path, "rb") as rom_file:
        img_bytes = rom_file.read(nb_bytes(image_size, image_format))

    return load_as_qimage(img_bytes, image_size, image_format)


def create_zfb_file(
    zfb_file_path: str,
    rom_string: str,
    qimage: QImage,
    image_size: Tuple[int, int],
    image_format: int = QImage.Format_RGB16,
):
    with open(zfb_file_path, "wb") as zfb_fp:
        if qimage:
            zfb_fp.write(get_bytes_from_qimage(qimage, image_format))
        else:
            zfb_fp.write(bytes(b"\x01" * nb_bytes(image_size, image_format)))

        # Write four 00 bytes
        zfb_fp.write(b"\x00\x00\x00\x00")
        # Write the ROM filename
        zfb_fp.write(rom_string.encode())
        # Write two 00 bytes
        zfb_fp.write(b"\x00\x00")

    logging.info(f"ZFB file `{zfb_file_path}` created successfully.")


def replace_thumb_in_zxx(
    zxx_rom_path: str, qimage: QImage, image_size: Tuple[int, int], image_format: int
) -> QImage:
    img = qimage.convertToFormat(image_format)
    if img.byteCount() != nb_bytes(image_size, image_format):
        raise ValueError(f"Invalid image size for {image_format}.")

    img_bits = img.bits().asstring(img.byteCount())
    with open(zxx_rom_path, "wb") as zxx_fp:
        zxx_fp.write(img_bits)


def create_zxx_file(
    dest_zxx_path: str,
    rom_path: str,
    qimage: QImage,
    image_size: Tuple[int, int],
    image_format: int = QImage.Format_RGB16,
):
    # TODO Check if this rom type is supported
    rom_basename = basename(rom_path)
    _, rom_extension = splitext(rom_path)

    with open(dest_zxx_path, "wb") as zxx_fp:
        # Write thumb content
        if qimage:
            zxx_fp.write(get_bytes_from_qimage(qimage, image_format))
        else:
            zxx_fp.write(bytes(b"\x01" * nb_bytes(image_size, image_format)))

        # Write zip/rom content
        if rom_extension != ".zip":
            # Create zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(
                dest_zxx_path, "w", zipfile.ZIP_DEFLATED, False
            ) as zipf:
                zipf.write(rom_path, arcname=rom_basename)

            zxx_fp.write(zip_buffer.getvalue())
        else:
            # if already zipped, just copy content
            with open(rom_path, "rb") as rom_fp:
                zxx_fp.write(rom_fp.read())

    logging.info(f"Zxx file `{dest_zxx_path}` created successfully.")
