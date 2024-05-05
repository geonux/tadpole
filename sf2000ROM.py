from pathlib import Path


class sf2000ROM:
    rom_path: Path
    title: str
    thumbnail = None
    console = None

    def __init__(self, path: Path):
        super().__init__()
        self.rom_path = path
        self.title = path.stem

    def setTitle(self, newTitle):
        """
        Change the title of the ROM and rename the file accordingly
        """

        new_path = self.rom_path.with_stem(newTitle)
        self.rom_path.rename(new_path)
        self.rom_path = new_path
        self.title = new_path.stem
#
    def getFileSize(self):
        return self.rom_path.stat().st_size
        # TODO Add counting multiple files for ARCADE zips

    def getHumanFileSize(self):
        filesize = self.getFileSize()
        for unit in ("", "K", "M"):
            if filesize < 1024.0:
                return f"{filesize:3.2f} {unit}B"
            filesize /= 1024.0
        return f"{filesize:.2f} GB"
