import logging
import shutil
import zipfile
from os.path import splitext
from pathlib import Path

from PyQt5.QtGui import QImage

from utils.image_utils import resize_qimage
from utils.roms_utils import (
    create_zfb_file,
    create_zxx_file,
    get_qimage_from_zxx,
    get_rompath_from_zfb,
    replace_thumb_in_zxx,
    write_index_file,
)

logger = logging.getLogger(__name__)

# Resources
# GB300 : https://nummacway.github.io/gb300/
# SF2000 : https://github.com/vonmillhausen/sf2000?tab=readme-ov-file

# MENU RESSOURCES INDEXES
ENGLISH_ROMLIST = 0  # English ROM Names, used to display the game-lists when the UI language is set to English
CHINESE_ROMLIST = 1  # Chinese translations of the English ROM names, used to display the game-lists when the UI language is set to Chinese. Not all game names are translated
PINYIN_ROMLIST = 2  # Pinyin translations of the English ROM names, used for Chinese language searching. Not all game names are translate
MAIN_MENU_BKG = 3  # Main menu background (640x480 RGB565 Little Endian for SF2000)
GAMELIST_BKG = 4  # Game-list background (640x480 RGB565 Little Endian for SF2000)
GAMELIST_INDICATOR = 5  # Game-list indicator (40x24 RGB565 Little Endian for SF2000)

# File extension doesn't seem to matter much. This mapping table may be useless
zxx_exts = {
    ".zfc": [".nes", ".fds", ".unf", ".nfc"],
    ".zgb": [".gba", ".agb", ".gbz", ".gbc", ".gb", ".sgb"],
    ".zmd": [".md", ".smd", ".gen", ".sms"],
    ".zsf": [".sfc", ".smc", ".fig", ".swc", ".gd3", ".gd7", ".dx2", ".bsx", ".bin"],
    ".zpc": [".pce"],
    ".zfb": [".zip"],
}


# fmt: off
frog_systems = {
    "SF2000": {
        "screen_size": (640, 480),
        "bootscreen_size": (512, 200),
        "image_format": QImage.Format_RGB16,
        "max_menu_items": 10,
        "supported_rom_formats": [".zip", ".zfc", ".zsf", ".zmd",".zgb", ".zfb", ".smc", ".fig", ".sfc", ".gd3", ".gd7",
                                  ".dx2", ".bsx", ".swc",".nes", ".nfc", ".fds", ".unf", ".gbc", ".gb", ".sgb", ".gba",
                                  ".agb", ".gbz", ".bin", ".md", ".smd", ".gen", ".sms"],
        "menu_ressources":  [
            ["rdbui.tax", "fhcfg.nec", "nethn.bvs", "fixas.ctp", "urlkp.bvs", "certlm.msa", ],  # Menu entry #0 : FC
            ["urefs.tax", "adsnt.nec", "xvb6c.bvs", "drivr.ers", "c1eac.pal", "djctq.rsd", ],  # Menu entry #1 : #SFC
            ["scksp.tax", "setxa.nec", "wmiui.bvs", "icuin.cpl", "ihdsf.bke", "dxdiag.bin", ],  # Menu entry #2 : #MD
            ["vdsdc.tax", "umboa.nec", "qdvd6.bvs", "xajkg.hsp", "fltmc.sta", "fvecpl.ai", ],  # Menu entry #3 : #GB
            ["pnpui.tax", "wjere.nec", "mgdel.bvs", "qwave.bke", "cero.phl", "htui.kcc", ],  # Menu entry #4 : #GBC
            ["vfnet.tax", "htuiw.nec", "sppnp.bvs", "irftp.ctp", "efsui.stc", "icm32.dll", ],  # Menu entry #5 : #GBA
            ["mswb7.tax", "msdtc.nec", "mfpmp.bvs", "hctml.ers", "apisa.dlk", "msgsm.dll",],  # Menu entry #6 : #ARCADE
            ["NONE", "NONE.nec", "NONE.bvs", "", "", ""],  # Menu entry #7 :
            ["", "", "", "", "dsuei.cpl", "qasf.bel"],  # Users ROMS
        ],
        "bios": [
            
        ]
    },
    "GB300":{
        "screen_size": (640, 480),
        "bootscreen_size": (512, 200),
        "image_format": QImage.Format_RGB16,
        "max_menu_items": 10,
        "menu_ressources":  [
            ["rdbui.tax", "fhcfg.nec", "nethn.bvs"],  # Menu entry #0 : FC
            ["urefs.tax", "adsnt.nec", "xvb6c.bvs"],  # Menu entry #1 : #SFC
            ["scksp.tax", "setxa.nec", "wmiui.bvs"],  # Menu entry #2 : #MD
            ["vdsdc.tax", "umboa.nec", "qdvd6.bvs"],  # Menu entry #3 : #GB
            ["pnpui.tax", "wjere.nec", "mgdel.bvs"],  # Menu entry #4 : #GBC
            ["vfnet.tax", "htuiw.nec", "sppnp.bvs"],  # Menu entry #5 : #GBA
            ["mswb7.tax", "msdtc.nec", "mfpmp.bvs"],  # Menu entry #6 : #ARCADE
        ]
    },
    "SF900":{ # Sure
        "screen_size": (960, 853),
        "bootscreen_size": (853, 392),
        "image_format": QImage.Format_RGB16
    },
    "Vilcorn":{ # == SF900 ?
        "screen_size": (960, 853),
        "bootscreen_size": (853, 392),
        "image_format": QImage.Format_RGB16
    },
    "SF901":{
        "screen_size": (960, 853),
        "bootscreen_size": (853, 392),
        "image_format": QImage.Format_RGB16
    },
    "SG800":{ #Y2 SG 2.0
        "screen_size": (960, 853),
        "bootscreen_size": (853, 392),
        "image_format": QImage.Format_RGB16
    },
}
# fmt: on


