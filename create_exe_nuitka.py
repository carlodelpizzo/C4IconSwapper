import os
import subprocess
import sys
import tkinterdnd2
from C4IconSwapper import version

main_file = 'C4IconSwapper.py'
exe_file_name = 'C4IconSwapper'
tkdnd_path = os.path.join(os.path.dirname(tkinterdnd2.__file__), 'tkdnd')

command = [
    sys.executable, '-m', 'nuitka',
    '--standalone',
    '--onefile',
    # '--mingw64',
    '--msvc=latest',
    '--assume-yes-for-downloads',
    '--enable-plugin=tk-inter',
    '--windows-console-mode=disable',
    '--windows-icon-from-ico=assets/icon.ico',
    f'--output-filename={exe_file_name}.{version}.exe',
    '--include-data-dir=assets=assets',
    # '--include-package=tkinterdnd2',
    # '--collect-all=tkinterdnd2',
    f'--include-data-dir={tkdnd_path}=tkinterdnd2/tkdnd',
    main_file
]

# Change to True before running; this is to prevent accidental run
execute = True

if __name__ == '__main__':
    if execute:
        result = subprocess.run(command)

        if result.returncode == 0:
            print('--- Build Completed ---')
        else:
            print('--- Build Failed or Interrupted ---')
    else:
        print(f'{os.path.basename(__file__)} execution set to False')
