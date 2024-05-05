import configparser
import logging
from os import mkdir
from os.path import exists
from pathlib import Path


class TadpoleConfig:
    _tadpole_folder = Path.home() / ".tadpole"
    _tadpole_config_file = _tadpole_folder / "tadpole.ini"

    _DEFAULT_CONFIG = """
        [tadpole]
        user_directory = 

        [Thumbnails]
        viewintable = False
        overwrite = False
        download = 0
    """
    _MAIN_SECTION = "tadpole"
    _THUMB_SECTION = "Thumbnails"

    def __init__(self):
        super().__init__()
        logging.info(f"establishing tadpole config")
        self.config = configparser.ConfigParser()

        # Load default value
        self.config.read_string(self._DEFAULT_CONFIG)

        # Overwrite default value with user's values
        try:
            self.config.read(self._tadpole_config_file)
        except:
            # Problem reading file so creating a new one
            if not exists(self._tadpole_folder):
                mkdir(self._tadpole_folder)

        # Wrtite config file with merged default values
        with open(self._tadpole_config_file, "w") as fp:
            self.config.write(fp)

    def setVariable(self, section, option, value):
        self.config[section][option] = str(value)
        with open(self._tadpole_config_file, "w") as fp:
            self.config.write(fp)

    def setLocalUserDirectory(self, location):
        self.setVariable(self._MAIN_SECTION, "user_directory", location)

    def getLocalUserDirectory(self):
        return self.config[self._MAIN_SECTION].get("user_directory")

    def setViewThumbnailsInTable(self, enabled: bool):
        self.setVariable(self._THUMB_SECTION, "viewintable", enabled)

    def getViewThumbnailsInTable(self):
        return self.config[self._THUMB_SECTION].getboolean("viewintable")

    def setThumbnailDownload(self, enabled: bool):
        self.setVariable(self._THUMB_SECTION, "download", enabled)

    def getThumbnailDownload(self):
        return self.config[self._THUMB_SECTION].getboolean("download")

    def setThumbnailOverwrite(self, enabled: bool):
        self.setVariable(self._THUMB_SECTION, "overwrite", enabled)

    def getThumbnailOverwrite(self):
        return self.config[self._THUMB_SECTION].getboolean("overwrite")
