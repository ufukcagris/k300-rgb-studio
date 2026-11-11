# -*- mode: python ; coding: utf-8 -*-
# PyInstaller tarifi.  Derleme:  pyinstaller --noconfirm --clean K300RGBStudio.spec
# Cikti: dist/K300RGBStudio/K300RGBStudio.exe  (onedir: tek dosyadan hizli acilir, antivirus
# yanlis alarmlari onefile'a gore daha az).
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("soundcard")      # soundcard, cffi baslik dosyalarini calisma aninda okur

excludes = [
    "tkinter", "matplotlib", "scipy", "pandas", "IPython", "pytest", "PIL",
    # Kullanilmayan Qt modulleri (paketi kucultur)
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtMultimedia",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp",
]

a = Analysis(
    ["run.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=["_cffi_backend"],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="K300RGBStudio",
    icon="assets/icon.ico",
    version="packaging/version_info.txt",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="K300RGBStudio")