class FrogConfig:
    frog_root_path: Path = None
    frog_system = None
    font_color = None
    default_system = None
    systems = []
    image_format = QImage.Format_RGB16
    screen_size = ((640, 480),)
    bootscreen_size = (512, 200)
    thumb_size = (144, 208)

    def __init__(self):
        super().__init__()

    def read_frog_config(self, frog_root_path: Path):
        """
        Read config from Foldername.ini
        """

        foldername_ini = frog_root_path / "Resources" / "Foldername.ini"

        with foldername_ini.open("r") as fh:
            foldername_lines = fh.read().splitlines()

        if 16 < len(foldername_lines) < 17:
            raise Exception("Unsupported Foldername.ini")

        self.frog_root_path = frog_root_path

        self.frog_system = foldername_lines[0]
        # Combine with static systems info
        config = frog_systems[self.frog_system]
        self.image_format = config.get("image_format")
        self.screen_size = config.get("screen_size")
        self.bootscreen_size = config.get("bootscreen_size")
        menu_ressources = config.get("menu_ressources")
        self.supported_rom_formats = config.get("supported_rom_formats")

        self.font_color = foldername_lines[2]

        # Get number of active systems and load menu configuration
        m_id = config.get("max_menu_items") + 3
        nb_systems, self.default_system, _ = foldername_lines[m_id].split(" ")
        for i in range(0, int(nb_systems) - 1):  # Do not take into account ROM entry
            color, folder = foldername_lines[4 + i].split(" ")
            self.systems.append([folder, menu_ressources[i], color])

        _, _, width, height = foldername_lines[14].split(" ")
        self.thumb_size = (int(width), int(height))

    def get_bios_path(self) -> Path:
        return self.frog_root_path / "bios" / "bisrv.asd"

    def resource_path(self, system, resource_id) -> Path:
        file_name = system[1][resource_id]
        return self.frog_root_path / "Resources" / file_name

    def system_path(self, system) -> Path:
        return self.frog_root_path / system[0]

    def favorite_path(self) -> Path:
        return self.frog_root_path / "Resources" / "Favorites.bin"

    def history_path(self) -> Path:
        return self.frog_root_path / "Resources" / "History.bin"

    def zxx_exts(self):
        return zxx_exts.keys()

    def __zxx_ext_for(self, rom_ext):
        for zxx_ext, roms_ext in zxx_exts.items():
            if rom_ext in roms_ext:
                return zxx_ext
        return list(zxx_exts.keys())[0]

    def load_thumbnail(self, rom_path: Path):
        if rom_path.suffix in zxx_exts.keys():
            return get_qimage_from_zxx(rom_path, self.thumb_size, self.image_format)

    def change_thumbnail(self, rom_path: Path, thumbnail: QImage, overwrite: bool):
        thumbnail = resize_qimage(thumbnail, self.thumb_size, crop=True)

        if rom_path.suffix in zxx_exts.keys() and overwrite:
            # We replace the old thumbnail with the new one
            replace_thumb_in_zxx(
                rom_path, thumbnail, self.thumb_size, self.image_format
            )
        else:
            self.__create_zxx(rom_path, rom_path.parent, thumbnail)

    def is_arcade_zip(self, rom_path: Path):
        """Open zip file and check if it is an "ARCADE" rom.
        For that, we check if it contains non Mame "console" related extension (i.e.
        SNES, MD, GB, etc.).
        If they are no "console" related extension, or too much one (i.e. `.bin`),
        we assume it is a "ARCADE" rom.
        """

        with zipfile.ZipFile(rom_path, "r") as zf:
            namelist = zf.namelist()

        matching_files = 0
        if len(namelist) < 4:
            for item in namelist:
                _, item_ext = splitext(item)
                if item_ext in self.supported_rom_formats:
                    matching_files += 1

        return matching_files != 1

    def add_rom(self, rom_path: Path, system, thumbnail: QImage = None):
        return self.__create_zxx(rom_path, self.system_path(system), thumbnail)

    def __create_zxx(self, rom_path: Path, system_path=None, thumbnail: QImage = None):

        if rom_path.suffix == ".zip" and self.is_arcade_zip(rom_path):
            ## Process as linked roms (Arcade ROMS are linked, not included in the zxx)
            (system_path / "bin").mkdir(parents=True, exist_ok=True)
            shutil.copy(rom_path, system_path / "bin" / rom_path.name)
            zfb_path = (system_path / rom_path.name).with_suffix(".zfb")
            create_zfb_file(
                zfb_path,
                rom_path.name,
                thumbnail,
                self.thumb_size,
                self.image_format,
            )
        else:
            ## Process as other console roms (include rom in the zxx file)
            # TODO : Multicore support
            zxx_ext = self.__zxx_ext_for(rom_path.suffix)
            zxx_path = (system_path / rom_path.name).with_suffix(zxx_ext)
            create_zxx_file(
                zxx_path,
                rom_path,
                thumbnail,
                self.thumb_size,
                self.image_format,
            )

        # Check if the rom is in the system folder
        if system_path == rom_path.parent:
            # delete the file
            rom_path.unlink()

    def delete_rom(self, rom_path: Path):
        if rom_path.suffix == ".zfb":
            # ROM is linked by a zfb file, need to also delete the linked file
            logger.debug(f"Delete linked rom from '{rom_path}'")

            arcadezip = get_rompath_from_zfb(
                rom_path,
                self.thumb_size,
                self.image_format,
            )

            # TODO : Multicore support
            arcade_rom = rom_path.parent / "bin" / arcadezip
            arcade_rom.unlink()

        rom_path.unlink()

    def write_system_indexes(self, system, roms_path: list[Path], test_mode: bool):
        nb_files = len(roms_path)
        if nb_files == 0:
            logger.debug("No ROMs found! Going to save an empty file list")
        else:
            roms_path = sorted(roms_path)

        index_path_files = self.resource_path(system, ENGLISH_ROMLIST)
        index_path_cn = self.resource_path(system, CHINESE_ROMLIST)
        index_path_pinyin = self.resource_path(system, PINYIN_ROMLIST)

        if test_mode:
            index_path_files = index_path_files.with_suffix(".test")
            index_path_cn = index_path_cn.with_suffix(".test")
            index_path_pinyin = index_path_pinyin.with_suffix(".test")

        # prepare maps of filenames to index name for the 3 index files
        # for English we just want the actual filenames, the menu will strip the extensions
        # for the Chinese names and pinyin initials, we use the English titles,
        # but use the stripped versions because the menu will not strip them here.
        stripped_names = [path.with_suffix("") for path in roms_path]

        write_index_file(index_path_files, roms_path)
        write_index_file(index_path_cn, stripped_names)
        write_index_file(index_path_pinyin, stripped_names)


frog_config = FrogConfig()
