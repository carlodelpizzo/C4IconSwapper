import os
import subprocess
import sys
import tkinterdnd2
from C4IconSwapper import version

main_file = 'C4IconSwapper.py'
exe_file_name = f'C4IconSwapper.{version}'
tkdnd_path = os.path.join(os.path.dirname(tkinterdnd2.__file__), 'tkdnd')


def make_exe():
    nuitka_command = [
        sys.executable, '-m', 'nuitka',
        '--standalone',
        '--onefile',
        '--msvc=latest',
        '--assume-yes-for-downloads',
        '--enable-plugin=tk-inter',
        '--windows-console-mode=disable',
        '--windows-icon-from-ico=assets/icon.ico',
        f'--output-filename={exe_file_name}.exe',
        '--include-data-dir=assets=assets',
        f'--include-data-dir={tkdnd_path}=tkinterdnd2/tkdnd',
        main_file
    ]

    result = subprocess.run(nuitka_command)

    if result.returncode == 0:
        print('--- Build Completed ---')
    else:
        print('--- Build Failed or Interrupted ---')


# pip install nuitka zstandard ordered-set
# App made using Python 3.11, not sure if other versions will work
# Change to True before running; this is to prevent accidental run
execute = False

if __name__ == '__main__':
    if execute:
        make_exe()
    else:
        print(f'{os.path.basename(__file__)} execution set to False')
