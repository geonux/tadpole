# GUI imports
import hashlib
import json
import logging

# OS imports
import os
import shutil

#feature imports
import struct
import zipfile
from io import BytesIO

import requests
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from frog_config import zxx_exts
from utils.image_utils import get_rompath_from_zfb

try:
    from PIL import Image, ImageDraw, ImageFont
    image_lib_avail = True
except ImportError:
    Image = None
    ImageDraw = None
    image_lib_avail = False

logger = logging.getLogger(__name__)


supported_save_ext = [
    "sav", "sa0", "sa1", "sa2", "sa3"
] 

version_displayString_1_5 = "2023.04.20 (V1.5)"
version_displayString_1_6 = "2023.08.03 (V1.6)"
version_displayString_1_7 = "2023.10.07 (V1.7)"
version_displayString_1_71 ="2023.10.13 (V1.71)"
# hash, versionName
versionDictionary = {
    "151d5eeac148cbede3acba28823c65a34369d31b61c54bdd8ad049767d1c3697": version_displayString_1_5,
    "5335860d13214484eeb1260db8fe322efc87983b425ac5a5f8b0fcdf9588f40a": version_displayString_1_6,
    "b88458bf2c25d3a34ab57ee149f36cfdc6b8a5138d5c6ed147fbea008b4659db": version_displayString_1_7,
    "08bd07ab3313e3f00b922538516a61b5846cde34c74ebc0020cd1a0b557dd54b": version_displayString_1_71
}

ROMART_baseURL = "https://raw.githubusercontent.com/EricGoldsteinNz/libretro-thumbnails/master/"

ROMArt_console = {  
    "FC":     "Nintendo - Nintendo Entertainment System",
    "SFC":    "Nintendo - Super Nintendo Entertainment System",
    "MD":     "Sega - Mega Drive - Genesis",
    "GB":     "Nintendo - Game Boy",
    "GBC":    "Nintendo - Game Boy Color",
    "GBA":    "Nintendo - Game Boy Advance", 
    "ARCADE": ""
}

class Exception_InvalidPath(Exception):
    pass    

class InvalidURLError(Exception):
    pass

class Exception_InvalidConsole(Exception):
    pass

