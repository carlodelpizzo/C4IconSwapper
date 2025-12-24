import PyInstaller.__main__
import shutil
import os
from C4IconSwapper import version

cur_dir = f'{os.getcwd()}/'


def make_exe(python_file: str):
    def clean_up():
        if os.path.isfile(cur_dir + python_file_name + '.spec'):
            os.remove(cur_dir + python_file_name + '.spec')
        if os.path.isdir(f'{cur_dir}dist/'):
            shutil.rmtree(f'{cur_dir}dist/')
        if os.path.isdir(f'{cur_dir}build/'):
            shutil.rmtree(f'{cur_dir}build/')
        if os.path.isdir(f'{cur_dir}__pycache__/'):
            shutil.rmtree(f'{cur_dir}__pycache__/')

    python_file_name = python_file.replace('.py', '')
    # Remove old builds if any
    clean_up()
    # Build Exe
    PyInstaller.__main__.run([python_file, '--onefile', '-w', '--icon=icon.ico'])
    # Move and Rename
    if os.path.isfile(f'{cur_dir}dist/{python_file_name}.exe'):
        if os.path.isfile(f'{cur_dir}C4IconSwapper.{version}.exe'):
            os.remove(f'{cur_dir}C4IconSwapper.{version}.exe')
        shutil.copy(f'{cur_dir}dist/{python_file_name}.exe', f'{cur_dir}C4IconSwapper.{version}.exe')

    # Remove build files
    clean_up()


# Change to True before running; this is to prevent accidental run; add tkdnd2.8\ to Python\Python38\tcl\tcl8.6\
execute = False

if execute:
    overwrite_file = '_'
    if os.path.isfile(f'{cur_dir}C4IconSwapper.{version}.exe'):
        overwrite_file = input('Overwrite file? (y/n)... ')
    else:
        make_exe('C4IconSwapper.py')
    if overwrite_file[0] in ['y', 'Y']:
        make_exe('C4IconSwapper.py')
else:
    print('create_exe execution set to False')
