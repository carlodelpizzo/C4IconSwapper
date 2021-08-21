import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import ImageTk, Image
from datetime import datetime
import os
import shutil
import base64
import time
import random

# exe made with pyinstaller --onefile -w
version = '3.1b'

# Root Window
root = tk.Tk()
root.geometry('915x250')
root.title('C4 Icon Swapper')
root.resizable(False, False)
entry_font = 'Helvetica'

# Creating temporary directory
cur_dir = os.getcwd()
temp_dir = os.getcwd() + '/temp/'
if not os.path.isdir(temp_dir):
    os.mkdir(temp_dir)

# Base64 encoded icon
# Decoding and creating a temporary image file
win_icon = \
    """
AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAABMLAAATCwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEAAQEBAIODg4RFRUVHBUVFRwVFRUcFRUVHBUVFRwVFRUcDg4OEQMDAwIEBAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEOAgICfQEBAcwBAQHcAQEB3AEBAdwBAQHcAQEB3AEBAdwBAQHMAgICfAEBAQ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVFRUA////AAEBAXsAAAD7EBAQ/yAgIP8gICD/ICAg/yAgIP8gICD/ICAg/xAQEP8AAAD7AgICe////wAWFhYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYGBgAGBgYPAAAAyQ8PD/+srKz/5OTk/+Pj4//j4+P/4+Pj/+Pj4//k5OT/rKys/w8PD/8AAADJBgYGDwYGBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8PDwATExMCCQkJDQcHB0QAAADoKioq/+np6f//////8PDw//b29v/29vb/8PDw///////o6Oj/Kioq/wAAAOgHBwdECQkJDgwMDAMPDw8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQEBDgMDA30BAQHKAAAA6QAAAP9tbW3//v7+/+/v7/9PT0//XV1d/11dXf9PT0//7+/v//7+/v9tbW3/AAAA/wAAAOkBAQHMAgICiAUFBRYDAwMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAgIAN/f3wACAgJ9AAAA/A8PD/8oKCj/bGxs/+Xl5f//////7u7u/zU1Nf8AAAD/AAAA/zc3N//v7+///////+Xl5f9sbGz/KCgo/xEREf8AAAD/AgIChzQ0NAENDQ0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEhIAEhISEQEBAcsQEBD/rKys/+vr6//8/Pz/////////////////jY2N/wICAv8CAgL/jY2N//////////////////v7+//r6+v/sbGx/xEREf8BAQHNExMTEhQUFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABUVFQAUFBQeAQEB3iEhIf/i4uL//v7+/+rq6v/p6en//Pz8///////u7u7/ZGRk/2VlZf/u7u7///////z8/P/p6en/6urq//7+/v/i4uL/ISEh/wEBAd4UFBQeFRUVAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWFhYAAAAAAAEBAVIAAAD2PT09/9zc3P92dnb/Kioq/yoqKv91dXX/6+vr///////29vb/9vb2///////q6ur/dXV1/yoqKv8rKyv/d3d3/9zc3P88PDz/AAAA9gMDA08BAQEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQEBAAGBgYGAQEBqgEBAf+Pj4//eHh4/wAAAP8AAAD/AAAA/wAAAP91dXX//v7+/////////////v7+/3V1df8AAAD/AAAA/wAAAP8AAAD/eXl5/42Njf8AAAD/AQEBpAwMDAUJCQkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACsAAADmHx8f/8PDw/8uLi7/AAAA/wAAAP8AAAD/AAAA/ywsLP/p6en////////////p6en/Kysr/wAAAP8AAAD/AAAA/wAAAP8uLi7/wcHB/x0dHf8AAADkBgYGKgUFBQAAAAAAAAAAAAAAAAAAAAAAAAAAABkZGQAAAAAAAgICaAAAAP5ZWVn/5eXl/ywsLP8AAAD/AAAA/wAAAP8AAAD/LCws/+rq6v///////////+np6f8rKyv/AAAA/wAAAP8AAAD/AAAA/y0tLf/l5eX/VlZW/wAAAP4EBARkAAAAAB0dHQAAAAAAAAAAAAAAAAAAAAAADQ0NADAwMAEBAQGeAAAA/5iYmP//////dXV1/wAAAP8AAAD/AAAA/wAAAP93d3f//v7+/////////////f39/3V1df8AAAD/AAAA/wAAAP8AAAD/d3d3//////+Tk5P/AAAA/wICApr///8AFBQUAAAAAAAAAAAAAAAAAAAAAAAEBAQABAQECwAAAMINDQ3/xsbG///////r6+v/dXV1/yoqKv8qKir/dnZ2/+vr6///////////////////////6urq/3V1df8qKir/Kysr/3Z2dv/r6+v//////8LCwv8MDAz/AAAAvwYGBgoGBgYAAAAAAAAAAAAAAAAAAAAAABMTEwASEhIWAAAA1RwcHP/d3d3////////////8/Pz/6enp/+np6f/8/Pz//////////////////////////////////Pz8/+np6f/p6en//Pz8////////////29vb/xsbG/8AAADTERERFRISEgAAAAAAAAAAAAAAAAAAAAAAFRUVABQUFBkBAQHZHh4e/+Dg4P/////////////////////////////////////////////////////////////////////////////////////////////////g4OD/Hh4e/wEBAdYWFhYXFxcXAAAAAAAAAAAAAAAAAAAAAAAICAgABwcHDgAAAMgTExP/0NDQ/////////////////////////////////////////////////////////////////////////////////////////////////9LS0v8UFBT/AAAAxwQEBA0EBAQAAAAAAAAAAAAAAAAAAAAAAA8PDwAWFhYDAQEBpwQEBP+qqqr/////////////////////////////////////////////////////////////////////////////////////////////////ra2t/wUFBf8BAQGoFBQUAw0NDQAAAAAAAAAAAAAAAAAAAAAARkZGAAAAAAACAgJqAAAA/2FhYf/8/Pz///////////////////////////////////////////////////////////////////////////////////////39/f9lZWX/AAAA/wMDA20AAAAANzc3AAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEAAUFBScAAADfFhYW/8PDw///////////////////////////////////////////////////////////////////////////////////////xcXF/xcXF/8AAADfBAQEJwMDAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAICAgANjY2AQMDA4IAAAD+QkJC/+Li4v///////////////////////////////////////////////////////////////////////////+Li4v9CQkL/AAAA/gMDA4EzMzMBCAgIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBgYABwcHGAEBAbkAAAD/S0tL/9nZ2f/////////////////////////////////////////////////////////////////V1dX/SEhI/wAAAP8BAQG2BgYGFgQEBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMDAwACgoKKwMDA8YAAAD/LCws/56env/r6+v///////////////////////////////////////7+/v/o6Oj/lpaW/ycnJ/8AAAD/AAAAvAAAACQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFdXVwAAAAAABQUFIwEBAaQAAAD3BgYG/zMzM/96enr/srKy/9LS0v/f39//39/f/9HR0f+vr6//dXV1/y4uLv8EBAT/AAAA9QICAp4DAwMfBAQEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEACQkJCwICAlkBAQG+AAAA8wAAAP8GBgb/FBQU/x4eHv8eHh7/ExMT/wUFBf8AAAD/AAAA8AEBAbUCAgJQCwsLCQAAAACysrIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAgIAAQEBAAwMDA4DAwNAAgICfwEBAa0AAADIAQEB2QEBAdkBAQHHAgICrAICAnkDAwM6BAQECwUFBQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkJABDQ0MADg4OBQgICA0LCwsZCwsLGQoKCg0WFhYE////AFJSUgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////////////////+AH///AA///wAP//4AB//4AAH/8AAA//AAAH/gAAB/4AAAf+AAAH/AAAA/wAAAP8AAAD+AAAA/gAAAH4AAAB+AAAAfgAAAH4AAAB/AAAA/wAAAP8AAAD/gAAB/8AAA//gAAf/8AAP//wAP///gf//////8=
"""
icon_data = base64.b64decode(win_icon)
temp_icon_file = temp_dir + 'icon.ico'
icon_file = open(temp_icon_file, 'wb')
icon_file.write(icon_data)
icon_file.close()
# root.wm_iconbitmap(temp_icon_file)  # Windows defender flags pyinstaller exe if this is enabled

