# C4IconSwapper
This program can be used to replace icons for Control4 drivers.

In addition to swapping icons, the program modifies the driver xml file,
there is no option to prevent xml modification,
but the exported driver will have a .bak file of the old driver.xml if you want to restore it manually
(must have 'include backup files' selected).

It can add connections such as HDMI IN/OUT,
has drag and drop support for .c4z files and image files (Windows version only),
and currently has limited support for modifying multi-state experience drivers.

It has two built in generic drivers:
1) a two-state experience driver ("Load Generic Driver")
2) a multi-state "key-status" experience driver ("Load Multi Driver")

The built-in multi-state driver has support for re-naming the 13 driver states.
It has not been thoroughly tested, but seems to work from what little testing has been done.
