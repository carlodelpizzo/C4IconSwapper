# C4IconSwapper
This program can be used to replace icons for Control 4 drivers.

In addition to swapping icons, the program modifies the diver xml file,
there is no option prevent xml modification,
but the outputted .c4z file will have a .bak file of the old driver.xml if you want to restore it manually.

It can add connections such as HDMI IN/OUT,
has drag and drop support for .c4z files and image files,
and currently has limited support for modifying multi-state experience drivers.

It has two built in generic drivers:
1) a two-state experience driver ("Load Generic Driver")
2) a multi-state "key-status" experience driver ("Load Multi Driver")

The built-in multi-state driver has support for re-naming the 13 driver states.
It has not been thoroughly tested, but seems to work from what little testing has been done.

Since drag and drop support was added with tkinterdnd2,
there have been issues with getting the program to run due to missing tkinter dependency.
I have had some luck with manually copying tkdnd2.8 folder to \tcl\tcl8.6\ sub-folder of the python interpreter.
The exe file should work either way, but antivirus doesn't like the exe file :(