# Base64 encoded blank image
# Decoding and creating a temporary image file
blank_img_b64 = \
    """
R0lGODlhpAGkAYAAAAAAAP///ywAAAAApAGkAQAC/4yPqcvtD6OctNqLs968+w+G4kiW5omm6sq27gvH8kzX9o3n+s73/g8MCofEovGITCqXzKbzCY1Kp9Sq9YrNarfcrvcLDovH5LL5jE6r1+y2+w2Py+f0uv2Oz+v3/L7/DxgoOEhYaHiImKi4yNjo+AgZKTlJWWl5iZmpucnZ6fkJGio6SlpqeoqaqrrK2ur6ChsrO0tba3uLm6u7y9vr+wscLDxMXGx8jJysvMzc7PwMHS09TV1tfY2drb3N3e39DR4uPk5ebn6Onq6+zt7u/g4fLz9PX29/j5+vv8/f7/8PMKDAgQQLGjyIMKHChQwbOnwIMaLEiRQrWryIMaPGjf8cO3r8CDKkyJEkS5o8iTKlypUsW7p8CTOmzJk0a9q8iTOnzp08e/r8CTSo0KFEixo9ijSp0qVMmzp9CjWq1KlUq1q9ijWr1q1cu3r9Cjas2LFky5o9izat2rVs27p9Czeu3Ll069q9izev3r18+/r9Cziw4MGECxs+jDix4sWMGzt+DDmy5MmUK1u+jDmz5s2cO3v+DDq06NGkS5s+jTq16tWsW7t+DTu27Nm0a9u+jTu37t28e/v+DTy48OHEixs/jjy58uXMmzt/Dj269OnUq1u/jj279u3cu3v/Dj68+PHky5s/jz69+vXs27t/Dz++/Pn069u/jz+//v38+/tw/w9ggAIOSGCBBh6IYIIKLshggw4+CGGEEk5IYYUWXohhhhpuyGGHHn4IYogijkhiiSaeiGKKKq7IYosuvghjjDLOSGONNt6IY4467shjjz7+CGSQQg5JZJFGHolkkkouyWSTTj4JZZRSTklllRsVAAA7
"""
blank_img_data = base64.b64decode(blank_img_b64)
blank_image_path = temp_dir + 'blank_img.gif'
blank_img_file = open(blank_image_path, 'wb')
blank_img_file.write(blank_img_data)
blank_img_file.close()
blank_image = Image.open(blank_image_path)
blank = blank_image.resize((128, 128), Image.ANTIALIAS)
blank = ImageTk.PhotoImage(blank)
blank_image.close()