def changeGameShortcut(drive, rom_path, menu_id, position):
    """
    Create game shortcut

    drive should be the Drive of the Frog card only. It must inlude the semicolon if relevant. ie "E:"
    rom_path should be the full file path including the drive letter.
    menu_id is a 0-based id of the menu to store the shortcut. values 0 to 9 are considered valid.
    position is a 0-based index of the short. values 0 to 3 are considered valid.
    """
    # Check the passed variables for validity
    if not(0 <= position <= 3):
        raise Exception_InvalidPath
    if menu_id > 8:
        raise Exception_InvalidConsole

    # Extract the real name of the rom to start
    if rom_path.lower().endwidth(".zfb"):
        game = get_rompath_from_zfb(rom_path)
    else:
        game = os.path.basename(rom_path)

    try:
        #Read in all the existing shortcuts from file
        xfgle_filepath = os.path.join(drive, "Resources", "xfgle.hgp")
        with open(xfgle_filepath, "r", encoding="utf-8") as fh:
            lines = fh.readlines()

        # Check that xfgle had the correct number of lines, if it didnt we will need to fix it.
        if lines == 0:
            raise IOError

        # Overwrite the one line we want to change
        lines[4*menu_id+position] = f"{menu_id} {game}*\n"

        # Save the changes out to file
        with open(xfgle_filepath, "w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line)
  
    except (OSError, IOError) as e:
        logger.error(f"Tadpole_functions~changeGameShortcut: Failed changing the shortcut file. {str(e)}")
        return False
  
    return -1


#returns the position of the game's shortcut on the main screen.  If it isn't a shortcut, it returns 0  
def getGameShortcutPosition(drive, console, game):
        
    try:
        gamePath = os.path.join(drive, console, game)
        #Read in all the existing shortcuts from file
        xfgle_filepath = os.path.join(drive, "Resources", "xfgle.hgp")
        xfgle_file_handle = open(xfgle_filepath, "r")
        lines = xfgle_file_handle.readlines()
        xfgle_file_handle.close()
        prefix = getPrefixFromConsole(console)
        #Arcade is special; the actual game name is embedded in the ZFB
        if(console == "ARCADE" ):
            game = get_rompath_from_zfb(gamePath)             
        savedShortcut = f"{prefix} {game}*\n"
        # see if this game is listed.  If so get its position
        for i, gameShortcutLine in enumerate(lines):
            if gameShortcutLine == savedShortcut:
                logger.debug("Found " + savedShortcut + "as shortcut")
                #now we found the match of the raw location, now we need to return the position from console
                #from xfgle, the positions start with 3 random lines, and then go down in order from FC -> SNES -> ... -> Arcade
                if(console == "FC" ):
                    return (i - 3)
                if(console == "SFC" ):
                    return (i - 7)
                if(console == "MD" ):
                    return (i - 11)
                if(console == "GB" ):
                    return (i - 15)
                if(console == "GBC" ):
                    return (i - 19)
                if(console == "GBA" ):
                    return (i - 23)
                if(console == "ARCADE" ):
                    return (i - 27)
        return 0      
    except (OSError, IOError):
        logger.debug(f"! Failed changing the shortcut file")
        return 0

#Although not required, if you don't have seperate prefixes, games with same ROM names/extension
# e.g. Gameboy, gameboy color, and gameboy advance can get confused when loading the shortcuts in other systems.  
def getPrefixFromConsole(console):
    if console == "FC":  
        return 1
    elif console == "SFC": 
        return 2
    elif console == "MD":  
        return 3
    elif console == "GB":  
        return 4
    elif console == "GBC":
        return 5
    elif console == "GBA":
        return 7
    else:  
        return 6 #Aracde NEEDS 6 so always default to that


    
"""
This function is used to check if the supplied path has relevant folders and files for an SF2000 SD card. 
This should be used to prevent people from accidentally overwriting their other drives.
If the correct files are found it will return True.
If the correct files are not found it will return False.
"""
def checkDriveLooksFroggy(froggypath):
    bisrvpath = os.path.join(froggypath,"bios","bisrv.asd")
    if os.path.exists(bisrvpath):
        return True
    return False




def get_background_music(url="https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/BackgroundMusic"):
    """gets index of background music from provided GitHub API URL"""
    music = {}
    response = requests.get(url)

    if response.status_code == 200:
        data = json.loads(response.content)
        for item in data:
            music[item['name'].replace(".bgm", "")] = item['download_url']
        return music
    raise ConnectionError("Unable to obtain music resources. (Status Code: {})".format(response.status_code))

def get_themes(url="https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/Themes") -> bool:
    """gets index of theme from provided GitHub API URL"""
    theme = {}
    response = requests.get(url)

    if response.status_code == 200:
        data = json.loads(response.content)
        for item in data:
            theme[item['name'].replace(".zip", "")] = item['download_url']
        return theme
    raise ConnectionError("Unable to obtain theme resources. (Status Code: {})".format(response.status_code))

def get_boot_logos(url="https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/BootLogos") -> bool:
    """gets index of theme from provided GitHub API URL"""
    bootlogos = {}
    response = requests.get(url)

    if response.status_code == 200:
        data = json.loads(response.content)
        for item in data:
            bootlogos[item['name'].replace(".zip", "")] = item['download_url']
        return bootlogos
    raise ConnectionError("Unable to obtain boot logo resources. (Status Code: {})".format(response.status_code))


"""
This function downloads a file from the internet and renames it to pagefile.sys to replace the background music.
"""

def changeBackgroundMusic(drive_path: str, url: str = "", file: str = "") -> bool:
    """
    Changes background music to music from the provided URL or file

    Params:
        url (str):  URL to music file to use for replacement.
        file (str):  Full path to a local file to use for replacement.

    Returns:
        bool: True if successful, False if not.

    Raises:
        ValueError: When both url and file params are provided.
    """
    if url and not file:
        return downloadAndReplace(drive_path, os.path.join("Resources","pagefile.sys"), url)
    elif file and not url:
        try:
            shutil.copyfile(file, os.path.join(drive_path, "Resources", "pagefile.sys"))
            return True
        except:
            return False
    else:
        raise ValueError("Provide only url or path, not both")

"""
This function downloads a file from the internet and downloads it to resources.
"""


def changeTheme(drive_path: str, url: str = "", file: str = "", progressBar: QProgressBar = "") -> bool:
    """
    Changes background theme from the provided URL or file

    Params:
        url (str):  URL to theme files to use for replacement.
        file (str):  Full path to a zip file to use for replacement.
        ProgressBar: address of the progressbar to update on screen
    Returns:
        bool: True if successful, False if not.

    Raises:
        ValueError: When both url and file params are provided.
    """
    # TODO do this in memory instead
    if url and not file:
        zip_file = "theme.zip"
        downloadFileFromGithub(zip_file, url)
        try:
            with zipfile.ZipFile(zip_file) as zip:
                progressBar.setMaximum(len(zip.infolist()))
                progress = 6
                #TODO: Hacky but assume any zip folder with more than 55 files is not a theme zip
                if len(zip.infolist()) > 55:
                    return False
                for zip_info in zip.infolist():     
                    #logger.debug(zip_info)
                    if zip_info.is_dir():
                        continue
                    zip_info.filename = os.path.basename(zip_info.filename)
                    progress += 1
                    progressBar.setValue(progress)
                    QApplication.processEvents()
                    resourcePath = os.path.join(drive_path, "Resources")
                    zip.extract(zip_info, resourcePath)
                    #Cleanup temp zip file
            if os.path.exists(zip_file):
                    os.remove(zip_file)   
            return True
        except:
            if os.path.exists(zip_file):
                os.remove(zip_file)   
            return False

        return True
    elif file and not url:
        try:
            with zipfile.ZipFile(file) as zip:
                progressBar.setMaximum(len(zip.infolist()))
                progress = 2
                for zip_info in zip.infolist():     
                    #logger.debug(zip_info)
                    if zip_info.is_dir():
                        continue
                    zip_info.filename = os.path.basename(zip_info.filename)
                    progress += 1
                    progressBar.setValue(progress)
                    QApplication.processEvents()
                    #TODO validate this is a real theme...maybe just check a set of files?
                    resourcePath =  os.path.join(drive_path, "Resources")
                    zip.extract(zip_info, resourcePath)
            return True
        except:
            return False
    else:
        raise ValueError("Error updating theme")

def changeConsoleLogos(drivePath, url=""):
    return downloadAndReplace(drivePath, os.path.join("Resources","sfcdr.cpl"), url)    


def downloadAndReplace(drivePath, fileToReplace, url=""):
    try:
        # retrieve bgm from GitHub resources
        content = ""
        if not url == "":
            logger.debug(f"Downloading {fileToReplace} from {url}")
            content = requests.get(url).content

        if not content == "":
            #write the content to file
            bgmPath = os.path.join(drivePath, fileToReplace)
            file_handle = open(bgmPath, 'wb') #rb for read, wb for write
            file_handle.write(content)
            file_handle.close()
        logger.debug ("Finished download and replace successfully")
        return True
    except (OSError, IOError) as error:
        logger.debug("An error occured while trying to download and replace a file.")
        return False
      
def downloadDirectoryFromGithub(location, url, progressBar):
    response = requests.get(url) 
    if response.status_code == 200:
        data = json.loads(response.content)
        downloadTotal = 0
        progressBar.setMaximum(len(data)+1)
        for item in data:
            if item["type"] == "dir":
                #create folder then recursively download
                foldername = item["name"]
                destination = os.path.join(location,foldername)
                logger.debug(f"creating directory if it doesnt exist {destination}")
                os.makedirs(destination, exist_ok=True)
                downloadDirectoryFromGithub(destination, item["url"], progressBar)
            else:# all other cases should be files
                filename = item["name"]
                downloadFileFromGithub(os.path.join(location,filename), item["download_url"])
                downloadTotal += 1
                progressBar.setValue(downloadTotal)
                QApplication.processEvents()
                
        return True
    raise ConnectionError("Unable to V1.5 Update. (Status Code: {})".format(response.status_code))
    return False
    
def downloadFileFromGithub(outFile, url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(outFile, 'wb') as f:
                logger.debug(f'downloading {url} to {outFile}')
                f.write(response.content)
            return True
        else:
            logger.debug("Error when trying to download a file from Github. Response was not code 200")
            raise InvalidURLError
    except Exception as e:
        logger.debug(str(e))
        return False

def downloadAndExtractZIPBar(root, url, progress):
    try:
        logger.info(f"tadpole_functions~downloadAndExtractZIPBar: Downloading ({url}) to extract to ({root})")
        response = requests.get(url, stream=True)
        total_length = int(response.headers.get('content-length'))
        dl = 0
        zip_in_memory = bytearray()
        for data in response.iter_content(chunk_size=4096):
            if data:
                dl += len(data)
                zip_in_memory.extend(data)  
                progress.showProgress(int(100 * dl / total_length), True)
        logger.info(f"tadpole_functions~downloadAndExtractZIPBar: Received {response.status_code} for ({url})")
        if response.status_code == 200:
            progress.setText("Extracting")
            progress.showProgress(0, True)
            zip = zipfile.ZipFile(BytesIO(zip_in_memory))
            zip.extractall(path=root)   
            progress.showProgress(100, True)       
            return True
        else: 
            logger.error("tadpole_functions~downloadAndExtractZIPBar: Problem when trying to download a file from Github. Response was not code 200")
            raise InvalidURLError
    except Exception as e:
        logger.error(f"tadpole_functions~downloadAndExtractZIPBar: ERROR {str(e)}")
    return False

#Keeping this for now as a failsafe, but should remove it to follow the new design structure
def DownloadOSFiles(correct_drive, progress): 
    downloadDirectoryFromGithub(correct_drive,"https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/OS/V1.6", progress)
    #Make the ROM directories
    os.mkdir(os.path.join(correct_drive,"ARCADE"))
    os.mkdir(os.path.join(correct_drive,"ARCADE","bin"))
    os.mkdir(os.path.join(correct_drive,"ARCADE","save"))
    os.mkdir(os.path.join(correct_drive,"ARCADE","skp"))
    os.mkdir(os.path.join(correct_drive,"FC"))
    os.mkdir(os.path.join(correct_drive,"FC","save"))
    os.mkdir(os.path.join(correct_drive,"GB"))
    os.mkdir(os.path.join(correct_drive,"GB","save"))
    os.mkdir(os.path.join(correct_drive,"GBC"))
    os.mkdir(os.path.join(correct_drive,"GBC","save"))
    os.mkdir(os.path.join(correct_drive,"GBA"))
    os.mkdir(os.path.join(correct_drive,"GBA","save"))
    os.mkdir(os.path.join(correct_drive,"MD"))
    os.mkdir(os.path.join(correct_drive,"MD","save"))
    os.mkdir(os.path.join(correct_drive,"SFC"))
    os.mkdir(os.path.join(correct_drive,"SFC","save"))
    os.mkdir(os.path.join(correct_drive,"ROMS"))
    os.mkdir(os.path.join(correct_drive,"ROMS","save")) 
    #Need to delete bisrv.asd again to prevent bootloader bug      
    if os.path.exists(os.path.join(correct_drive,"bios","bisrv.asd")):
        os.remove(os.path.join(correct_drive,"bios","bisrv.asd"))
    #Re-add biserv.asd
    #TODO: Review why we are doing this
    #Jason: Per Dteyn, we need to remove and redownlaod bisrv.asd to clear the known bug bootloader crash
    downloadFileFromGithub(os.path.join(correct_drive,"bios","bisrv.asd"), "https://raw.githubusercontent.com/EricGoldsteinNz/SF2000_Resources/main/OS/V1.6/bios/bisrv.asd")        
    return True



        
def GBABIOSFix(drive: str):
    if drive == "???":
        raise Exception_InvalidPath
    gba_bios_path = os.path.join(drive, "bios", "gba_bios.bin")
    if not os.path.exists(gba_bios_path):
        logger.debug(f"! Couldn't find game list file {gba_bios_path}")
        logger.debug("  Check the provided path points to an SF2000 SD card!")
        raise Exception_InvalidPath
    try:
        gba_folder_path = os.path.join(drive, "GBA", "mnt", "sda1", "bios")
        roms_folder_path = os.path.join(drive, "ROMS", "mnt", "sda1", "bios")
        os.makedirs(gba_folder_path, exist_ok=True)
        os.makedirs(roms_folder_path, exist_ok=True)
        shutil.copyfile(gba_bios_path, os.path.join(gba_folder_path, "gba_bios.bin"))
        shutil.copyfile(gba_bios_path, os.path.join(roms_folder_path, "gba_bios.bin"))
    except (OSError, IOError) as error:
        logger.debug("! Failed to copy GBA BIOS.")
        logger.debug(error)
        raise Exception_InvalidPath
 
def downloadROMArt(console : str, ROMpath : str, game : str, artType: str, realname : str):

    outFile = os.path.join(os.path.dirname(ROMpath),f"{realname}.png")
    if(downloadFileFromGithub(outFile,ROMART_baseURL + ROMArt_console[console] + artType + game)):
        logger.debug(' Downloaded ' + realname + ' ' + ' thumbnail')
        return True    
    else:
        logger.debug(' Could not downlaod ' + realname + ' ' + ' thumbnail')
        return True  
    
def stripShortcutText(drive: str):
    if drive == "???" or drive == "":
        raise Exception_InvalidPath
    gakne_path = os.path.join(drive, "Resources", "gakne.ctp")
    try:
        gakne = open(gakne_path, "rb")
        data = bytearray(gakne.read())
        gakne.close()
        # Gakne is made up of 8 rows of 4 items for a total of 32 items.
        # Each image is 144 x 32. Total image size 576 x 256.
        # To only strip the shortcut text we want to leave the settings menu items. So we have to skip the first 18,432 bytes
        
        for i in range (18432, len(data)):
            data[i-1] = 0x00
        gakne = open(gakne_path, "wb")
        gakne.write(data)
        gakne.close()
        return True
    except (OSError, IOError) as e:
        logger.debug(f"! Failed striping shortcut labels. {e}")
        return False

_static_shortcut_ARCADE = 6

def updateShortcutTextforConsole(drive: str, console: int, game1:str, game2:str, game3:str, game4:str):
    if drive == "???" or drive == "":
        raise Exception_InvalidPath
    if (console < 0 or console > _static_shortcut_ARCADE):
        raise Exception_InvalidConsole
    gakne_path = os.path.join(drive, "Resources", "gakne.ctp")
    try:
        # Gakne is made up of 8 rows of 4 items for a total of 32 items.
        # Each image is 144 x 32. Total image size 576 x 256.
        # To only strip the shortcut text we want to leave the settings menu items. So we have to skip the first 18,432 bytes
        # Console order: FC, SFC, MD, GB, GBC, GBA, ARCADE
        newText = [game1,game2,game3,game4]
        shortcutText = openBRGAasImage(gakne_path)
        replaceMask = Image.new("RGBA", (144, 32), (255, 255, 255, 255))
        fnt = ImageFont.truetype("arial.ttf", 24)
        for i in range(len(newText)):
            #Game Slot 1
            img_g = Image.new("RGBA", (144, 32), (0, 0, 0, 0)) #In the alpha channel 0 is fully transparent, 255 is fully opaque
            ImageDraw.Draw(img_g).text((72,16), newText[i], (255,255,255),font=fnt, anchor="mm")        
            shortcutText.paste(img_g, (144*i,(console+1)*32), replaceMask)

        shortcutText.save("C:\\Users\\OEM\\Documents\\test.png")
        # TODO XXXXXX
        writeImagetoBGRAfile(shortcutText, gakne_path)
        return True
    except (OSError, IOError) as e:
        logger.debug(f"! Failed updating shortcut labels. {e}")
        return False

def openBRGAasImage(inputFile):
    # Read the binary data
    with open(inputFile, 'rb') as file:
        data = file.read()
    # Unpack the BGRA8888 data
    pixels = struct.unpack('>' + ('L' * (len(data) // 4)), data)
    # Convert the BGRA8888 values to RGBA888 format
    rgba8888_pixels = [
            ((pixel & 0x0000FF00) >> 8, (pixel & 0x00FF0000) >> 16, (pixel & 0xFF000000) >> 24, (pixel & 0x000000FF))
            for pixel in pixels
    ]
    # Create an image from the pixels
    width = 576  # Specify the width of the image
    height = len(rgba8888_pixels) // width
    image = Image.new('RGBA', (width, height))
    image.putdata(rgba8888_pixels)
    return image

#TODO why is it all coming out yellow???
def writeImagetoBGRAfile(image:Image, outfile:str):
    try:
        dest_file = open(outfile, "wb")
        image_height = image.size[1]
        image_width = image.size[0]
        pixels = image.load()

        if not pixels:
            logger.error(f"tadpole_functions~writeImagetoBGRAfile: Failed to load image")
            return False
        data = []
        for h in range(image_height):
            for w in range(image_width):
                pixel = pixels[w, h]
                if not type(pixel) is tuple:
                    logger.error(f"! Unexpected pixel type at {w}x{h} from {outfile}")
                    return False
                r = pixel[0]
                g = pixel[1]
                b = pixel[2]
                a = pixel[3]
                bgra = (b) | (g << 16) | (r << 8) | (a << 24)
                data.append(struct.pack('>L', bgra))
        dest_file.write(b''.join(data))
        dest_file.close()
        return True
    except (OSError, IOError):
        logger.error(f"tadpole_functions~writeImagetoBGRAfile: Failed opening image file {outfile} for conversion")
        return False


def createSaveBackup(drive: str, zip_file_name):
    if drive == "???" or drive == "":
        raise Exception_InvalidPath 
    try:
        with zipfile.ZipFile(zip_file_name, 'w') as zip_object:
            for root, dirs, files in os.walk(drive):
                for file in files:
                    if check_is_save_file(file):
                        logger.debug(f"Found save: {file} in {root}")
                        try:
                            zip_object.write(os.path.join(root, file),
                                os.path.relpath(os.path.join(root, file),
                                                os.path.join(drive, '..')))
                        except Exception as e:
                            logger.debug(f"Bad zip file encountered: {os.path.join(root, file)}")
                            continue
        return True
    except Exception as e:
        logger.error({e})
        return False
                     
def check_is_save_file(filename):
    for ext in supported_save_ext:
        if filename.lower().endswith(ext):
            return True
    return False
        


def copy_files(source, destination, progressBar):
    total_files = 0
    for root, dirs, files in os.walk(source):
        total_files += len(files)
    copied_files = 0
    for root, dirs, files in os.walk(source):
        for file in files:
            source_file = os.path.join(root, file)
            destination_file = os.path.join(destination, os.path.relpath(source_file, source))
            os.makedirs(os.path.dirname(destination_file), exist_ok=True)
            with open(source_file, 'rb') as src, open(destination_file, 'wb') as dst:
                while True:
                    data = src.read(8192)
                    if not data:
                        break

                    dst.write(data)
            copied_files += 1
            progressBar.setValue(int((copied_files / total_files) * 100))
            QApplication.processEvents()
