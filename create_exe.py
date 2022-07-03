import PyInstaller.__main__
import shutil
import os
import platform
if platform.system() == 'Darwin':
    from C4IconSwapperMac import version
    on_mac = True
else:
    from C4IconSwapper import version
    on_mac = False

cur_dir = os.getcwd() + '/'


def make_exe(python_file: str):
    if not python_file.endswith('.py'):
        print('Not a python file...')
        return
    else:
        python_file_name = python_file[0:len(python_file) - 3]

    def clean_up():
        if os.path.isfile(cur_dir + python_file_name + '.spec'):
            os.remove(cur_dir + python_file_name + '.spec')
        if os.path.isdir(cur_dir + 'dist/'):
            shutil.rmtree(cur_dir + 'dist/')
        if os.path.isdir(cur_dir + 'build/'):
            shutil.rmtree(cur_dir + 'build/')
        if os.path.isdir(cur_dir + '__pycache__/'):
            shutil.rmtree(cur_dir + '__pycache__/')

    # Remove old builds if any
    clean_up()
    # Build Exe
    PyInstaller.__main__.run([python_file, '--onefile', '-w'])
    # Move and Rename
    if os.path.isfile(cur_dir + 'dist/' + python_file_name + '.exe'):
        if not os.path.isfile(cur_dir + 'C4IconSwapper.' + version + '.exe'):
            shutil.copy(cur_dir + 'dist/' + python_file_name + '.exe', cur_dir + 'C4IconSwapper.' + version + '.exe')
        else:
            os.remove(cur_dir + 'C4IconSwapper.' + version + '.exe')
            shutil.copy(cur_dir + 'dist/' + python_file_name + '.exe', cur_dir + 'C4IconSwapper.' + version + '.exe')
    # Remove build files
    clean_up()


# Change to True before running; this is to prevent accidental run; add tkdnd2.8\ to Python\Python38\tcl\tcl8.6\
execute = False

if execute:
    overwrite_file = '_'
    if os.path.isfile(cur_dir + 'C4IconSwapper.' + version + '.exe'):
        overwrite_file = input('Overwrite file? (y/n)... ')
        if overwrite_file[0] == 'y' or overwrite_file[0] == 'Y':
            make_exe('main.py')
    else:
        make_exe('main.py')