# 'Upload Control4 Driver' Frame
c4z_x = 5
c4z_y = 5

# 'Upload Replacement Image' Frame
replacement_x = 0
replacement_y = 0

# Global Variables
global c4_driver
device_icon_dir = temp_dir + 'driver/www/icons/device/'
icon_dir = temp_dir + 'driver/www/icons/'
replacement_image_path = temp_dir + 'replacement_icon.png'
orig_file_dir = ''
orig_file_path = ''
driver_selected = False
replacement_selected = False
schedule_entry_restore = False
restore_entry_string = ''
time_var = 0


class Icon:
    def __init__(self, path: str, name: str, size: int):
        self.path = path
        self.name = name
        self.size = size

        for i in reversed(range(len(path))):
            if path[i] == '.':
                self.type = path[i: len(path)]


class IconGroup:
    def __init__(self, icons: list):
        self.name = icons[0].name
        self.path = icons[0].path
        self.icons = icons

    def replace_icon(self):
        replacement_icon = Image.open(replacement_image_path)
        for icon in self.icons:
            if not os.path.isfile(icon.path + '.orig'):
                shutil.copy(icon.path, icon.path + '.orig')
            new_icon = replacement_icon.resize((icon.size, icon.size))
            new_icon.save(icon.path)
        c4z_panel.restore_button['state'] = ACTIVE
        c4z_panel.restore_all_button['state'] = ACTIVE
        c4z_panel.update_icon()

    def restore_icon(self):
        for icon in self.icons:
            if os.path.isfile(icon.path + '.orig'):
                shutil.copy(icon.path + '.orig', icon.path)
                os.remove(icon.path + '.orig')
        c4z_panel.restore_button['state'] = DISABLED
        disable_all_button = True
        for group in c4_driver.icon_groups:
            if os.path.isfile(group.icons[0].path + '.orig'):
                disable_all_button = False
        if disable_all_button:
            c4z_panel.restore_all_button['state'] = DISABLED
        c4z_panel.update_icon()


class C4Driver:
    def __init__(self, icons: list):
        self.icon_groups = icons
        self.current_icon = 0

    def inc_current_icon(self, step=1):
        if step > 0:
            if self.current_icon + step >= len(self.icon_groups):
                self.current_icon = self.current_icon + step - len(self.icon_groups)
            else:
                self.current_icon += 1
        else:
            if self.current_icon + step < 0:
                self.current_icon = self.current_icon + step + len(self.icon_groups)
            else:
                self.current_icon -= 1

        if os.path.isfile(self.icon_groups[self.current_icon].path + '.orig'):
            c4z_panel.restore_button['state'] = ACTIVE
        else:
            c4z_panel.restore_button['state'] = DISABLED

        c4z_panel.update_icon()


