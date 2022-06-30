from setuptools import setup
# In terminal, run "python setup.py py2app"

APP = ['main.py']
DATA_FILES = []
OPTIONS = {'argv_emulation': True, 'iconfile': 'icon.icns'}

setup(app=APP, data_files=DATA_FILES, options={'py2app': OPTIONS}, setup_requires=['py2app'],)
