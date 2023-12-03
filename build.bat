@echo off
set ver=1.2.1
rem build script for the distributable versions of tadpole
if not exist "venv\" (
    python -m venv venv
)
if not exist "venv\Lib\site-packages\PyInstaller" (
    venv\Scripts\python -m pip install pyinstaller
)
if not exist "venv\Lib\site-packages\PIL" (
    venv\Scripts\python -m pip install Pillow
)
if not exist "venv\Lib\site-packages\PyQt5" (
    venv\Scripts\python -m pip install PyQt5
)
python -m PyInstaller tadpole.py -n tadpole-%ver%.exe --onefile -F --icon frog.ico --clean --noconsole --version-file versioninfo --add-data="frog.ico;." --add-data="README.md;."