class C4zPanel:
    def __init__(self):
        self.x = 5
        self.y = 5

        # Labels
        self.blank_image_label = tk.Label(root, image=blank)
        self.blank_image_label.image = blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        self.icon_label = tk.Label(root, text='0 of 0')
        self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

        self.icon_name_label = tk.Label(root, text='icon name')
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(root, text='Open', width=10, command=upload_c4z)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.restore_button = tk.Button(root, text='Restore \n Original Icon', command=restore_icon)
        self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.restore_button['state'] = DISABLED

        self.restore_all_button = tk.Button(root, text='Restore All', command=restore_all)
        self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.restore_all_button['state'] = DISABLED

        self.prev_icon_button = tk.Button(root, text='Prev', command=prev_icon, width=5)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = tk.Button(root, text='Next', command=next_icon, width=5)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = tk.Entry(root, width=25)
        self.file_entry_field.insert(0, 'Select .c4z file...')
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field['state'] = DISABLED

    def update_pos(self, new_x=None, new_y=None):
        if new_x:
            self.x = new_x
        if new_y:
            self.y = new_y
        # Labels
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')
        # Buttons
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')
        self.restore_button.place(x=228 + self.x, y=71 + self.y, anchor='n')
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        # Entry
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')

    def update_icon(self):
        icon_image = Image.open(c4_driver.icon_groups[c4_driver.current_icon].path)

        icon = icon_image.resize((128, 128), Image.ANTIALIAS)
        icon = ImageTk.PhotoImage(icon)
        self.blank_image_label = tk.Label(root, image=icon)
        self.blank_image_label.image = icon
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        self.icon_label.config(text='icon: ' + str(c4_driver.current_icon + 1) +
                                    ' of ' + str(len(c4_driver.icon_groups)))
        self.icon_name_label.config(text='name: ' + c4_driver.icon_groups[c4_driver.current_icon].name)

    def blank_icon(self):
        self.blank_image_label = tk.Label(root, image=blank)
        self.blank_image_label.image = blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.icon_label.config(text='icon: 0 of 0')
        self.icon_name_label.config(text='name:')
        self.prev_icon_button['state'] = DISABLED
        self.next_icon_button['state'] = DISABLED
        replacement_panel.prev_icon_button['state'] = DISABLED
        replacement_panel.next_icon_button['state'] = DISABLED


class ReplacementPanel:
    def __init__(self):
        self.x = 310
        self.y = 5

        # Labels
        self.blank_image_label = tk.Label(root, image=blank)
        self.blank_image_label.image = blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(root, text='Open', width=10, command=upload_replacement)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.replace_all_button = tk.Button(root, text='Replace All', command=replace_all)
        self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.replace_all_button['state'] = DISABLED

        self.replace_button = tk.Button(root, text='Replace \n Current Icon', command=replace_icon)
        self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.replace_button['state'] = DISABLED

        self.prev_icon_button = tk.Button(root, text='Prev', command=prev_icon, width=5)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = tk.Button(root, text='Next', command=next_icon, width=5)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = tk.Entry(root, width=25)
        self.file_entry_field.insert(0, 'Select Image file...')
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field['state'] = DISABLED

    def update_pos(self, new_x=None, new_y=None):
        if new_x:
            self.x = new_x
        if new_y:
            self.y = new_y
        # Labels
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        # Buttons
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')
        self.replace_button.place(x=228 + self.x, y=71 + self.y, anchor='n')
        self.replace_all_button.place(x=228 + self.x, y=71 + self.y, anchor='n')
        self.replace_button.place(x=228 + self.x, y=71 + self.y, anchor='n')
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        # Entry
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')

    def update_icon(self):
        if replacement_selected:
            icon_image = Image.open(replacement_image_path)
            icon = icon_image.resize((128, 128), Image.ANTIALIAS)
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label = tk.Label(root, image=icon)
            self.blank_image_label.image = icon
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')


class ExportPanel:
    def __init__(self):
        self.x = 615
        self.y = 0

        # Labels
        self.driver_name_label = tk.Label(root, text='Driver Name:')
        self.driver_name_label.place(x=65 + self.x, y=160 + self.y, anchor='w')

        # Buttons
        self.export_button = tk.Button(root, text='Export', width=20, command=export_c4z)
        self.export_button.place(x=145 + self.x, y=195 + self.y, anchor='n')
        self.export_button['state'] = DISABLED

        # Entry
        self.driver_name_entry = tk.Entry(root, width=25)
        self.driver_name_entry.insert(0, 'New Driver')
        self.driver_name_entry.place(x=145 + self.x, y=170 + self.y, anchor='n')

        # Checkboxes
        self.modify_xml = IntVar(value=1)
        self.modify_xml_check = Checkbutton(root,
                                            text="modify driver.xml",
                                            variable=self.modify_xml).place(x=63 + self.x, y=135 + self.y, anchor='w')
        self.over_orig = IntVar()
        self.over_orig_check = Checkbutton(root,
                                            text="overwrite original file",
                                            variable=self.over_orig).place(x=63 + self.x, y=105 + self.y, anchor='w')


