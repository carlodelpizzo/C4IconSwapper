import platform
from C4IconSwapper import C4IconSwapper
from C4IconSwapperMac import C4IconSwapperMac

if platform.system() == 'Darwin':
    C4IconSwapperMac()
else:
    C4IconSwapper()
