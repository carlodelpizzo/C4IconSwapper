from setuptools import setup
# In terminal, run "python setup.py py2app"

APP = ['C4IconSwapperMac.py']
DATA_FILES = []
OPTIONS = {'argv_emulation': True, 'iconfile': 'icon.icns', 'includes': ['tkinter', 'tkinterdnd2', 'PIL', 'filecmp',
                                                                         'subprocess', 'os', 'shutil', 'base64',
                                                                         'time', 'random', 're', 'datetime', 'AppKit',
                                                                         'Base64Assets', 'XMLObject', 'platform',
                                                                         'Pillow', 'PyObjC', 'NSBundle', 'macholib',
                                                                         'altgraph', 'modulegraph', 'future']}

setup(app=APP, data_files=DATA_FILES, options={'py2app': OPTIONS}, setup_requires=['py2app'],)
