import os
import shutil
import base64
import time
import random
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import ImageTk, Image
from datetime import datetime

version = '3.2b'


class RootWin:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry('915x250')
        self.root.title('C4 Icon Swapper')
        self.root.resizable(False, False)

        # Creating temporary directory
        self.cur_dir = os.getcwd() + '/'
        self.temp_dir = self.cur_dir + 'temp/'
        if not os.path.isdir(self.temp_dir):
            os.mkdir(self.temp_dir)

        self.device_icon_dir = self.temp_dir + 'driver/www/icons/device/'
        self.icon_dir = self.temp_dir + 'driver/www/icons/'
        self.replacement_image_path = self.temp_dir + 'replacement_icon.png'
        self.orig_file_dir = ''
        self.orig_file_path = ''
        self.driver_selected = False
        self.replacement_selected = False
        self.schedule_entry_restore = False
        self.restore_entry_string = ''
        self.time_var = 0

        # Base64 encoded blank image
        # Decoding and creating a temporary image file
        blank_img_b64 = \
            """
        R0lGODlhpAGkAYAAAAAAAP///ywAAAAApAGkAQAC/4yPqcvtD6OctNqLs968+w+G4kiW5omm6sq27gvH8kzX9o3n+s73/g8MCofEovGITCqXzKbzCY1Kp9Sq9YrNarfcrvcLDovH5LL5jE6r1+y2+w2Py+f0uv2Oz+v3/L7/DxgoOEhYaHiImKi4yNjo+AgZKTlJWWl5iZmpucnZ6fkJGio6SlpqeoqaqrrK2ur6ChsrO0tba3uLm6u7y9vr+wscLDxMXGx8jJysvMzc7PwMHS09TV1tfY2drb3N3e39DR4uPk5ebn6Onq6+zt7u/g4fLz9PX29/j5+vv8/f7/8PMKDAgQQLGjyIMKHChQwbOnwIMaLEiRQrWryIMaPGjf8cO3r8CDKkyJEkS5o8iTKlypUsW7p8CTOmzJk0a9q8iTOnzp08e/r8CTSo0KFEixo9ijSp0qVMmzp9CjWq1KlUq1q9ijWr1q1cu3r9Cjas2LFky5o9izat2rVs27p9Czeu3Ll069q9izev3r18+/r9Cziw4MGECxs+jDix4sWMGzt+DDmy5MmUK1u+jDmz5s2cO3v+DDq06NGkS5s+jTq16tWsW7t+DTu27Nm0a9u+jTu37t28e/v+DTy48OHEixs/jjy58uXMmzt/Dj269OnUq1u/jj279u3cu3v/Dj68+PHky5s/jz69+vXs27t/Dz++/Pn069u/jz+//v38+/tw/w9ggAIOSGCBBh6IYIIKLshggw4+CGGEEk5IYYUWXohhhhpuyGGHHn4IYogijkhiiSaeiGKKKq7IYosuvghjjDLOSGONNt6IY4467shjjz7+CGSQQg5JZJFGHolkkkouyWSTTj4JZZRSTklllRsVAAA7
        """
        blank_img_data = base64.b64decode(blank_img_b64)
        blank_image_path = self.temp_dir + 'blank_img.gif'
        blank_img_file = open(blank_image_path, 'wb')
        blank_img_file.write(blank_img_data)
        blank_img_file.close()
        blank_image = Image.open(blank_image_path)
        blank = blank_image.resize((128, 128), Image.ANTIALIAS)
        self.blank = ImageTk.PhotoImage(blank)
        blank_image.close()

        # Base64 encoded icon
        # Decoding and creating a temporary image file
        win_icon = \
            """
        AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAABMLAAATCwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEAAQEBAIODg4RFRUVHBUVFRwVFRUcFRUVHBUVFRwVFRUcDg4OEQMDAwIEBAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEOAgICfQEBAcwBAQHcAQEB3AEBAdwBAQHcAQEB3AEBAdwBAQHMAgICfAEBAQ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVFRUA////AAEBAXsAAAD7EBAQ/yAgIP8gICD/ICAg/yAgIP8gICD/ICAg/xAQEP8AAAD7AgICe////wAWFhYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYGBgAGBgYPAAAAyQ8PD/+srKz/5OTk/+Pj4//j4+P/4+Pj/+Pj4//k5OT/rKys/w8PD/8AAADJBgYGDwYGBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8PDwATExMCCQkJDQcHB0QAAADoKioq/+np6f//////8PDw//b29v/29vb/8PDw///////o6Oj/Kioq/wAAAOgHBwdECQkJDgwMDAMPDw8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQEBDgMDA30BAQHKAAAA6QAAAP9tbW3//v7+/+/v7/9PT0//XV1d/11dXf9PT0//7+/v//7+/v9tbW3/AAAA/wAAAOkBAQHMAgICiAUFBRYDAwMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAgIAN/f3wACAgJ9AAAA/A8PD/8oKCj/bGxs/+Xl5f//////7u7u/zU1Nf8AAAD/AAAA/zc3N//v7+///////+Xl5f9sbGz/KCgo/xEREf8AAAD/AgIChzQ0NAENDQ0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEhIAEhISEQEBAcsQEBD/rKys/+vr6//8/Pz/////////////////jY2N/wICAv8CAgL/jY2N//////////////////v7+//r6+v/sbGx/xEREf8BAQHNExMTEhQUFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABUVFQAUFBQeAQEB3iEhIf/i4uL//v7+/+rq6v/p6en//Pz8///////u7u7/ZGRk/2VlZf/u7u7///////z8/P/p6en/6urq//7+/v/i4uL/ISEh/wEBAd4UFBQeFRUVAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWFhYAAAAAAAEBAVIAAAD2PT09/9zc3P92dnb/Kioq/yoqKv91dXX/6+vr///////29vb/9vb2///////q6ur/dXV1/yoqKv8rKyv/d3d3/9zc3P88PDz/AAAA9gMDA08BAQEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQEBAAGBgYGAQEBqgEBAf+Pj4//eHh4/wAAAP8AAAD/AAAA/wAAAP91dXX//v7+/////////////v7+/3V1df8AAAD/AAAA/wAAAP8AAAD/eXl5/42Njf8AAAD/AQEBpAwMDAUJCQkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACsAAADmHx8f/8PDw/8uLi7/AAAA/wAAAP8AAAD/AAAA/ywsLP/p6en////////////p6en/Kysr/wAAAP8AAAD/AAAA/wAAAP8uLi7/wcHB/x0dHf8AAADkBgYGKgUFBQAAAAAAAAAAAAAAAAAAAAAAAAAAABkZGQAAAAAAAgICaAAAAP5ZWVn/5eXl/ywsLP8AAAD/AAAA/wAAAP8AAAD/LCws/+rq6v///////////+np6f8rKyv/AAAA/wAAAP8AAAD/AAAA/y0tLf/l5eX/VlZW/wAAAP4EBARkAAAAAB0dHQAAAAAAAAAAAAAAAAAAAAAADQ0NADAwMAEBAQGeAAAA/5iYmP//////dXV1/wAAAP8AAAD/AAAA/wAAAP93d3f//v7+/////////////f39/3V1df8AAAD/AAAA/wAAAP8AAAD/d3d3//////+Tk5P/AAAA/wICApr///8AFBQUAAAAAAAAAAAAAAAAAAAAAAAEBAQABAQECwAAAMINDQ3/xsbG///////r6+v/dXV1/yoqKv8qKir/dnZ2/+vr6///////////////////////6urq/3V1df8qKir/Kysr/3Z2dv/r6+v//////8LCwv8MDAz/AAAAvwYGBgoGBgYAAAAAAAAAAAAAAAAAAAAAABMTEwASEhIWAAAA1RwcHP/d3d3////////////8/Pz/6enp/+np6f/8/Pz//////////////////////////////////Pz8/+np6f/p6en//Pz8////////////29vb/xsbG/8AAADTERERFRISEgAAAAAAAAAAAAAAAAAAAAAAFRUVABQUFBkBAQHZHh4e/+Dg4P/////////////////////////////////////////////////////////////////////////////////////////////////g4OD/Hh4e/wEBAdYWFhYXFxcXAAAAAAAAAAAAAAAAAAAAAAAICAgABwcHDgAAAMgTExP/0NDQ/////////////////////////////////////////////////////////////////////////////////////////////////9LS0v8UFBT/AAAAxwQEBA0EBAQAAAAAAAAAAAAAAAAAAAAAAA8PDwAWFhYDAQEBpwQEBP+qqqr/////////////////////////////////////////////////////////////////////////////////////////////////ra2t/wUFBf8BAQGoFBQUAw0NDQAAAAAAAAAAAAAAAAAAAAAARkZGAAAAAAACAgJqAAAA/2FhYf/8/Pz///////////////////////////////////////////////////////////////////////////////////////39/f9lZWX/AAAA/wMDA20AAAAANzc3AAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEAAUFBScAAADfFhYW/8PDw///////////////////////////////////////////////////////////////////////////////////////xcXF/xcXF/8AAADfBAQEJwMDAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAICAgANjY2AQMDA4IAAAD+QkJC/+Li4v///////////////////////////////////////////////////////////////////////////+Li4v9CQkL/AAAA/gMDA4EzMzMBCAgIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBgYABwcHGAEBAbkAAAD/S0tL/9nZ2f/////////////////////////////////////////////////////////////////V1dX/SEhI/wAAAP8BAQG2BgYGFgQEBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMDAwACgoKKwMDA8YAAAD/LCws/56env/r6+v///////////////////////////////////////7+/v/o6Oj/lpaW/ycnJ/8AAAD/AAAAvAAAACQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFdXVwAAAAAABQUFIwEBAaQAAAD3BgYG/zMzM/96enr/srKy/9LS0v/f39//39/f/9HR0f+vr6//dXV1/y4uLv8EBAT/AAAA9QICAp4DAwMfBAQEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEACQkJCwICAlkBAQG+AAAA8wAAAP8GBgb/FBQU/x4eHv8eHh7/ExMT/wUFBf8AAAD/AAAA8AEBAbUCAgJQCwsLCQAAAACysrIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAgIAAQEBAAwMDA4DAwNAAgICfwEBAa0AAADIAQEB2QEBAdkBAQHHAgICrAICAnkDAwM6BAQECwUFBQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkJABDQ0MADg4OBQgICA0LCwsZCwsLGQoKCg0WFhYE////AFJSUgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////////////////+AH///AA///wAP//4AB//4AAH/8AAA//AAAH/gAAB/4AAAf+AAAH/AAAA/wAAAP8AAAD+AAAA/gAAAH4AAAB+AAAAfgAAAH4AAAB/AAAA/wAAAP8AAAD/gAAB/8AAA//gAAf/8AAP//wAP///gf//////8=
        """
        icon_data = base64.b64decode(win_icon)
        temp_icon_file = self.temp_dir + 'icon.ico'
        icon_file = open(temp_icon_file, 'wb')
        icon_file.write(icon_data)
        icon_file.close()
        self.root.wm_iconbitmap(temp_icon_file)
        os.remove(temp_icon_file)

        self.c4_driver = None
        self.c4z_panel = C4zPanel(self)
        self.replacement_panel = ReplacementPanel(self)
        self.export_panel = ExportPanel(self)

        # Separators
        self.separator0 = ttk.Separator(self.root, orient='vertical').place(x=305, y=0, relheight=1)
        self.separator1 = ttk.Separator(self.root, orient='vertical').place(x=610, y=0, relheight=1)

        # Version Label
        self.version_label = Label(self.root, text=version).place(relx=1, rely=1.01, anchor='se')

        # Main Loop
        self.root.after(0, self.restore_entry_text)
        self.root.mainloop()
        shutil.rmtree(self.temp_dir)

    def restore_icon(self):
        self.c4_driver.icon_groups[self.c4_driver.current_icon].restore_icon()

    def replace_icon(self):
        self.c4_driver.icon_groups[self.c4_driver.current_icon].replace_icon()

    def restore_all(self):
        for group in self.c4_driver.icon_groups:
            group.restore_icon()
        self.c4z_panel.restore_button['state'] = DISABLED
        self.c4z_panel.restore_all_button['state'] = DISABLED
        self.c4z_panel.update_icon()

    def replace_all(self):
        for group in self.c4_driver.icon_groups:
            group.replace_icon()
        self.c4z_panel.restore_button['state'] = ACTIVE
        self.c4z_panel.restore_all_button['state'] = ACTIVE
        self.c4z_panel.update_icon()

    def prev_icon(self):
        self.c4_driver.inc_current_icon(step=-1)

    def next_icon(self):
        self.c4_driver.inc_current_icon()

    def restore_entry_text(self):
        if self.schedule_entry_restore:
            self.time_var = int(round(time.time() * 100))
            self.schedule_entry_restore = False
        elif self.time_var != 0:
            if int(round(time.time() * 100)) - self.time_var > 3:
                self.c4z_panel.file_entry_field['state'] = NORMAL
                self.c4z_panel.file_entry_field.delete(0, 'end')
                self.c4z_panel.file_entry_field.insert(0, self.restore_entry_string)
                self.c4z_panel.file_entry_field['state'] = 'readonly'
                self.restore_entry_string = ''
                self.time_var = 0

        self.root.after(2000, self.restore_entry_text)


