# C4IconSwapper
This program can be used to replace icons of (most) Control4 drivers with custom images.

In addition to swapping icons, the program modifies the driver xml (driver manufacturer, creator, and version are customizable).
There is no option to prevent xml modification,
but the exported driver will have a .bak file of the original driver.xml if you want to restore it manually (must have 'include backup files' selected).

It can add/remove driver connections (e.g. HDMI IN/OUT),
and [Windows version] has drag-and-drop support for .c4z files and image files/folders.

It has two built-in generic drivers for quick driver creation:
1) a two-state experience driver (Accessible by selecting "Load Generic Driver" in File menu)
2) a multi-state "key-status" experience driver (Accessible by selecting "Load Multi Driver" in File menu)

The program has (experimental) support for re-naming the 13 states of the multi-state driver by modifying the lua file (in addition to the xml file).
Multi-state related uses have not been well tested but seem to work from what little testing has been done.
