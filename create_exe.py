import PyInstaller.__main__
import shutil
import os
from C4IconSwapper import version

cur_dir = os.getcwd() + '/'


def clean_up():
    if os.path.isfile(cur_dir + 'main.spec'):
        os.remove(cur_dir + 'main.spec')
    if os.path.isdir(cur_dir + 'dist/'):
        shutil.rmtree(cur_dir + 'dist/')
    if os.path.isdir(cur_dir + 'build/'):
        shutil.rmtree(cur_dir + 'build/')
    if os.path.isdir(cur_dir + '__pycache__/'):
        shutil.rmtree(cur_dir + '__pycache__/')


def move_rename():
    if os.path.isfile(cur_dir + 'dist/main.exe'):
        if not os.path.isfile(cur_dir + 'C4IconSwapper.' + str(version) + '.exe'):
            shutil.copy(cur_dir + 'dist/main.exe', cur_dir + 'C4IconSwapper.' + str(version) + '.exe')
        else:
            os.remove(cur_dir + 'C4IconSwapper.' + str(version) + '.exe')
            shutil.copy(cur_dir + 'dist/main.exe', cur_dir + 'C4IconSwapper.' + str(version) + '.exe')


clean_up()
PyInstaller.__main__.run(['main.py', '--onefile', '-w'])
move_rename()
clean_up()