class Icon:
    def __init__(self, path: str, name: str, size: int):
        self.path = path
        self.name = name
        self.size = size

        for i in reversed(range(len(path))):
            if path[i] == '.':
                self.type = path[i: len(path)]


class IconGroup:
    def __init__(self, icons: list, root_win):
        self.name = icons[0].name
        self.path = icons[0].path
        self.icons = icons
        self.root_win = root_win

    def replace_icon(self):
        replacement_icon = Image.open(self.root_win.replacement_image_path)
        for icon in self.icons:
            if not os.path.isfile(icon.path + '.orig'):
                shutil.copy(icon.path, icon.path + '.orig')
            new_icon = replacement_icon.resize((icon.size, icon.size))
            new_icon.save(icon.path)
        self.root_win.c4z_panel.restore_button['state'] = ACTIVE
        self.root_win.c4z_panel.restore_all_button['state'] = ACTIVE
        self.root_win.c4z_panel.update_icon()

    def restore_icon(self):
        for icon in self.icons:
            if os.path.isfile(icon.path + '.orig'):
                shutil.copy(icon.path + '.orig', icon.path)
                os.remove(icon.path + '.orig')
        self.root_win.c4z_panel.restore_button['state'] = DISABLED
        disable_all_button = True
        for group in self.root_win.c4_driver.icon_groups:
            if os.path.isfile(group.icons[0].path + '.orig'):
                disable_all_button = False
        if disable_all_button:
            self.root_win.c4z_panel.restore_all_button['state'] = DISABLED
        self.root_win.c4z_panel.update_icon()