# Functions
def upload_c4z():
    global driver_selected
    global replacement_selected
    global c4_driver
    global schedule_entry_restore
    global restore_entry_string
    global orig_file_dir
    global orig_file_path

    if c4z_panel.file_entry_field.get() != 'Select .c4z file...' and \
            c4z_panel.file_entry_field.get() != 'Invalid driver selected...':
        c4_driver_bak = c4_driver
        if os.path.isdir(temp_dir + 'driver'):
            shutil.copytree(temp_dir + 'driver', temp_dir + '/bak/')

    icon_objects = []
    filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])

    if filename:
        if os.path.isdir(temp_dir + 'driver'):
            shutil.rmtree(temp_dir + 'driver')

        shutil.unpack_archive(filename, temp_dir + 'driver', 'zip')

        if os.path.isdir(device_icon_dir):
            icon_list = os.listdir(device_icon_dir)
            for i in range(len(icon_list)):
                temp_name = ''
                temp_size = ''
                get_size = False
                for letter in icon_list[i]:
                    if letter == '.':
                        break
                    else:
                        if get_size:
                            temp_size += letter
                        if letter == '_':
                            get_size = True
                        elif not get_size:
                            temp_name += letter
                icon_objects.append(Icon(device_icon_dir + str(icon_list[i]), temp_name, int(temp_size)))
        if os.path.isdir(icon_dir):
            icon_list = os.listdir(icon_dir)
            for i in range(len(icon_list)):
                if icon_list[i][len(icon_list[i]) - 4] == '.':
                    if 'device_lg' not in icon_list[i] and 'device_sm' not in icon_list[i]:
                        temp_name = ''
                        temp_size = ''
                        get_size = False
                        for letter in icon_list[i]:
                            if letter == '.':
                                break
                            else:
                                if get_size:
                                    temp_size += letter
                                if letter == '_':
                                    get_size = True
                                elif not get_size:
                                    temp_name += letter
                        icon_objects.append(Icon(icon_dir + str(icon_list[i]), temp_name, int(temp_size)))
            for i in range(len(icon_list)):
                if icon_list[i][len(icon_list[i]) - 4] == '.':
                    if 'device_lg' in icon_list[i]:
                        icon_objects.append(Icon(icon_dir + str(icon_list[i]), 'device', 32))
                    elif 'device_sm' in icon_list[i]:
                        icon_objects.append(Icon(icon_dir + str(icon_list[i]), 'device', 16))

        icon_groups = []
        temp_list = []
        for i in range(len(icon_objects)):
            if not temp_list:
                temp_list.append(icon_objects[i])
            elif icon_objects[i].name == temp_list[0].name:
                temp_list.append(icon_objects[i])
            else:
                new_icon_group = IconGroup(temp_list)
                icon_groups.append(new_icon_group)
                temp_list = [icon_objects[i]]
            if i == len(icon_objects) - 1:
                new_icon_group = IconGroup(temp_list)
                icon_groups.append(new_icon_group)
                temp_list = ''

        c4_driver = C4Driver(icon_groups)
        preserve_prev_next = False
        if len(c4_driver.icon_groups) > 0:
            c4z_panel.file_entry_field['state'] = NORMAL
            c4z_panel.file_entry_field.delete(0, 'end')
            c4z_panel.file_entry_field.insert(0, filename)
            c4z_panel.file_entry_field['state'] = 'readonly'
            orig_file_path = filename
            for i in reversed(range(len(orig_file_path))):
                if orig_file_path[i] == '/':
                    orig_file_dir = orig_file_path[0:i + 1]
                    break
            driver_selected = True
            c4z_panel.update_icon()
        else:
            c4z_panel.file_entry_field['state'] = NORMAL
            if c4z_panel.file_entry_field.get() != 'Select .c4z file...' and \
                    c4z_panel.file_entry_field.get() != 'Invalid driver selected...':
                # noinspection PyUnboundLocalVariable
                c4_driver = c4_driver_bak
                schedule_entry_restore = True
                restore_entry_string = c4z_panel.file_entry_field.get()
                preserve_prev_next = True
                if os.path.isdir(temp_dir + '/driver/'):
                    shutil.rmtree(temp_dir + '/driver/')
                shutil.copytree(temp_dir + '/bak/', temp_dir + '/driver/')
            c4z_panel.file_entry_field.delete(0, 'end')
            c4z_panel.file_entry_field.insert(0, 'Invalid driver selected...')
            c4z_panel.file_entry_field['state'] = DISABLED

        if not preserve_prev_next:
            if len(c4_driver.icon_groups) <= 1:
                c4z_panel.prev_icon_button['state'] = DISABLED
                c4z_panel.next_icon_button['state'] = DISABLED
                replacement_panel.prev_icon_button['state'] = DISABLED
                replacement_panel.next_icon_button['state'] = DISABLED
            elif len(c4_driver.icon_groups) > 1:
                c4z_panel.prev_icon_button['state'] = ACTIVE
                c4z_panel.next_icon_button['state'] = ACTIVE
                replacement_panel.prev_icon_button['state'] = ACTIVE
                replacement_panel.next_icon_button['state'] = ACTIVE

        if replacement_selected:
            if driver_selected:
                replacement_panel.replace_button['state'] = ACTIVE
                replacement_panel.replace_all_button['state'] = ACTIVE
            else:
                replacement_panel.replace_button['state'] = DISABLED
                replacement_panel.replace_all_button['state'] = DISABLED
        if driver_selected:
            export_panel.export_button['state'] = ACTIVE

        if os.path.isdir(temp_dir + '/bak/'):
            shutil.rmtree(temp_dir + '/bak/')


