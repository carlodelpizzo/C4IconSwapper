import PyInstaller.__main__
import shutil
import os
import platform
if platform.system() == 'Darwin':
    from UnifiedVersion import get_path
    on_mac = True
else:
    on_mac = False
from UnifiedVersion import version

cur_dir = os.getcwd() + '/'
if on_mac:
    cur_dir = get_path(cur_dir) + '/'


def make_exe(python_file: str):
    def clean_up():
        if os.path.isfile(cur_dir + python_file_name + '.spec'):
            os.remove(cur_dir + python_file_name + '.spec')
        if os.path.isdir(cur_dir + 'dist/'):
            shutil.rmtree(cur_dir + 'dist/')
        if os.path.isdir(cur_dir + 'build/'):
            shutil.rmtree(cur_dir + 'build/')
        if os.path.isdir(cur_dir + '__pycache__/'):
            shutil.rmtree(cur_dir + '__pycache__/')

    python_file_name = python_file.replace('.py', '')
    # Remove old builds if any
    clean_up()
    if not on_mac:
        # Build Exe
        PyInstaller.__main__.run([python_file, '--onefile', '-w', '--icon=icon.ico'])
        # Move and Rename
        if os.path.isfile(cur_dir + 'dist/' + python_file_name + '.exe'):
            if os.path.isfile(cur_dir + 'C4IconSwapper.' + version + '.exe'):
                os.remove(cur_dir + 'C4IconSwapper.' + version + '.exe')
            shutil.copy(cur_dir + 'dist/' + python_file_name + '.exe',
                        cur_dir + 'C4IconSwapper.' + version + '.exe')
    else:
        # Build Exe
        PyInstaller.__main__.run([python_file, '--onefile', '-w', '--icon=icon.icns'])
        # Move and Rename
        if os.path.isdir(cur_dir + '/C4IconSwapper.' + version + '.app'):
            shutil.rmtree(cur_dir + '/C4IconSwapper.' + version + '.app')
        shutil.copytree(cur_dir + '/dist/' + python_file_name + '.app',
                        cur_dir + '/C4IconSwapper.' + version + '.app')
    # Remove build files
    clean_up()


# Change to True before running; this is to prevent accidental run; add tkdnd2.8\ to Python\Python38\tcl\tcl8.6\
execute = False

if execute:
    overwrite_file = '_'
    if not on_mac:
        if os.path.isfile(cur_dir + 'C4IconSwapper.' + version + '.exe'):
            overwrite_file = input('Overwrite file? (y/n)... ')
        else:
            make_exe('Control4 Icon Swapper.py')
    else:
        if os.path.isdir(cur_dir + 'C4IconSwapper.' + version + '.app'):
            overwrite_file = input('Overwrite file? (y/n)... ')
        else:
            make_exe('C4 Icon Swapper for Mac.py')
    if overwrite_file[0] == 'y' or overwrite_file[0] == 'Y':
        make_exe('Control4 Icon Swapper.py')