class C4Driver:
    def __init__(self, icons: list, root_win):
        self.icon_groups = icons
        self.current_icon = 0
        self.root_win = root_win

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
            self.root_win.c4z_panel.restore_button['state'] = ACTIVE
        else:
            self.root_win.c4z_panel.restore_button['state'] = DISABLED

        self.root_win.c4z_panel.update_icon()


class C4zPanel:
    def __init__(self, root_win):
        self.x = 5
        self.y = 5
        self.root_win = root_win

        # Labels
        self.blank_image_label = tk.Label(self.root_win.root, image=self.root_win.blank)
        self.blank_image_label.image = self.root_win.blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        self.icon_label = tk.Label(self.root_win.root, text='0 of 0')
        self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

        self.icon_name_label = tk.Label(self.root_win.root, text='icon name')
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(self.root_win.root, text='Open', width=10, command=self.upload_c4z)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.restore_button = tk.Button(self.root_win.root, text='Restore \n Original Icon',
                                        command=self.root_win.restore_icon)
        self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.restore_button['state'] = DISABLED

        self.restore_all_button = tk.Button(self.root_win.root, text='Restore All', command=self.root_win.restore_all)
        self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.restore_all_button['state'] = DISABLED

        self.prev_icon_button = tk.Button(self.root_win.root, text='Prev', command=self.root_win.prev_icon, width=5)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = tk.Button(self.root_win.root, text='Next', command=self.root_win.next_icon, width=5)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = tk.Entry(self.root_win.root, width=25)
        self.file_entry_field.insert(0, 'Select .c4z file...')
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field['state'] = DISABLED

    def update_icon(self):
        icon_image = Image.open(self.root_win.c4_driver.icon_groups[self.root_win.c4_driver.current_icon].path)

        icon = icon_image.resize((128, 128), Image.ANTIALIAS)
        icon = ImageTk.PhotoImage(icon)
        self.blank_image_label = tk.Label(self.root_win.root, image=icon)
        self.blank_image_label.image = icon
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        self.icon_label.config(text='icon: ' + str(self.root_win.c4_driver.current_icon + 1) +
                                    ' of ' + str(len(self.root_win.c4_driver.icon_groups)))
        self.icon_name_label.config(text='name: ' +
                                         self.root_win.c4_driver.icon_groups[self.root_win.c4_driver.current_icon].name)

    def blank_icon(self):
        self.blank_image_label = tk.Label(self.root_win.root, image=self.root_win.blank)
        self.blank_image_label.image = self.root_win.blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.icon_label.config(text='icon: 0 of 0')
        self.icon_name_label.config(text='name:')
        self.prev_icon_button['state'] = DISABLED
        self.next_icon_button['state'] = DISABLED
        self.root_win.replacement_panel.prev_icon_button['state'] = DISABLED
        self.root_win.replacement_panel.next_icon_button['state'] = DISABLED

    def upload_c4z(self):
        if self.file_entry_field.get() != 'Select .c4z file...' and \
                self.file_entry_field.get() != 'Invalid driver selected...':
            c4_driver_bak = self.root_win.c4_driver
            if os.path.isdir(self.root_win.temp_dir + 'driver'):
                shutil.copytree(self.root_win.temp_dir + 'driver', self.root_win.temp_dir + '/bak/')
        else:
            c4_driver_bak = None

        icon_objects = []
        filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])

        if filename:
            if os.path.isdir(self.root_win.temp_dir + 'driver'):
                shutil.rmtree(self.root_win.temp_dir + 'driver')

            shutil.unpack_archive(filename, self.root_win.temp_dir + 'driver', 'zip')

            if os.path.isdir(self.root_win.device_icon_dir):
                icon_list = os.listdir(self.root_win.device_icon_dir)
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
                    icon_objects.append(Icon(self.root_win.device_icon_dir + str(icon_list[i]),
                                             temp_name, int(temp_size)))
            if os.path.isdir(self.root_win.icon_dir):
                icon_list = os.listdir(self.root_win.icon_dir)
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
                            icon_objects.append(Icon(self.root_win.icon_dir + str(icon_list[i]),
                                                     temp_name, int(temp_size)))
                for i in range(len(icon_list)):
                    if icon_list[i][len(icon_list[i]) - 4] == '.':
                        if 'device_lg' in icon_list[i]:
                            icon_objects.append(Icon(self.root_win.icon_dir + str(icon_list[i]), 'device', 32))
                        elif 'device_sm' in icon_list[i]:
                            icon_objects.append(Icon(self.root_win.icon_dir + str(icon_list[i]), 'device', 16))

            icon_groups = []
            temp_list = []
            for i in range(len(icon_objects)):
                if not temp_list:
                    temp_list.append(icon_objects[i])
                elif icon_objects[i].name == temp_list[0].name:
                    temp_list.append(icon_objects[i])
                else:
                    new_icon_group = IconGroup(temp_list, self.root_win)
                    icon_groups.append(new_icon_group)
                    temp_list = [icon_objects[i]]
                if i == len(icon_objects) - 1:
                    new_icon_group = IconGroup(temp_list, self.root_win)
                    icon_groups.append(new_icon_group)
                    temp_list = ''

            self.root_win.c4_driver = C4Driver(icon_groups, self.root_win)
            preserve_prev_next = False
            if len(self.root_win.c4_driver.icon_groups) > 0:
                self.file_entry_field['state'] = NORMAL
                self.file_entry_field.delete(0, 'end')
                self.file_entry_field.insert(0, filename)
                self.file_entry_field['state'] = 'readonly'
                orig_file_path = filename
                orig_driver_name = ''
                for i in reversed(range(len(orig_file_path))):
                    if orig_file_path[i] == '/':
                        self.root_win.orig_file_dir = orig_file_path[0:i + 1]
                        break
                    if orig_file_path[i] == '.':
                        orig_driver_name = '.'
                    if orig_driver_name != '':
                        if orig_driver_name == '.':
                            orig_driver_name = orig_file_path[i]
                        else:
                            orig_driver_name = orig_file_path[i] + orig_driver_name
                self.root_win.export_panel.driver_name_entry.delete(0, 'end')
                self.root_win.export_panel.driver_name_entry.insert(0, orig_driver_name)
                self.root_win.driver_selected = True
                self.update_icon()
            else:
                self.file_entry_field['state'] = NORMAL
                if self.file_entry_field.get() != 'Select .c4z file...' and \
                        self.file_entry_field.get() != 'Invalid driver selected...':
                    self.root_win.c4_driver = c4_driver_bak
                    self.root_win.schedule_entry_restore = True
                    self.root_win.restore_entry_string = self.file_entry_field.get()
                    preserve_prev_next = True
                    if os.path.isdir(self.root_win.temp_dir + '/driver/'):
                        shutil.rmtree(self.root_win.temp_dir + '/driver/')
                    shutil.copytree(self.root_win.temp_dir + '/bak/', self.root_win.temp_dir + '/driver/')
                self.file_entry_field.delete(0, 'end')
                self.file_entry_field.insert(0, 'Invalid driver selected...')
                self.file_entry_field['state'] = DISABLED

            if not preserve_prev_next:
                if len(self.root_win.c4_driver.icon_groups) <= 1:
                    self.prev_icon_button['state'] = DISABLED
                    self.next_icon_button['state'] = DISABLED
                    self.root_win.replacement_panel.prev_icon_button['state'] = DISABLED
                    self.root_win.replacement_panel.next_icon_button['state'] = DISABLED
                elif len(self.root_win.c4_driver.icon_groups) > 1:
                    self.prev_icon_button['state'] = ACTIVE
                    self.next_icon_button['state'] = ACTIVE
                    self.root_win.replacement_panel.prev_icon_button['state'] = ACTIVE
                    self.root_win.replacement_panel.next_icon_button['state'] = ACTIVE

            if self.root_win.replacement_selected:
                if self.root_win.driver_selected:
                    self.root_win.replacement_panel.replace_button['state'] = ACTIVE
                    self.root_win.replacement_panel.replace_all_button['state'] = ACTIVE
                else:
                    self.root_win.replacement_panel.replace_button['state'] = DISABLED
                    self.root_win.replacement_panel.replace_all_button['state'] = DISABLED
            if self.root_win.driver_selected:
                self.root_win.export_panel.export_button['state'] = ACTIVE

            if os.path.isdir(self.root_win.temp_dir + '/bak/'):
                shutil.rmtree(self.root_win.temp_dir + '/bak/')