def upload_replacement():
    global driver_selected
    global replacement_selected

    filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"), ("Image", "*.gif"),
                                                     ("Image", "*.jpeg")])

    if filename:
        shutil.copy(filename, temp_dir + 'replacement_icon.png')

        replacement_panel.file_entry_field['state'] = NORMAL
        replacement_panel.file_entry_field.delete(0, 'end')
        replacement_panel.file_entry_field.insert(0, filename)
        replacement_panel.file_entry_field['state'] = 'readonly'

        if driver_selected:
            replacement_panel.replace_button['state'] = ACTIVE
            replacement_panel.replace_all_button['state'] = ACTIVE
        else:
            replacement_panel.replace_button['state'] = DISABLED
            replacement_panel.replace_all_button['state'] = DISABLED

        if os.path.isfile(temp_dir + 'replacement_icon.png'):
            replacement_selected = True
            replacement_panel.update_icon()


def restore_icon():
    c4_driver.icon_groups[c4_driver.current_icon].restore_icon()


def replace_icon():
    c4_driver.icon_groups[c4_driver.current_icon].replace_icon()


def restore_all():
    for group in c4_driver.icon_groups:
        group.restore_icon()
    c4z_panel.restore_button['state'] = DISABLED
    c4z_panel.restore_all_button['state'] = DISABLED
    c4z_panel.update_icon()


def replace_all():
    for group in c4_driver.icon_groups:
        group.replace_icon()
    c4z_panel.restore_button['state'] = ACTIVE
    c4z_panel.restore_all_button['state'] = ACTIVE
    c4z_panel.update_icon()


def prev_icon():
    c4_driver.inc_current_icon(step=-1)


def next_icon():
    c4_driver.inc_current_icon()


