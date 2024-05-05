# GUI imports
import hashlib
import json
import logging

# OS imports
import os
import shutil

# feature imports
import struct
import zipfile
from io import BytesIO

import requests
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import frogtool
from utils.image_utils import create_zxx_file, get_bytes_from_qimage, load_as_qimage

offset_logo_presequence = [
    0x62,
    0x61,
    0x64,
    0x5F,
    0x65,
    0x78,
    0x63,
    0x65,
    0x70,
    0x74,
    0x69,
    0x6F,
    0x6E,
    0x00,
    0x00,
    0x00,
]
offset_buttonMap_presequence = [
    0x00,
    0x00,
    0x00,
    0x71,
    0xDB,
    0x8E,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
]
offset_buttonMap_postsequence = [
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01,
    0x00,
    0x00,
    0x00,
    0x01,
    0x00,
    0x00,
    0x00,
    0x02,
    0x00,
    0x00,
    0x00,
    0x02,
    0x00,
    0x00,
    0x00,
]


def findSequence(needle, haystack, offset=0):
    # Loop through the data array starting from the offset
    for i in range(len(haystack) - offset - len(needle) + 1):
        readpoint = offset + i
        # Assume a match until proven otherwise
        match = True
        # Loop through the target sequence and compare each byte
        for j in range(len(needle)):
            if haystack[readpoint + j] != needle[j]:
                # Mismatch found, break the inner loop and continue the outer loop
                match = False
                break
        # If match is still true after the inner loop, we have found a match
        if match:
            # Return the index of the first byte of the match
            return readpoint
    # If we reach this point, no match was found
    return -1


