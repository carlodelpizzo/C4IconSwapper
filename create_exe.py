import PyInstaller.__main__
import shutil
import os
from C4IconSwapper import version

cur_dir = os.getcwd()
pathjoin = os.path.join


def make_exe(python_file: str):
    def clean_up():
        if os.path.isfile(pathjoin(cur_dir + python_file_name + '.spec')):
            os.remove(pathjoin(cur_dir + python_file_name + '.spec'))
        if os.path.isdir(pathjoin(cur_dir, 'dist')):
            shutil.rmtree(pathjoin(cur_dir, 'dist'))
        if os.path.isdir(pathjoin(cur_dir, 'build')):
            shutil.rmtree(pathjoin(cur_dir, 'build'))
        if os.path.isdir(pathjoin(cur_dir, '__pycache__')):
            shutil.rmtree(pathjoin(cur_dir, '__pycache__'))

    if not python_file.endswith('.py'):
        print('Invalid File')
        return
    python_file_name = python_file[:-3]
    # Remove old builds if any
    clean_up()
    # Include Assets
    assets = ['--add-data', 'assets/generic.c4z;assets',
              '--add-data', 'assets/icon.ico;assets',
              '--add-data', 'assets/blank_img.png;assets',
              '--add-data', 'assets/loading_img.png;assets']
    # Build Exe
    PyInstaller.__main__.run([python_file, '--onefile', '-w', '--icon=assets/icon.ico', *assets])
    # Move and Rename
    if os.path.isfile(pathjoin(cur_dir, 'dist', f'{python_file_name}.exe')):
        if os.path.isfile(f'{cur_dir}C4IconSwapper.{version}.exe'):
            os.remove(f'{cur_dir}C4IconSwapper.{version}.exe')
        shutil.move(pathjoin(cur_dir, 'dist', f'{python_file_name}.exe'),
                    pathjoin(cur_dir, f'C4IconSwapper.{version}.exe'))

    # Remove build files
    clean_up()


# Change to True before running; this is to prevent accidental run; add tkdnd2.8\ to Python\Python38\tcl\tcl8.6\
execute = False

if execute:
    overwrite_file = '_'
    if os.path.isfile(pathjoin(cur_dir, f'C4IconSwapper.{version}.exe')):
        overwrite_file = input('Overwrite file? (y/n)... ')
    else:
        make_exe('C4IconSwapper.py')
    if overwrite_file[0] in ['y', 'Y']:
        make_exe('C4IconSwapper.py')
else:
    print('create_exe execution set to False')