class ReplacementPanel:
    def __init__(self, root_win):
        self.x = 310
        self.y = 5
        self.root_win = root_win

        # Labels
        self.blank_image_label = tk.Label(self.root_win.root, image=self.root_win.blank)
        self.blank_image_label.image = self.root_win.blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(self.root_win.root, text='Open', width=10, command=self.upload_replacement)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.replace_all_button = tk.Button(self.root_win.root, text='Replace All', command=self.root_win.replace_all)
        self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.replace_all_button['state'] = DISABLED

        self.replace_button = tk.Button(self.root_win.root, text='Replace \n Current Icon',
                                        command=self.root_win.replace_icon)
        self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.replace_button['state'] = DISABLED

        self.prev_icon_button = tk.Button(self.root_win.root, text='Prev', command=self.root_win.prev_icon, width=5)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = tk.Button(self.root_win.root, text='Next', command=self.root_win.next_icon, width=5)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = tk.Entry(self.root_win.root, width=25)
        self.file_entry_field.insert(0, 'Select Image file...')
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field['state'] = DISABLED

    def update_icon(self):
        if self.root_win.replacement_selected:
            icon_image = Image.open(self.root_win.replacement_image_path)
            icon = icon_image.resize((128, 128), Image.ANTIALIAS)
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label = tk.Label(self.root_win.root, image=icon)
            self.blank_image_label.image = icon
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

    def upload_replacement(self):
        filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"), ("Image", "*.gif"),
                                                         ("Image", "*.jpeg")])

        if filename:
            shutil.copy(filename, self.root_win.temp_dir + 'replacement_icon.png')

            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, filename)
            self.file_entry_field['state'] = 'readonly'

            if self.root_win.driver_selected:
                self.replace_button['state'] = ACTIVE
                self.replace_all_button['state'] = ACTIVE
            else:
                self.replace_button['state'] = DISABLED
                self.replace_all_button['state'] = DISABLED

            if os.path.isfile(self.root_win.temp_dir + 'replacement_icon.png'):
                self.root_win.replacement_selected = True
                self.update_icon()