def bisrv_getFirmwareVersion(index_path):
    print(f"trying to read {index_path}")
    try:
        file_handle = open(index_path, "rb")  # rb for read, wb for write
        bisrv_content = bytearray(file_handle.read(os.path.getsize(index_path)))
        file_handle.close()
        print("Finished reading file")
        # First, replace CRC32 bits with 00...
        bisrv_content[396] = 0x00
        bisrv_content[397] = 0x00
        bisrv_content[398] = 0x00
        bisrv_content[399] = 0x00
        print("Blanked CRC32")

        # Next identify the boot logo position, and blank it out too...
        print("start finding logo")
        badExceptionOffset = findSequence(
            offset_logo_presequence, bisrv_content, 10000000
        )  # Set the offset to 10000000 as we know it doesnt occur earlier than that
        print(f"finished finding logo - ({badExceptionOffset})")
        if badExceptionOffset > -1:  # Check we found the boot logo position
            bootLogoStart = badExceptionOffset + 16
            for i in range(bootLogoStart, bootLogoStart + 204800):
                bisrv_content[i] = 0x00
        else:  # If no boot logo found exit
            return False

        print("Blanked Bootlogo")
        print("start finding button mapping")
        # Next identify the emulator button mappings (if they exist), and blank them out too...
        preButtonMapOffset = findSequence(
            offset_buttonMap_presequence, bisrv_content, 9200000
        )
        print(f"found button mapping - ({preButtonMapOffset})")
        if preButtonMapOffset > -1:
            postButtonMapOffset = findSequence(
                offset_buttonMap_postsequence, bisrv_content, preButtonMapOffset
            )
            if postButtonMapOffset > -1:
                for i in range(preButtonMapOffset + 16, i < postButtonMapOffset):
                    bisrv_content[i] = 0x00
            else:
                return False
        else:
            return False
        print("finished finding button mapping")
        # Next we'll look for (and zero out) the five bytes that the power
        # monitoring functions of the SF2000 use for switching the UI's battery
        # level indicator. These unfortunately can't be searched for - they're just
        # in specific known locations for specific firmware versions...
        print("start finding powercurve")
        prePowerCurve = findSequence(
            [0x11, 0x05, 0x00, 0x02, 0x24], bisrv_content, 3000000
        )
        print(f"found pre-powercurve - ({prePowerCurve})")
        if prePowerCurve > -1:
            powerCurveFirstByteLocation = prePowerCurve + 5
            if powerCurveFirstByteLocation == 0x35A8F8:
                # Seems to match mid-March layout...
                bisrv_content[0x35A8F8] = 0x00
                bisrv_content[0x35A900] = 0x00
                bisrv_content[0x35A9B0] = 0x00
                bisrv_content[0x35A9B8] = 0x00
                bisrv_content[0x35A9D4] = 0x00

            elif powerCurveFirstByteLocation == 0x35A954:
                # Seems to match April 20th layout...
                bisrv_content[0x35A954] = 0x00
                bisrv_content[0x35A95C] = 0x00
                bisrv_content[0x35AA0C] = 0x00
                bisrv_content[0x35AA14] = 0x00
                bisrv_content[0x35AA30] = 0x00

            elif powerCurveFirstByteLocation == 0x35C78C:
                # Seems to match May 15th layout...
                bisrv_content[0x35C78C] = 0x00
                bisrv_content[0x35C794] = 0x00
                bisrv_content[0x35C844] = 0x00
                bisrv_content[0x35C84C] = 0x00
                bisrv_content[0x35C868] = 0x00

            elif powerCurveFirstByteLocation == 0x35C790:
                # Seems to match May 22nd layout...
                bisrv_content[0x35C790] = 0x00
                bisrv_content[0x35C798] = 0x00
                bisrv_content[0x35C848] = 0x00
                bisrv_content[0x35C850] = 0x00
                bisrv_content[0x35C86C] = 0x00

            elif powerCurveFirstByteLocation == 0x3564EC:
                # Seems to match August 3rd layout...
                bisrv_content[0x3564EC] = 0x00
                bisrv_content[0x3564F4] = 0x00
                bisrv_content[0x35658C] = 0x00
                bisrv_content[0x356594] = 0x00
                bisrv_content[0x3565B0] = 0x00

            elif powerCurveFirstByteLocation == 0x356638:
                # Seems to match October 7th/13th layout...
                bisrv_content[0x356638] = 0x00
                bisrv_content[0x356640] = 0x00
                bisrv_content[0x3566D8] = 0x00
                bisrv_content[0x3566E0] = 0x00
                bisrv_content[0x3566FC] = 0x00
            else:
                return False
        else:
            return False

        # Next we'll look for and zero out the bytes used for SNES audio rate and
        # CPU cycles, in case folks want to patch those bytes to correct SNES
        # first-launch issues on newer firmwares...
        # Location: Approximately 0xC0A170 (about 99% of the way through the file)
        preSNESBytes = findSequence(
            [0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x80], bisrv_content, 12500000
        )
        print(f"found pre SNES fix bytes - ({preSNESBytes})")
        if preSNESBytes > -1:
            snesAudioBitrateBytes = preSNESBytes + 8
            snesCPUCyclesBytes = snesAudioBitrateBytes + 8
            bisrv_content[snesAudioBitrateBytes] = 0x00
            bisrv_content[snesAudioBitrateBytes + 1] = 0x00
            bisrv_content[snesCPUCyclesBytes] = 0x00
            bisrv_content[snesCPUCyclesBytes + 1] = 0x00
        else:
            return False

        # If we're here, we've zeroed-out all of the bits of the firmware that are
        # semi-user modifiable (boot logo, button mappings and the CRC32 bits); now
        # we can generate a hash of what's left and compare it against some known
        # values...
        print("starting to compute hash")
        sha256hasher = hashlib.new("sha256")
        sha256hasher.update(bisrv_content)
        bisrvHash = sha256hasher.hexdigest()
        print(f"Hash: {bisrvHash}")
        version = versionDictionary.get(bisrvHash)
        return version

    except (IOError, OSError):
        print("! Failed reading bisrv.")
        print(
            "  Check the SD card and file are readable, and the file is not open in another program."
        )
        raise Exception_InvalidPath


