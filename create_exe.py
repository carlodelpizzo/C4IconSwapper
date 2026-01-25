import PyInstaller.__main__
import shutil
import os
from C4IconSwapper import version

cur_dir = os.getcwd()
pathjoin = os.path.join
isfile = os.path.isfile
isdir = os.path.isdir

main_file = 'C4IconSwapper.py'
exe_file_name = 'C4IconSwapper'


def make_exe():
    def clean_up():
        if isfile(pathjoin(cur_dir, f'{exe_file_name}.spec')):
            os.remove(pathjoin(cur_dir, f'{exe_file_name}.spec'))
        if isdir(pathjoin(cur_dir, 'dist')):
            shutil.rmtree(pathjoin(cur_dir, 'dist'))
        if isdir(pathjoin(cur_dir, 'build')):
            shutil.rmtree(pathjoin(cur_dir, 'build'))
        if isdir(pathjoin(cur_dir, '__pycache__')):
            shutil.rmtree(pathjoin(cur_dir, '__pycache__'))

    # Remove old builds if any
    clean_up()

    # Include Assets
    assets = ['--add-data', 'assets/generic.c4z;assets',
              '--add-data', 'assets/multi_generic.c4z;assets',
              '--add-data', 'assets/icon.ico;assets',
              '--add-data', 'assets/blank_img.png;assets',
              '--add-data', 'assets/loading_img.png;assets']

    # Build Exe
    PyInstaller.__main__.run([main_file, '--onefile', '-w', '--icon=assets/icon.ico', *assets])

    # Move and Rename
    if isfile(pathjoin(cur_dir, 'dist', f'{exe_file_name}.exe')):
        if isfile(pathjoin(cur_dir, f'{exe_file_name}.{version}.exe')):
            os.remove(pathjoin(cur_dir, f'{exe_file_name}.{version}.exe'))
        shutil.move(pathjoin(cur_dir, 'dist', f'{exe_file_name}.exe'),
                    pathjoin(cur_dir, f'{exe_file_name}.{version}.exe'))

    # Remove build files
    clean_up()


# Change to True before running; this is to prevent accidental run; add tkdnd2.8\ to Python\Python38\tcl\tcl8.6\
execute = False

if execute:
    overwrite_file = '_'
    if isfile(pathjoin(cur_dir, f'{exe_file_name}.{version}.exe')):
        overwrite_file = input('Overwrite file? (y/n)... ')
    else:
        make_exe()
    if overwrite_file[0] in ('y', 'Y'):
        make_exe()
else:
    print(f'{os.path.basename(__file__)} execution set to False')
