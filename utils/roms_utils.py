import io
import logging
import struct
import zipfile
from pathlib import Path

from PyQt5.QtGui import QImage

from .image_utils import Size, get_bytes_from_qimage, nb_bytes, write_qimage


def get_qimage_from_zxx(
    zxx_rom_path: Path, image_size: Size, image_format: int
) -> QImage:
    """
    Extracts image from the rom and passes to load image function.
    """
    with zxx_rom_path.open("rb") as rom_file:
        image_content = rom_file.read(nb_bytes(image_size, image_format))

    return QImage(image_content, *image_size, image_format)


def replace_thumb_in_zxx(
    zxx_rom_path: str, qimage: QImage, image_size: Size, image_format: int
) -> QImage:
    img_bits = get_bytes_from_qimage(qimage, image_format)
    if len(img_bits) != nb_bytes(image_size, image_format):
        raise ValueError(f"Invalid image size for {image_format}.")

    with open(zxx_rom_path, "wb") as zxx_fp:
        zxx_fp.write(img_bits)


def create_zfb_file(
    zfb_path: Path,
    rom_string: str,
    qimage: QImage,
    image_size: Size,
    image_format: int = QImage.Format_RGB16,
):
    with zfb_path.open("wb") as zfb_fp:
        write_qimage(zfb_fp, qimage, image_size, image_format)

        zfb_fp.write(b"\x00\x00\x00\x00")
        zfb_fp.write(rom_string.encode())
        zfb_fp.write(b"\x00\x00")

    logging.info(f"ZFB file `{zfb_path.name}` created successfully.")


def get_rompath_from_zfb(zfb_path: Path, image_size: Size, image_format: int) -> Path:
    with zfb_path.open("rb") as zfb_fp:
        zfb_fp.seek(nb_bytes(image_size, image_format) + 4)
        name = zfb_fp.read()

    return name[:-2].decode()


def create_zxx_file(
    zxx_path: Path,
    rom_path: Path,
    qimage: QImage,
    image_size: Size,
    image_format: int = QImage.Format_RGB16,
):
    with zxx_path.open("wb") as zxx_fp:
        # Write thumb content
        write_qimage(zxx_fp, qimage, image_size, image_format)

        # Write zip/rom content
        if rom_path.suffix != ".zip":
            # Create zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zipf:
                zipf.write(rom_path, arcname=rom_path.name)

            zxx_fp.write(zip_buffer.getvalue())
        else:
            # if already zipped, just copy content
            with open(rom_path, "rb") as rom_fp:
                zxx_fp.write(rom_fp.read())

    logging.info(f"Zxx file `{zxx_path.name}` created successfully.")


def write_index_file(index_path: Path, content_list: list[str], backup: bool = True):
    # build up the list of names in that order as a byte string, and also build a list of pointers
    pointers = []
    names_bytes = b""
    for item in content_list:
        pointers.append(len(names_bytes))
        names_bytes += item.encode("utf-8") + b'\x00'
    
    # build the metadata - first value is the total count of games in this list
    metadata_bytes = struct.pack('>I', len(content_list))

    # build the pointers structure
    for pointer in pointers:
        metadata_bytes += struct.pack('>I', pointer)
    
    if backup:
        # backup the original index file
        orig_index_path = index_path.with_suffix(".orig")
        if not orig_index_path.exists():
            index_path.rename(orig_index_path)

    # write the index file
    with index_path.open("wb") as fp:
        fp.write(metadata_bytes)
        fp.write(names_bytes)
