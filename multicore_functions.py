import logging
import os
from utils.image_utils import create_zfb_file

multicore_exclusionList = [
    "data",
    "DoConfig.exe",
    "Manual",
    "Manual.html",
    "OrgView.exe",
    "Readme.txt",
    "SETTINGS.DAT",
    ""
]


def makeMulticoreROMList(drive):
    logging.info("tadpole_functions~makeMulticoreROMList")
    romcount = 0
    for d in os.listdir(os.path.join(drive,"cores")):
        if os.path.isdir(os.path.join(drive,"cores",d)):
            logging.info(f"Build Multicore ROMs for {d}")
            romfolder = os.path.join(drive,"ROMS",d)
            if os.path.exists(romfolder):
                for rom in os.listdir(romfolder):
                    romcount += 1
                    # Creates a new file 
                    with open(os.path.join(drive,"ROMS",f"{d};{rom}.gba"), 'w'): 
                        pass
    return romcount

def makeMulticoreROMList_ARCADEMode(drive):
    logging.info("tadpole_functions~makeMulticoreROMList_ARCADEMode")
    romcount = 0
    for d in os.listdir(os.path.join(drive,"cores")):
        # Handle some special cases first
        if(d == "2048"):
            create_zfb_file(os.path.join(drive, "ARCADE", "2048.zfb"), "2048;game.gba")
        elif(d == "cavestory"):
            create_zfb_file(os.path.join(drive, "ARCADE", "Cave Story.zfb"), "cavestory;Config.dat.gba")
        elif(d =="gong"):
            create_zfb_file(os.path.join(drive, "ARCADE", "Gong.zfb"), "gong;game.gba")
        elif(d == "mrboom"):
            create_zfb_file(os.path.join(drive, "ARCADE", "Mrboom.zfb"), "mrboom;dummy.gba")
        elif(d == "wolf3d"):
            create_zfb_file(os.path.join(drive, "ARCADE", "Wolfenstein 3D.zfb"), "wolf3d;WOLF3D.EXE.gba")     
        elif os.path.isdir(os.path.join(drive,"cores",d)):
            logging.info(f"Build Multicore ROMs for {d}")
            print(f"Got to {d}")
            romfolder = os.path.join(drive,"ROMS",d)
            if os.path.exists(romfolder):
                destination_zfb = "ARCADE"
                if "snes" in d:
                    destination_zfb = "SFC"
                elif "nes" in d:
                    destination_zfb = "FC"
                elif "gba" in d:
                    destination_zfb = "GBA"
                elif "gbc" in d:
                    destination_zfb = "GBC"
                elif "gb" in d:
                    destination_zfb = "GB"
                elif "sega" in d:
                    destination_zfb = "MD"

                for rom in os.listdir(romfolder):
                    dest_filename = os.path.join(drive, destination_zfb, f"{os.path.splitext(rom)[0]}.zfb")
                    if(not os.path.exists(dest_filename) and rom not in multicore_exclusionList):
                        romcount += 1
                        # Creates a new file 
                        create_zfb_file(dest_filename, f"{d};{rom}.gba")  

    return romcount