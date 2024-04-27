import binascii
import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)

systems = {
    "ARCADE": ["mswb7.tax", "msdtc.nec", "mfpmp.bvs"],
    "FC": ["rdbui.tax", "fhcfg.nec", "nethn.bvs"],
    "GB": ["vdsdc.tax", "umboa.nec", "qdvd6.bvs"],
    "GBA": ["vfnet.tax", "htuiw.nec", "sppnp.bvs"],
    "GBC": ["pnpui.tax", "wjere.nec", "mgdel.bvs"],
    "MD": ["scksp.tax", "setxa.nec", "wmiui.bvs"],
    "SFC": ["urefs.tax", "adsnt.nec", "xvb6c.bvs"],
}

supported_rom_ext = [
    "bkp",
    "zip",
    "zfc",
    "zsf",
    "zmd",
    "zgb",
    "zfb",
    "smc",
    "fig",
    "sfc",
    "gd3",
    "gd7",
    "dx2",
    "bsx",
    "swc",
    "nes",
    "nfc",
    "fds",
    "unf",
    "gba",
    "agb",
    "gbz",
    "gbc",
    "gb",
    "sgb",
    "bin",
    "md",
    "smd",
    "gen",
    "sms",
]

supported_zip_ext = ["bkp", "zip"]


class StopExecution(Exception):
    pass


def int_to_4_bytes_reverse(src_int):
    hex_string = format(src_int, "x").rjust(8, "0")[0:8]
    return binascii.unhexlify(hex_string)[::-1]  # reverse it


def file_entry_to_name(file_entry):
    return file_entry.name


def check_file(file_entry, supported_exts):
    file_regex = ".+\\.(" + "|".join(supported_exts) + ")$"
    return file_entry.is_file() and re.search(file_regex, file_entry.name.lower())


def check_rom(file_entry):
    return check_file(file_entry, supported_rom_ext)


def check_zip(file_entry):
    return check_file(file_entry, supported_zip_ext)


def strip_file_extension(name):
    parts = name.split(".")
    parts.pop()
    return ".".join(parts)


def sort_normal(unsorted_list):
    return sorted(unsorted_list)


def sort_without_file_ext(unsorted_list):
    stripped_names = list(map(strip_file_extension, unsorted_list))
    sort_map = dict(zip(unsorted_list, stripped_names))
    return sorted(sort_map, key=sort_map.get)


def getROMList(roms_path):
    if not os.path.isdir(roms_path):
        logger.debug(f"! Couldn't find folder {roms_path}")
        logger.debug("  Check the provided path points to an SF2000 SD card!")
        raise StopExecution
    files = os.scandir(roms_path)
    files = list(filter(check_rom, files))
    filenames = list(map(file_entry_to_name, files))
    return filenames


def process_sys(drive, system, test_mode):
    logger.debug(f"Processing {system}")

    roms_path = os.path.join(drive, system)
    filenames = getROMList(roms_path)

    index_path_files = os.path.join(drive, "Resources", systems[system][0])
    index_path_cn = os.path.join(drive, "Resources", systems[system][1])
    index_path_pinyin = os.path.join(drive, "Resources", systems[system][2])
    check_and_back_up_file(index_path_files)
    check_and_back_up_file(index_path_cn)
    check_and_back_up_file(index_path_pinyin)

    logger.debug(f"Looking for files in {roms_path}")

    # Bugfix: get new filenames now that we have converted from zip to zxx
    filenames = getROMList(roms_path)
    no_files = len(filenames)
    if no_files == 0:
        logger.debug("No ROMs found! Going to save an empty file list")
        # return f"No ROMs found to rebuild in {system}"

    stripped_names = list(map(strip_file_extension, filenames))

    # prepare maps of filenames to index name for the 3 index files
    # for "files" we just want the actual filenames as both key and value, the menu will strip the extensions
    name_map_files = dict(zip(filenames, filenames))
    # for the Chinese names and pinyin initials, i'm not supporting that at the moment, so use the English titles
    # but use the stripped versions because the menu will not strip them here
    name_map_cn = dict(zip(filenames, stripped_names))
    name_map_pinyin = dict(zip(filenames, stripped_names))

    write_index_file(name_map_files, sort_without_file_ext, index_path_files, test_mode)
    write_index_file(name_map_cn, sort_normal, index_path_cn, test_mode)
    write_index_file(name_map_pinyin, sort_normal, index_path_pinyin, test_mode)

    logger.debug("Done\n")
    return f"Finished updating {system} with {no_files} ROMs"


def find_matching_file_diff_ext(target, files):
    target_no_ext = strip_file_extension(target.name)
    for file in files:
        file_no_ext = strip_file_extension(file.name)
        if file_no_ext == target_no_ext:
            return file


def check_and_back_up_file(file_path):
    if not os.path.exists(file_path):
        logger.debug(f"! Couldn't find game list file {file_path}")
        logger.debug("  Check the provided path points to an SF2000 SD card!")
        raise StopExecution

    if not os.path.exists(f"{file_path}_orig"):
        logger.debug(f"Backing up {file_path} as {file_path}_orig")
        try:
            shutil.copyfile(file_path, f"{file_path}_orig")
        except (OSError, IOError):
            logger.debug("! Failed to copy file.")
            logger.debug("  Check the SD card and Resources directory are writable.")
            raise StopExecution


def write_index_file(name_map, sort_func, index_path, test_mode):
    # entries must maintain a consistent order between all indexes, but what that order actually is doesn't matter
    # so use alphabetised filenames for this
    sorted_filenames = sorted(name_map.keys())
    # build up the list of names in that order as a byte string, and also build a dict of pointers to each name
    names_bytes = b""
    pointers_by_name = {}
    for filename in sorted_filenames:
        display_name = name_map[filename]
        current_pointer = len(names_bytes)
        pointers_by_name[display_name] = current_pointer
        names_bytes += display_name.encode("utf-8") + chr(0).encode("utf-8")

    # build the metadata - first value is the total count of games in this list
    metadata_bytes = int_to_4_bytes_reverse(len(name_map))
    # the rest are pointers to the display names in the desired display order
    # so sort display names according to the display order, and build a list of pointers in that order
    sorted_display_names = sort_func(name_map.values())
    sorted_pointers = map(lambda name: pointers_by_name[name], sorted_display_names)
    for current_pointer in sorted_pointers:
        metadata_bytes += int_to_4_bytes_reverse(current_pointer)

    new_index_content = metadata_bytes + names_bytes

    if test_mode:
        logger.debug(f"Checking {index_path}")
        file_handle = open(index_path, "rb")
        existing_index_content = file_handle.read(os.path.getsize(index_path))
        file_handle.close()
        if existing_index_content != new_index_content:
            logger.debug("! Doesn't match")
        return

    logger.debug(f"Overwriting {index_path}")
    try:
        file_handle = open(index_path, "wb")
        file_handle.write(new_index_content)
        file_handle.close()
    except (IOError, OSError):
        logger.debug("! Failed overwriting file.")
        logger.debug(
            "  Check the SD card and file are writable, and the file is not open in another program."
        )
        raise StopExecution


def check_sys_valid(system):
    return system and (system in systems.keys() or system == "ALL")
