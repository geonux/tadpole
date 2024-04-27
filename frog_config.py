import os

from PyQt5.QtGui import QImage

from utils.image_utils import (
    create_zxx_file,
    get_bytes_from_qimage,
    load_as_qimage,
    replace_thumb_in_zxx,
)

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
    "zfc": ["nes", "fds", "unf", "nfc"],
    "zgb": [
        "gba",
        "agb",
        "gbz",
        "gbc",
        "gb",
        "sgb",
    ],
    "zmd": ["md", "smd", "gen", "sms"],
    "zsf": ["sfc", "smc", "fig", "swc", "gd3", "gd7", "dx2", "bsx", "bin"],
    "zpc": ["pce"],
}


# fmt: off
frog_systems = {
    "SF2000": {
        "screen_size": (640, 480),
        "bootscreen_size": (512, 200),
        "image_format": QImage.Format_RGB16,
        "max_menu_items": 10,
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
    frog_root_path = None
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

    def read_frog_config(self, frog_root_path):
        """
        Read config from Foldername.ini
        """

        foldername_ini = os.path.join(frog_root_path, "Resources", "Foldername.ini")

        with open(foldername_ini, "r") as fh:
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

        self.font_color = foldername_lines[2]

        # Get number of active systems and load menu configuration
        m_id = config.get("max_menu_items") + 3
        nb_systems, self.default_system, _ = foldername_lines[m_id].split(" ")
        for i in range(0, int(nb_systems) - 1):  # Do not take into account ROM entry
            color, folder = foldername_lines[4 + i].split(" ")
            self.systems.append([folder, menu_ressources[i], color])

        _, _, width, height = foldername_lines[14].split(" ")
        self.thumb_size = (int(width), int(height))

    def get_bios_file(self):
        return os.path.join(self.frog_root_path, "bios", "bisrv.asd")

    def resource_path(self, system, resource_id):
        file_name = system[1][resource_id]
        return os.path.join(self.frog_root_path, "Resources", file_name)

    def system_path(self, system):
        return os.path.join(self.frog_root_path, system[0])

    def _zxx_ext_for(self, rom_ext):
        for zxx_ext, roms_ext in zxx_exts:
            if rom_ext in roms_ext:
                return zxx_ext

    def create_or_edit_zxx_file(self, system, rom_path, qimage, ovewrite):
        rom_fullname = os.path.basename(rom_path)
        rom_name, rom_ext = os.path.splitext(rom_fullname)

        if rom_ext[1:] in zxx_exts.keys() and ovewrite:
            # We replace the old thumbnail with the new one
            replace_thumb_in_zxx(rom_path, qimage, self.thumb_size, self.image_format)
        else:
            zxx_ext = self._zxx_ext_for(rom_ext[1:])
            zxx_path = os.path.join(self.system_path(system), f"{rom_name}.{zxx_ext}")
            create_zxx_file(
                zxx_path,
                rom_path,
                qimage,
                self.thumb_size,
                self.image_format,
            )


frog_config = FrogConfig()