# Thanks to Dteyn for putting the python together from here: https://github.com/Dteyn/SF2000_Battery_Level_Patcher/blob/master/main.py
# Thanks to OpenAI for writing the class and converting logging to prints
class BatteryPatcher:
    def __init__(self, firmware_file, fw_version):

        self.fw_version = fw_version
        # Filename of original firmware file to open
        self.firmware_file = firmware_file
        # Filename of patched firmware file to save
        self.patched_file = firmware_file

        # Define voltage values for each battery level (user can modify these)
        self.VOLTAGE_LEVELS = {
            "5 bars": 4.0,  # Full charge
            "4 bars": 3.88,
            "3 bars": 3.80,
            "2 bars": 3.72,
            "1 bar (red)": 3.66,  # Near empty
        }

        # Offset addresses for each battery level - firmware 08.03
        self.ADDRESSES_V1_6 = [
            0x3564EC,  # 5 bars (full charge)
            0x3564F4,  # 4 bars
            0x35658C,  # 3 bars
            0x356594,  # 2 bars (yellow)
            0x3565B0,  # 1 bar (red)
        ]

        # Offset addresses for each battery level - firmware v1.71
        self.ADDRESSES_V1_71 = [
            0x356638,  # 5 bars (full charge)
            0x356640,  # 4 bars
            0x3566D8,  # 3 bars
            0x3566E0,  # 2 bars (yellow)
            0x3566FC,  # 1 bar (red)
        ]

        # Stock values for sanity check
        self.STOCK_VALUES = [0xBF, 0xB7, 0xAF, 0xA9, 0xA1]

        # New values for sanity check
        self.BATTERY_FIX_VALUES = [0xC8, 0xC2, 0xBE, 0xBA, 0xB7]

    def voltage_to_value(self, voltage):
        """Convert voltage to the appropriate firmware value using the 50x multiplier."""
        return int(voltage * 50)

    def calculate_crc32(self, data):
        """
        Calculate the CRC32 value for the given data.
        Credit to @bnister for the C version of this code (translated to Python by GPT-4)
        """
        tab_crc32 = [(i << 24) & 0xFFFFFFFF for i in range(256)]
        for i in range(256):
            c = tab_crc32[i]
            for _ in range(8):
                c = (c << 1) ^ 0x4C11DB7 if (c & (1 << 31)) else c << 1
                c &= 0xFFFFFFFF
            tab_crc32[i] = c

        c = ~0 & 0xFFFFFFFF
        for i in range(512, len(data)):
            c = (c << 8) ^ tab_crc32[((c >> 24) ^ data[i]) & 0xFF]
            c &= 0xFFFFFFFF
        return c

    def check_patch_applied(self):
        with open(self.firmware_file, "rb") as f:
            bisrv_data = bytearray(f.read())
            logging.info("File '%s' opened successfully." % self.firmware_file)
        # TODO add error checking
        ADDRESSES = self.get_ADRESSES()
        if not ADDRESSES:
            return False
        for addr, expected_value in zip(ADDRESSES, self.BATTERY_FIX_VALUES):
            if bisrv_data[addr] != expected_value:
                logging.info(
                    "The firmware does not match the expected battery patched versions at offset %X. "
                )
                return False
        logging.info(
            "The firmware matched the expected battery patched versions at offset %X."
            % addr
        )
        return True

    def get_ADRESSES(self):
        if self.fw_version == version_displayString_1_6:
            return self.ADDRESSES_V1_6
        elif self.fw_version == version_displayString_1_71:
            return self.ADDRESSES_V1_71
        else:
            logging.warn(
                "BatteryPatcher~check_latest_firmware: Firmware version mismatch"
            )
            return False

    def check_latest_firmware(self):
        # TODO: Replace this with a proper check
        """
        Check if the firmware matches the patched values
        """
        with open(self.firmware_file, "rb") as f:
            bisrv_data = bytearray(f.read())
            logging.info("File '%s' opened successfully." % self.firmware_file)
        ADDRESSES = self.get_ADRESSES()
        if not ADDRESSES:
            return False
        for addr, expected_value in zip(ADDRESSES, self.STOCK_VALUES):
            if bisrv_data[addr] != expected_value:
                print(
                    "The firmware does not match the expected '08.03' version at offset %X. "
                    "Please check the offsets." % addr
                )
                return False
        logging.info(
            "The firmware matched the expected firmware versions at offset %X." % addr
        )
        return True

    def patch_firmware(self, progressIndicator):
        """
        Patch the firmware file with new battery values and update its CRC32.
        """
        try:
            progressIndicator.setValue(1)
            QApplication.processEvents()
            with open(self.firmware_file, "rb") as f:
                bisrv_data = bytearray(f.read())
            print("File '%s' opened successfully." % self.firmware_file)

            # Perform sanity check
            if not self.check_latest_firmware():
                return
            ADDRESSES = self.get_ADRESSES()
            if not ADDRESSES:
                return False
            # Convert voltage levels to firmware values
            self.BATTERY_VALUES = {
                addr: self.voltage_to_value(self.VOLTAGE_LEVELS[bar])
                for addr, bar in zip(ADDRESSES, self.VOLTAGE_LEVELS)
            }
            # Patch the battery values
            for addr, value in self.BATTERY_VALUES.items():
                bisrv_data[addr] = value
            print("File patched with new battery values.")
            progressIndicator.setValue(10)
            QApplication.processEvents()

            # Calculate new CRC32
            print("Calculating new CRC32...")
            crc = self.calculate_crc32(bisrv_data)
            print("New CRC32 value: %X" % crc)
            progressIndicator.setValue(80)
            QApplication.processEvents()
            # Update CRC32 in the bisrv_data
            bisrv_data[0x18C] = crc & 0xFF
            bisrv_data[0x18D] = (crc >> 8) & 0xFF
            bisrv_data[0x18E] = (crc >> 16) & 0xFF
            bisrv_data[0x18F] = (crc >> 24) & 0xFF

            # Write the patched data back to the file
            with open(self.patched_file, "wb") as f:
                f.write(bisrv_data)
            print("Patched data written back to '%s'." % self.patched_file)
            return True
        except FileNotFoundError:
            print("File '%s' not found." % self.firmware_file)
            return False
        except Exception as e:
            print("An error occurred: %s" % str(e))
            return False


