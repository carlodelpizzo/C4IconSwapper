import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import ImageTk, Image
import os
import shutil
# import xml.dom.minidom as md
import base64

version = '3.0'

# Root Window
root = tk.Tk()
root.geometry('915x250')
root.title('C4 Icon Swapper')
root.resizable(False, False)
# root.wm_iconbitmap(temp_icon_file)
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
c4z_frame = Frame(root).place(x=0, y=0)
c4z_x = 5
c4z_y = 5

# 'Upload Replacement Image' Frame
replacement_frame = Frame(root).place(x=0, y=0)
replacement_x = 0
replacement_y = 0

# Global Variables
global c4_driver
device_icon_dir = temp_dir + 'driver/www/icons/device/'
icon_dir = temp_dir + 'driver/www/icons/'
driver_selected = False
replacement_selected = False


class Icon:
    def __init__(self, path: str, name: str, size: int):
        self.path = path
        self.name = name
        self.size = size

        for i in reversed(range(len(path))):
            if path[i] == '.':
                self.type = path[i: len(path)]


class C4Driver:
    def __init__(self, icons: list):
        self.icons = icons
        self.shown_icons = []
        for icon in self.icons:
            self.shown_icons.append(icon)
            temp_counter = 0
            for shown_icon in self.shown_icons:
                if icon.name == shown_icon.name:
                    temp_counter += 1
                    if temp_counter == 2:
                        self.shown_icons.pop()
        self.current_icon = 0

    def inc_current_icon(self, step=1):
        if step > 0:
            if self.current_icon + step >= len(self.shown_icons):
                self.current_icon = self.current_icon + step - len(self.shown_icons)
            else:
                self.current_icon += 1
        else:
            if self.current_icon + step < 0:
                self.current_icon = self.current_icon + step + len(self.shown_icons)
            else:
                self.current_icon -= 1

        c4z_panel.update_icon()


class C4zPanel:
    def __init__(self):
        self.x = 5
        self.y = 5

        # Labels
        self.blank_image_label = tk.Label(c4z_frame, image=blank)
        self.blank_image_label.image = blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        self.icon_label = tk.Label(c4z_frame, text='0 of 0')
        self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

        self.icon_name_label = tk.Label(c4z_frame, text='icon name')
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(c4z_frame, text='Open', width=10, command=upload_c4z)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.restore_button = tk.Button(c4z_frame, text='Restore \n Original Icon', command=restore_icon)
        self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.restore_button['state'] = DISABLED

        self.restore_all_button = tk.Button(c4z_frame, text='Restore All', command=restore_all)
        self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.restore_all_button['state'] = DISABLED

        self.prev_icon_button = tk.Button(c4z_frame, text='Prev', command=prev_icon, width=5)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = tk.Button(c4z_frame, text='Next', command=next_icon, width=5)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = tk.Entry(c4z_frame, width=25)
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
        icon_image = Image.open(c4_driver.shown_icons[c4_driver.current_icon].path)

        icon = icon_image.resize((128, 128), Image.ANTIALIAS)
        icon = ImageTk.PhotoImage(icon)
        self.blank_image_label = tk.Label(c4z_frame, image=icon)
        self.blank_image_label.image = icon
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        self.icon_label.config(text='icon: ' + str(c4_driver.current_icon + 1) +
                                    ' of ' + str(len(c4_driver.shown_icons)))
        self.icon_name_label.config(text='name: ' + c4_driver.shown_icons[c4_driver.current_icon].name)


class ReplacementPanel:
    def __init__(self):
        self.x = 310
        self.y = 5

        # Labels
        self.blank_image_label = tk.Label(c4z_frame, image=blank)
        self.blank_image_label.image = blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(c4z_frame, text='Open', width=10, command=upload_replacement)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.replace_all_button = tk.Button(c4z_frame, text='Replace All', command=replace_icon)
        self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.replace_all_button['state'] = DISABLED

        self.replace_button = tk.Button(c4z_frame, text='Replace \n Current Icon', command=replace_all)
        self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.replace_button['state'] = DISABLED

        self.prev_icon_button = tk.Button(c4z_frame, text='Prev', command=prev_icon, width=5)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = tk.Button(c4z_frame, text='Next', command=next_icon, width=5)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = tk.Entry(c4z_frame, width=25)
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


# Functions
def upload_c4z():
    global driver_selected
    global replacement_selected
    global c4_driver

    icon_objects = []
    filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])

    if filename:
        if os.path.isdir(temp_dir + 'driver'):
            shutil.rmtree(temp_dir + 'driver')

        c4z_panel.file_entry_field['state'] = NORMAL
        c4z_panel.file_entry_field.delete(0, 'end')
        c4z_panel.file_entry_field.insert(0, filename)
        c4z_panel.file_entry_field['state'] = 'readonly'
        shutil.unpack_archive(filename, temp_dir + 'driver', 'zip')

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

        icon_list = os.listdir(icon_dir)
        for i in range(len(icon_list)):
            if 'device_lg' in icon_list[i]:
                icon_objects.append(Icon(icon_dir + str(icon_list[i]), 'device', 32))
            if 'device_sm' in icon_list[i]:
                icon_objects.append(Icon(icon_dir + str(icon_list[i]), 'device', 16))
        driver_selected = True

        c4_driver = C4Driver(icon_objects)
        c4z_panel.update_icon()

        if len(c4_driver.shown_icons) == 1:
            c4z_panel.prev_icon_button['state'] = DISABLED
            c4z_panel.next_icon_button['state'] = DISABLED
        elif len(c4_driver.shown_icons) > 1:
            c4z_panel.prev_icon_button['state'] = ACTIVE
            c4z_panel.next_icon_button['state'] = ACTIVE


def upload_replacement():
    global driver_selected
    global replacement_selected

    filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"), ("Image", "*.gif"),
                                                     ("Image", "*.jpeg")])

    if filename:
        replacement_panel.file_entry_field['state'] = NORMAL
        replacement_panel.file_entry_field.delete(0, 'end')
        replacement_panel.file_entry_field.insert(0, filename)
        replacement_panel.file_entry_field['state'] = 'readonly'
        replacement_selected = True


def restore_icon():
    pass


def replace_icon():
    pass


def restore_all():
    pass


def replace_all():
    pass


def prev_icon():
    c4_driver.inc_current_icon(step=-1)


def next_icon():
    c4_driver.inc_current_icon()


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

root.mainloop()

shutil.rmtree(temp_dir)