def export_c4z():
    def append_line(array: list, string: str):
        encoded_str = string.encode("ascii", "ignore")
        decoded_str = encoded_str.decode()
        array.append(decoded_str)

    driver_name = export_panel.driver_name_entry.get()
    temp = ''
    for letter in driver_name:
        if str(letter).isalnum() or str(letter) == '_' or str(letter) == '-' or str(letter) == ' ':
            temp += str(letter)
    driver_name = temp
    export_panel.driver_name_entry.delete(0, 'end')
    export_panel.driver_name_entry.insert(0, driver_name)

    dir_list = os.listdir(icon_dir)
    for i in range(len(dir_list)):
        if '.orig' in dir_list[i]:
            if not os.path.isdir(icon_dir + '/original_icons'):
                os.mkdir(icon_dir + '/original_icons')
            shutil.copy(icon_dir + dir_list[i], icon_dir + '/original_icons/' + dir_list[i].replace('.orig', ''))
            os.remove(icon_dir + dir_list[i])
    dir_list = os.listdir(device_icon_dir)
    for i in range(len(dir_list)):
        if '.orig' in dir_list[i]:
            if not os.path.isdir(device_icon_dir + '/original_icons'):
                os.mkdir(device_icon_dir + '/original_icons')
            shutil.copy(device_icon_dir + dir_list[i], device_icon_dir + '/original_icons/' +
                        dir_list[i].replace('.orig', ''))
            os.remove(device_icon_dir + dir_list[i])

    if export_panel.modify_xml.get() == 1:
        os.rename(temp_dir + '/driver/driver.xml', temp_dir + '/driver/driver.txt')
        driver_xml_file = open(temp_dir + '/driver/driver.txt', errors='ignore')
        driver_xml_lines = driver_xml_file.readlines()
        driver_xml_file.close()
        modified_xml_lines = []

        do_name_swap = True
        update_modified_date = True
        proxy_step2 = False
        icon_step2 = False
        old_driver_name = ''
        old_icon_path = ''
        for line in driver_xml_lines:
            printed_line = False
            if do_name_swap:
                if '<name>' in line:
                    result = re.search('<name>(.*)</name>', line)
                    if result:
                        line = line.replace(result.group(1), driver_name)
                    do_name_swap = False
                    append_line(modified_xml_lines, line)
                    printed_line = True
            if update_modified_date:
                if '<modified>' in line:
                    result = re.search('<modified>(.*)</modified>', line)
                    if result:
                        modified_datestamp = str(datetime.now().strftime("%m/%d/%Y %H:%M"))
                        line = line.replace(result.group(1), modified_datestamp)
                        append_line(modified_xml_lines, line)
                        printed_line = True
            if '<proxy' in line:
                if not proxy_step2:
                    temp_str = ''
                    temp_step2 = False
                    for l in line:
                        if not temp_step2:
                            if len(temp_str) < 6:
                                temp_str += l
                            else:
                                temp_str = temp_str[1:len(temp_str)]
                                temp_str += l
                        else:
                            if l != '"':
                                old_driver_name += l
                            else:
                                break
                        if temp_str == 'name="':
                            temp_step2 = True
                    line = line.replace(old_driver_name, driver_name)
                    append_line(modified_xml_lines, line)
                    printed_line = True
                    proxy_step2 = True
                else:
                    if 'name="' + old_driver_name + '"' in line:
                        line = line.replace('name="' + old_driver_name + '"', 'name="' + driver_name + '"')
                        append_line(modified_xml_lines, line)
                        printed_line = True
            if '<Icon' in line:
                if not icon_step2:
                    result = re.search('driver/(.*)/icons', line)
                    if result:
                        old_icon_path = result.group(1)
                        line = line.replace(old_icon_path, driver_name)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                else:
                    if old_icon_path in line:
                        line = line.replace(old_icon_path, driver_name)
                        append_line(modified_xml_lines, line)
                        printed_line = True
            if '<creator>' in line:
                result = re.search('<creator>(.*)</creator>', line)
                if result:
                    line = line.replace(result.group(1), 'C4IconSwapper')
                    append_line(modified_xml_lines, line)
                    printed_line = True
            if '<manufacturer>' in line:
                result = re.search('<manufacturer>(.*)</manufacturer>', line)
                if result:
                    line = line.replace(result.group(1), 'C4IconSwapper')
                    append_line(modified_xml_lines, line)
                    printed_line = True
            if not printed_line:
                append_line(modified_xml_lines, line)

        driver_xml_file = open(temp_dir + '/driver/driver.txt', 'w', errors='ignore')
        driver_xml_file.writelines(modified_xml_lines)
        driver_xml_file.close()
        os.rename(temp_dir + '/driver/driver.txt', temp_dir + '/driver/driver.xml')

    def confirm_write(ran_name=False):
        if ran_name:
            ran_file_name = 'IcnSwp_'
            for _ in range(0, 6):
                ran_file_name += str(random.randint(0, 9))
            if os.path.isfile(cur_dir + '/' + ran_file_name + '.c4z'):
                os.remove(cur_dir + '/' + ran_file_name + '.c4z')
            if os.path.isfile(cur_dir + '/' + ran_file_name + '.zip'):
                os.remove(cur_dir + '/' + ran_file_name + '.zip')
            shutil.make_archive(ran_file_name, 'zip', temp_dir + '/driver')
            base_path = os.path.splitext(cur_dir + '/' + ran_file_name + '.zip')[0]
            os.rename(cur_dir + '/' + ran_file_name + '.zip', base_path + '.c4z')
        else:
            if os.path.isfile(cur_dir + '/' + driver_name + '.c4z'):
                os.remove(cur_dir + '/' + driver_name + '.c4z')
            if os.path.isfile(cur_dir + '/' + driver_name + '.zip'):
                os.remove(cur_dir + '/' + driver_name + '.zip')
            shutil.make_archive(driver_name, 'zip', temp_dir + '/driver')
            base_path = os.path.splitext(cur_dir + '/' + driver_name + '.zip')[0]
            os.rename(cur_dir + '/' + driver_name + '.zip', base_path + '.c4z')

        pop.destroy()

    if export_panel.over_orig.get() == 1:
        temp_name = 'IcnSwp'
        for _ in range(0, 6):
            temp_name += str(random.randint(0, 9))
        try:
            if not os.path.isfile(orig_file_path + '.orig'):
                shutil.copy(orig_file_path, orig_file_path + '.orig')
            else:
                shutil.copy(orig_file_path, orig_file_path + '.' + temp_name)
                os.remove(orig_file_path + '.' + temp_name)
            shutil.make_archive(temp_name, 'zip', temp_dir + '/driver')
            base = os.path.splitext(cur_dir + '/' + temp_name + '.zip')[0]
            os.rename(cur_dir + '/' + temp_name + '.zip', base + '.c4z')
            os.remove(orig_file_path)
            shutil.copy(base + '.c4z', orig_file_path)
            os.remove(base + '.c4z')
        except IOError as x:
            pop = Toplevel(root)
            pop.title('Cannot Overwrite Original File')
            pop.geometry('239x95')
            pop.grab_set()
            pop.transient(root)
            pop.resizable(False, False)

            label_text = 'Access Denied to: ' + orig_file_dir
            access_label = Label(pop, text=label_text)
            access_label.grid(row=0, column=0, columnspan=2, sticky='w')
            pop.update()
            if 240 <= access_label.winfo_width():
                new_size = str(access_label.winfo_width()) + 'x95'
                pop.geometry(new_size)
                pop.update()

            write_label = Label(pop, text='Export to Current Directory Instead?')
            write_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=10)

            no_button = tk.Button(pop, text='No', width='10', command=pop.destroy)
            no_button.grid(row=2, column=0, sticky='w', padx=5)

            yes_button = tk.Button(pop, text='Yes', width='10', command=confirm_write)
            yes_button.grid(row=2, column=0, sticky='w', padx=90)
    else:
        if os.path.isfile(cur_dir + '/' + driver_name + '.c4z') or os.path.isfile(
                cur_dir + '/' + driver_name + '.zip'):
            pop = Toplevel(root)
            pop.title('Overwrite')
            pop.geometry('239x70')
            pop.grab_set()
            pop.transient(root)
            pop.resizable(False, False)

            confirm_label = Label(pop, text='Would you like to overwrite the existing file?')
            confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

            no_button = tk.Button(pop, text='No', width='10', command=pop.destroy)
            no_button.grid(row=2, column=0, sticky='e', padx=5)

            yes_button = tk.Button(pop, text='Yes', width='10', command=confirm_write)
            yes_button.grid(row=2, column=1, sticky='w', padx=5)
        else:
            shutil.make_archive(driver_name, 'zip', temp_dir + '/driver')
            base = os.path.splitext(cur_dir + '/' + driver_name + '.zip')[0]
            os.rename(cur_dir + '/' + driver_name + '.zip', base + '.c4z')


def restore_entry_text():
    global restore_entry_string
    global schedule_entry_restore
    global time_var

    if schedule_entry_restore:
        time_var = int(round(time.time() * 100))
        schedule_entry_restore = False
    elif time_var != 0:
        if int(round(time.time() * 100)) - time_var > 3:
            c4z_panel.file_entry_field['state'] = NORMAL
            c4z_panel.file_entry_field.delete(0, 'end')
            c4z_panel.file_entry_field.insert(0, restore_entry_string)
            c4z_panel.file_entry_field['state'] = 'readonly'
            restore_entry_string = ''
            time_var = 0

    root.after(2000, restore_entry_text)


# Separators
separator0 = ttk.Separator(root, orient='vertical')
separator0.place(x=305, y=0, relwidth=0.2, relheight=1)

separator1 = ttk.Separator(root, orient='vertical')
separator1.place(x=610, y=0, relwidth=0.2, relheight=1)

# Version Label
version_label = Label(root, text=version).place(relx=1, rely=1.01, anchor='se')

# Initialize
c4z_panel = C4zPanel()
replacement_panel = ReplacementPanel()
export_panel = ExportPanel()

root.after(0, restore_entry_text)
root.mainloop()

shutil.rmtree(temp_dir)