def changeBootLogo(bios_path, newLogoFileName, msgBox):
    # Confirm we arent going to brick the firmware by finding a known version
    sfVersion = bisrv_getFirmwareVersion(bios_path)
    print(f"Found Version: {sfVersion}")
    if sfVersion == None:
        return False
    # Load the new Logo
    msgBox.setText("Loading new boot logo...")
    msgBox.showProgress(25, True)
    newLogo = QImage(newLogoFileName)

    # Convert to RGB565 and increase the size to 512x200
    msgBox.setText("Converting boot logo...")
    msgBox.showProgress(40, True)
    newLogo = newLogo.scaled(512, 200, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    rgb565Data = get_bytes_from_qimage(newLogo, QImage.Format_RGB16)

    # Seek logo sequence. Logo is 16 bytes after offset_logo_presequence
    msgBox.setText("Seek logo sequence in BIOS file...")
    msgBox.showProgress(60, True)
    with open(bios_path, "rb") as fp:
        bisrv_content = bytearray(fp.read())
    logoOffset = findSequence(offset_logo_presequence, bisrv_content, 10000000)
    bootLogoStart = logoOffset + 16

    # Change the boot logo
    msgBox.setText("Updating BIOS file...")
    msgBox.showProgress(80, True)
    bisrv_content[bootLogoStart : bootLogoStart + newLogo.byteCount()] = rgb565Data
    bisrv_content = patchCRC32(bisrv_content)

    msgBox.setText("Saving updated BIOS file...")
    msgBox.showProgress(90, True)
    with open(bios_path, "wb") as fp:
        fp.write(bisrv_content)
    msgBox.showProgress(99, True)
    return True


def patchCRC32(bisrv_content):
    x = crc32mpeg2(bisrv_content[512 : len(bisrv_content) : 1])
    bisrv_content[0x18C] = x & 255
    bisrv_content[0x18D] = x >> 8 & 255
    bisrv_content[0x18E] = x >> 16 & 255
    bisrv_content[0x18F] = x >> 24
    return bisrv_content


def crc32mpeg2(buf, crc=0xFFFFFFFF):
    for val in buf:
        crc ^= val << 24
        for _ in range(8):
            crc = crc << 1 if (crc & 0x80000000) == 0 else (crc << 1) ^ 0x104C11DB7
    return crc