class ExportPanel:
    def __init__(self, root_win):
        self.x = 615
        self.y = -20
        self.root_win = root_win

        # Labels
        self.driver_name_label = tk.Label(self.root_win.root, text='Driver Name:')
        self.driver_name_label.place(x=65 + self.x, y=160 + self.y, anchor='w')

        # Buttons
        self.export_button = tk.Button(self.root_win.root, text='Export', width=20, command=self.export_c4z)
        self.export_button.place(x=145 + self.x, y=195 + self.y, anchor='n')
        self.export_button['state'] = DISABLED

        # Entry
        self.driver_name_entry = tk.Entry(self.root_win.root, width=25)
        self.driver_name_entry.insert(0, 'New Driver')
        self.driver_name_entry.place(x=145 + self.x, y=170 + self.y, anchor='n')

        # Checkboxes
        self.modify_xml = IntVar(value=1)
        self.modify_xml_check = Checkbutton(self.root_win.root,
                                            text="modify driver.xml",
                                            variable=self.modify_xml).place(x=63 + self.x, y=135 + self.y, anchor='w')
        self.over_orig = IntVar()
        self.over_orig_check = Checkbutton(self.root_win.root,
                                            text="overwrite original file",
                                            variable=self.over_orig).place(x=63 + self.x, y=105 + self.y, anchor='w')

    def export_c4z(self):
        def append_line(array: list, string: str):
            encoded_str = string.encode("ascii", "ignore")
            decoded_str = encoded_str.decode()
            array.append(decoded_str)

        driver_name = self.driver_name_entry.get()
        temp = ''
        for letter in driver_name:
            if str(letter).isalnum() or str(letter) == '_' or str(letter) == '-' or str(letter) == ' ':
                temp += str(letter)
        driver_name = temp
        self.driver_name_entry.delete(0, 'end')
        self.driver_name_entry.insert(0, driver_name)

        dir_list = os.listdir(self.root_win.icon_dir)
        for i in range(len(dir_list)):
            if '.orig' in dir_list[i]:
                if not os.path.isdir(self.root_win.icon_dir + '/original_icons'):
                    os.mkdir(self.root_win.icon_dir + '/original_icons')
                shutil.copy(self.root_win.icon_dir + dir_list[i],
                            self.root_win.icon_dir + '/original_icons/' + dir_list[i].replace('.orig', ''))
                os.remove(self.root_win.icon_dir + dir_list[i])
        dir_list = os.listdir(self.root_win.device_icon_dir)
        for i in range(len(dir_list)):
            if '.orig' in dir_list[i]:
                if not os.path.isdir(self.root_win.device_icon_dir + '/original_icons'):
                    os.mkdir(self.root_win.device_icon_dir + '/original_icons')
                shutil.copy(self.root_win.device_icon_dir + dir_list[i],
                            self.root_win.device_icon_dir + '/original_icons/' +
                            dir_list[i].replace('.orig', ''))
                os.remove(self.root_win.device_icon_dir + dir_list[i])

        if self.modify_xml.get() == 1:
            os.rename(self.root_win.temp_dir + '/driver/driver.xml', self.root_win.temp_dir + '/driver/driver.txt')
            driver_xml_file = open(self.root_win.temp_dir + '/driver/driver.txt', errors='ignore')
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

            driver_xml_file = open(self.root_win.temp_dir + '/driver/driver.txt', 'w', errors='ignore')
            driver_xml_file.writelines(modified_xml_lines)
            driver_xml_file.close()
            os.rename(self.root_win.temp_dir + '/driver/driver.txt', self.root_win.temp_dir + '/driver/driver.xml')

        def confirm_write(ran_name=False):
            if ran_name:
                ran_file_name = 'IcnSwp_'
                for _ in range(0, 6):
                    ran_file_name += str(random.randint(0, 9))
                if os.path.isfile(self.root_win.cur_dir + ran_file_name + '.c4z'):
                    os.remove(self.root_win.cur_dir + ran_file_name + '.c4z')
                if os.path.isfile(self.root_win.cur_dir + ran_file_name + '.zip'):
                    os.remove(self.root_win.cur_dir + ran_file_name + '.zip')
                shutil.make_archive(ran_file_name, 'zip', self.root_win.temp_dir + '/driver')
                base_path = os.path.splitext(self.root_win.cur_dir + ran_file_name + '.zip')[0]
                os.rename(self.root_win.cur_dir + ran_file_name + '.zip', base_path + '.c4z')
            else:
                if os.path.isfile(self.root_win.cur_dir + driver_name + '.c4z'):
                    os.remove(self.root_win.cur_dir + driver_name + '.c4z')
                if os.path.isfile(self.root_win.cur_dir + driver_name + '.zip'):
                    os.remove(self.root_win.cur_dir + driver_name + '.zip')
                shutil.make_archive(driver_name, 'zip', self.root_win.temp_dir + '/driver')
                base_path = os.path.splitext(self.root_win.cur_dir + driver_name + '.zip')[0]
                os.rename(self.root_win.cur_dir + driver_name + '.zip', base_path + '.c4z')

            pop.destroy()

        if self.over_orig.get() == 1:
            temp_name = 'IcnSwp'
            for _ in range(0, 6):
                temp_name += str(random.randint(0, 9))
            try:
                if not os.path.isfile(self.root_win.orig_file_path + '.orig'):
                    shutil.copy(self.root_win.orig_file_path, self.root_win.orig_file_path + '.orig')
                else:
                    shutil.copy(self.root_win.orig_file_path, self.root_win.orig_file_path + '.' + temp_name)
                    os.remove(self.root_win.orig_file_path + '.' + temp_name)
                shutil.make_archive(temp_name, 'zip', self.root_win.temp_dir + '/driver')
                base = os.path.splitext(self.root_win.cur_dir + temp_name + '.zip')[0]
                os.rename(self.root_win.cur_dir + temp_name + '.zip', base + '.c4z')
                os.remove(self.root_win.orig_file_path)
                shutil.copy(base + '.c4z', self.root_win.orig_file_path)
                os.remove(base + '.c4z')
            except IOError as _:
                pop = Toplevel(self.root_win.root)
                pop.title('Cannot Overwrite Original File')
                pop.geometry('239x95')
                pop.grab_set()
                pop.transient(self.root_win.root)
                pop.resizable(False, False)

                label_text = 'Access Denied to: ' + self.root_win.orig_file_dir
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
            if os.path.isfile(self.root_win.cur_dir + driver_name + '.c4z') or os.path.isfile(
                    self.root_win.cur_dir + driver_name + '.zip'):
                pop = Toplevel(self.root_win.root)
                pop.title('Overwrite')
                pop.geometry('239x70')
                pop.grab_set()
                pop.transient(self.root_win.root)
                pop.resizable(False, False)

                confirm_label = Label(pop, text='Would you like to overwrite the existing file?')
                confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

                no_button = tk.Button(pop, text='No', width='10', command=pop.destroy)
                no_button.grid(row=2, column=0, sticky='e', padx=5)

                yes_button = tk.Button(pop, text='Yes', width='10', command=confirm_write)
                yes_button.grid(row=2, column=1, sticky='w', padx=5)
            else:
                shutil.make_archive(driver_name, 'zip', self.root_win.temp_dir + '/driver')
                base = os.path.splitext(self.root_win.cur_dir + driver_name + '.zip')[0]
                os.rename(self.root_win.cur_dir + driver_name + '.zip', base + '.c4z')
