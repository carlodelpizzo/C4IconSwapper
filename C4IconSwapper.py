import filecmp
import os
import shutil
import base64
import time
import random
import re
import PIL.Image
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import ImageTk, Image
from datetime import datetime
from Base64Assets import *
from XMLObject import XMLObject

version = '5.6.4b'

letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
           'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
capital_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                   'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

conn_template = ['connection', '', [], [['id', '0', [], []], ['type', '0', [], []],
                                        ['connectionname', 'REPLACE', [], []],
                                        ['consumer', 'False', [], []], ['linelevel', 'True', [], []],
                                        ['classes', '', [], [['class', '', [], [['classname', 'REPLACE', [], []]]]]]]]


class C4IconSwapper:
    class C4zPanel:
        class SubIcon:
            def __init__(self, root_path: str, path: str, name: str, size: int):
                # Initialize Icon
                self.root = root_path
                self.path = path
                self.name = name
                self.size = size

                for i in reversed(range(len(path))):
                    if path[i] != '.':
                        self.type = path[i: len(path)]
                        break

        class Icon:
            def __init__(self, icons: list, extra=False):
                # Initialize Icon Group
                self.name = icons[0].name
                self.path = icons[0].path
                self.icons = icons
                self.extra = extra

        def __init__(self, upper_class):
            # Initialize C4z Panel
            self.x = 5
            self.y = 20
            self.uc = upper_class
            self.current_icon = 0
            self.icons = []
            self.extra_icons = 0
            self.valid_connections = ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI', 'STEREO', 'DIGITAL_OPTICAL',
                                      'IR_OUT', 'HDMI IN', 'COMPOSITE IN', 'VGA IN', 'COMPONENT IN', 'DVI IN',
                                      'STEREO IN', 'DIGITAL_OPTICAL IN', 'HDMI OUT', 'COMPOSITE OUT', 'VGA OUT',
                                      'COMPONENT OUT', 'DVI OUT', 'STEREO OUT', 'DIGITAL_OPTICAL OUT']

            # Labels
            self.panel_label = tk.Label(self.uc.root, text='Driver Selection', font=("Arial", 15))
            self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')

            self.blank_image_label = tk.Label(self.uc.root, image=self.uc.blank)
            self.blank_image_label.image = self.uc.blank
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
            self.blank_image_label.drop_target_register(DND_FILES)
            self.blank_image_label.dnd_bind('<<Drop>>', self.drop_in_c4z)

            self.icon_label = tk.Label(self.uc.root, text='0 of 0')
            self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

            self.icon_name_label = tk.Label(self.uc.root, text='icon name')
            self.icon_name_label.place(x=108 + self.x, y=193 + self.y, anchor='n')

            # Buttons
            self.open_file_button = tk.Button(self.uc.root, text='Open', width=10, command=self.upload_c4z, takefocus=0)
            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

            self.restore_button = tk.Button(self.uc.root, text='Restore\nOriginal Icon', command=self.restore_icon,
                                            takefocus=0)
            self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.restore_button['state'] = DISABLED

            self.restore_all_button = tk.Button(self.uc.root, text='Restore All', command=self.restore_all, takefocus=0)
            self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.restore_all_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.uc.root, text='Prev', command=self.prev_icon, width=5, takefocus=0)
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.uc.root, text='Next', command=self.next_icon, width=5, takefocus=0)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
            self.next_icon_button['state'] = DISABLED

            self.gen_driver_button = tk.Button(self.uc.root, text='Load Generic Driver', command=self.load_gen_driver,
                                               takefocus=0)
            self.gen_driver_button.place(x=228 + self.x, y=219 + self.y, anchor='n')

            self.multi_driver_button = tk.Button(self.uc.root, text='Load Multi Driver', command=self.load_gen_multi,
                                                 takefocus=0)
            self.multi_driver_button.place(x=5 + self.x, y=219 + self.y, anchor='nw')

            # Entry
            self.file_entry_field = tk.Entry(self.uc.root, width=25, takefocus=0)
            self.file_entry_field.insert(0, 'Select .c4z file...')
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field['state'] = DISABLED
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_c4z)

            # Checkbox
            self.show_extra_icons = IntVar(value=0)
            self.show_extra_icons.trace('w', self.toggle_extra_icons)
            self.show_sub_icons_check = Checkbutton(self.uc.root, text='show extra icons',
                                                    variable=self.show_extra_icons, takefocus=0)
            self.show_sub_icons_check.place(x=self.x + 177, y=self.y + 176, anchor='nw')

        def toggle_extra_icons(self, *args):
            if args:  # For IDE unused argument warning
                pass
            if not self.uc.driver_selected:
                return
            if self.show_extra_icons.get() == 0 and self.uc.c4z_panel.icons[self.uc.c4z_panel.current_icon].extra:
                self.next_icon()
            self.update_icon()

        def load_gen_driver(self):
            # Upload generic two-state driver from Base64Assets
            self.multi_driver_button['state'] = NORMAL
            temp_gen_driver = self.uc.temp_dir + 'generic.c4z'
            if self.file_entry_field.get() == temp_gen_driver:
                return
            with open(temp_gen_driver, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_driver))

            if os.path.isdir(self.uc.temp_dir + 'driver'):
                shutil.rmtree(self.uc.temp_dir + 'driver')

            shutil.unpack_archive(temp_gen_driver, self.uc.temp_dir + 'driver', 'zip')
            os.remove(temp_gen_driver)

            sizes = [(70, 70), (90, 90), (300, 300), (512, 512)]
            pictures = os.listdir(self.uc.device_icon_dir)
            for picture in pictures:
                resized_icon = Image.open(self.uc.device_icon_dir + '/' + picture)
                for size in sizes:
                    new_icon = resized_icon.resize(size)
                    new_icon.save(self.uc.device_icon_dir + '/' + picture.replace(str(1024), str(size[0])))

            shutil.make_archive(temp_gen_driver.replace('.c4z', ''), 'zip', self.uc.temp_dir + 'driver')
            os.rename(temp_gen_driver.replace('.c4z', '.zip'), temp_gen_driver)

            self.upload_c4z(temp_gen_driver)
            self.uc.export_panel.driver_name_entry.delete(0, 'end')
            self.uc.export_panel.driver_name_entry.insert(0, 'New Driver')
            os.remove(temp_gen_driver)
            self.gen_driver_button['state'] = DISABLED

        def load_gen_multi(self, show_loading_image=True):
            # Upload generic multi-state driver from Base64Assets
            if show_loading_image:
                # Show loading image while driver images are created
                with open(self.uc.temp_dir + 'loading_icon.gif', 'wb') as loading_img:
                    loading_img.write(base64.b64decode(loading_icon))
                icon_image = Image.open(self.uc.temp_dir + 'loading_icon.gif')
                icon = ImageTk.PhotoImage(icon_image)
                self.blank_image_label.configure(image=icon)
                self.blank_image_label.image = icon
                self.multi_driver_button['state'] = DISABLED
                self.uc.root.after(1, self.uc.show_loading_image)
                return

            self.gen_driver_button['state'] = NORMAL
            temp_gen_driver = self.uc.temp_dir + 'multi generic.c4z'
            if self.file_entry_field.get() == temp_gen_driver:
                return
            with open(temp_gen_driver, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_multi))

            if os.path.isdir(self.uc.temp_dir + 'driver'):
                shutil.rmtree(self.uc.temp_dir + 'driver')

            shutil.unpack_archive(temp_gen_driver, self.uc.temp_dir + 'driver', 'zip')
            os.remove(temp_gen_driver)

            sizes = [(90, 90), (300, 300), (512, 512), (1024, 1024)]
            pictures = os.listdir(self.uc.device_icon_dir)
            for picture in pictures:
                resized_icon = Image.open(self.uc.device_icon_dir + '/' + picture)
                for size in sizes:
                    new_icon = resized_icon.resize(size)
                    new_icon.save(self.uc.device_icon_dir + '/' + picture.replace(str(70), str(size[0])))

            shutil.make_archive(temp_gen_driver.replace('.c4z', ''), 'zip', self.uc.temp_dir + 'driver')
            os.rename(temp_gen_driver.replace('.c4z', '.zip'), temp_gen_driver)

            self.upload_c4z(temp_gen_driver)
            self.uc.export_panel.driver_name_entry.delete(0, 'end')
            self.uc.export_panel.driver_name_entry.insert(0, 'New Driver')
            os.remove(temp_gen_driver)
            os.remove(self.uc.temp_dir + 'loading_icon.gif')

            self.multi_driver_button['state'] = DISABLED

        def update_icon(self):
            if len(self.icons) == 0:
                return
            if abs(self.current_icon) >= len(self.icons):
                self.current_icon = abs(self.current_icon) % len(self.icons)
            icon_image = Image.open(self.icons[self.current_icon].path)
            icon = icon_image.resize((128, 128))
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label.configure(image=icon)
            self.blank_image_label.image = icon

            if self.show_extra_icons.get() == 0 and self.extra_icons != 0:
                self.icon_label.config(text='icon: ' + str(self.current_icon + 1) + ' of ' +
                                            str(len(self.icons) - self.extra_icons) +
                                            ' (' + str(len(self.icons)) + ')')
            else:
                self.icon_label.config(text='icon: ' + str(self.current_icon + 1) + ' of ' + str(len(self.icons)))
            self.icon_name_label.config(text='name: ' + self.icons[self.current_icon].name)

        def upload_c4z(self, given_path=None):
            def get_icons(directory):
                if not os.path.isdir(directory):
                    return
                icons_out = []
                sub_list = []
                path_list = os.listdir(directory)
                path_list.sort()
                for string in path_list:
                    if '.bak' in string or '.orig' in string or string[0] == '.':
                        continue
                    if '.' not in string:
                        if 'original_icons' in string or 'old' in string:
                            continue
                        sub_list.append(string)
                        continue
                    if 'device_lg' in string:
                        icon_objects.append(self.SubIcon(directory, directory + '/' + string, 'device', 32))
                        continue
                    elif 'device_sm' in string:
                        icon_objects.append(self.SubIcon(directory, directory + '/' + string, 'device', 16))
                        continue
                    temp_name = ''
                    temp_size = ''
                    read_size = False
                    read_name = False
                    for character in reversed(string):
                        if character == '.':
                            read_size = True
                            continue
                        if read_size:
                            try:
                                int(character)
                                temp_size = character + temp_size
                            except ValueError:
                                if temp_size == '' and character != '_':
                                    temp_name = character + temp_name
                                read_size = False
                                read_name = True
                            continue
                        if read_name:
                            temp_name = character + temp_name
                    if temp_size == '':
                        temp_img = PIL.Image.open(directory + '/' + string)
                        temp_size = str(temp_img.size[0])
                    icons_out.append(self.SubIcon(directory, directory + '/' + string, temp_name, int(temp_size)))

                if len(sub_list) == 0:
                    return icons_out
                sub_list.sort()
                for sub_dir in sub_list:
                    to_add = get_icons(directory + '/' + sub_dir)
                    for icon_path in to_add:
                        icons_out.append(icon_path)
                return icons_out

            if self.file_entry_field.get() == 'Invalid driver selected...':
                self.file_entry_field['state'] = NORMAL
                self.file_entry_field.delete(0, 'end')
                if self.uc.restore_entry_string != '':
                    self.file_entry_field.insert(0, self.uc.restore_entry_string)
                else:
                    self.file_entry_field.insert(0, 'Select .c4z file...')
                self.file_entry_field['state'] = 'readonly'
                self.uc.restore_entry_string = ''
                self.uc.time_var = 0
                self.uc.schedule_entry_restore = False

            # Backup existing driver data
            temp_bak = '/bak' + str(random.randint(11111111, 99999999)) + '/'
            icons_bak = None
            if len(self.icons) != 0:
                icons_bak = self.icons
                if os.path.isdir(self.uc.temp_dir + 'driver'):
                    shutil.copytree(self.uc.temp_dir + 'driver', self.uc.temp_dir + temp_bak)

            # File select dialog
            if given_path is None:
                filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])
                # If no file selected
                if not filename:
                    if os.path.isdir(self.uc.temp_dir + temp_bak):
                        shutil.rmtree(self.uc.temp_dir + temp_bak)
                    return
            else:
                filename = given_path

            # Delete existing driver
            self.uc.driver_selected = False
            if os.path.isdir(self.uc.temp_dir + 'driver/'):
                shutil.rmtree(self.uc.temp_dir + 'driver/')

            # Unpack selected driver
            shutil.unpack_archive(filename, self.uc.temp_dir + 'driver', 'zip')

            # Get all individual icons from driver
            icon_objects = []
            try:
                for icon in get_icons(self.uc.icon_dir):
                    icon_objects.append(icon)
            except TypeError:
                pass

            # Form icon groups; I should probably rewrite this
            self.icons = []
            temp_list = []
            for icon in icon_objects:
                if not temp_list or (icon.name == temp_list[0].name and icon.root == temp_list[0].root):
                    temp_list.append(icon)
                    continue
                else:
                    if 'device' not in temp_list[0].path and 'device' not in temp_list[0].root and \
                            'device' not in temp_list[0].name:
                        self.icons.append(self.Icon(temp_list, extra=True))
                    else:
                        self.icons.append(self.Icon(temp_list))
                    temp_list = [icon]
            if len(temp_list) != 0:
                if 'device' not in temp_list[0].path and 'device' not in temp_list[0].root and \
                        'device' not in temp_list[0].name:
                    self.icons.append(self.Icon(temp_list, extra=True))
                else:
                    self.icons.append(self.Icon(temp_list))

            # Count extra icons & Fix Icon order (sloppy)
            temp_list = []
            device_exception = None
            self.extra_icons = 0
            for icon in reversed(self.icons):
                if icon.extra:
                    self.extra_icons += 1
                    continue
                if icon.name == 'device':
                    device_exception = icon
                    self.icons.pop(self.icons.index(icon))
                    continue
                temp_list.append(icon)
                self.icons.pop(self.icons.index(icon))
            temp_name_list = []
            temp_name_dict = {}
            for icon in temp_list:
                temp_name_list.append(icon.name)
                temp_name_dict[icon.name] = temp_list.index(icon)
            temp_name_list.sort(key=natural_key)
            for icon_name in reversed(temp_name_list):
                self.icons.insert(0, temp_list[temp_name_dict[icon_name]])
            if device_exception:
                self.icons.insert(0, device_exception)

            # Update entry fields and restore driver if necessary
            if len(self.icons) == 0:
                self.file_entry_field['state'] = NORMAL
                if self.file_entry_field.get() != 'Select .c4z file...' and \
                        self.file_entry_field.get() != 'Invalid driver selected...':
                    # Restore existing driver data if invalid driver selected
                    self.icons = icons_bak
                    if os.path.isdir(self.uc.temp_dir + temp_bak):
                        if os.path.isdir(self.uc.temp_dir + 'driver/'):
                            shutil.rmtree(self.uc.temp_dir + 'driver/')
                        shutil.copytree(self.uc.temp_dir + temp_bak, self.uc.temp_dir + 'driver/')
                        shutil.rmtree(self.uc.temp_dir + temp_bak)
                    self.uc.schedule_entry_restore = True
                    self.uc.restore_entry_string = self.file_entry_field.get()
                    self.uc.driver_selected = True
                self.file_entry_field.delete(0, 'end')
                self.file_entry_field.insert(0, 'Invalid driver selected...')
                self.file_entry_field['state'] = DISABLED
                return
            # Update entry with driver file path
            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, filename)
            self.file_entry_field['state'] = 'readonly'
            orig_file_path = filename
            orig_driver_name = ''
            for i in reversed(range(len(orig_file_path) - 1)):
                if orig_file_path[i] == '/':
                    self.uc.orig_file_dir = orig_file_path[0:i + 1]
                    break
                if orig_driver_name != '':
                    orig_driver_name = orig_file_path[i] + orig_driver_name
                    continue
                if orig_file_path[i + 1] == '.':
                    orig_driver_name = orig_file_path[i]
            if orig_driver_name != 'generic' and orig_driver_name != 'multi generic':
                self.uc.export_panel.driver_name_entry.delete(0, 'end')
                self.uc.export_panel.driver_name_entry.insert(0, orig_driver_name)
            self.uc.driver_selected = True
            self.current_icon = 0
            self.update_icon()

            # Read driver.xml and update used id tags
            self.uc.driver_xml = XMLObject(self.uc.temp_dir + 'driver/driver.xml')
            id_tags = self.uc.driver_xml.get_tag('id')
            if id_tags is not None:
                self.uc.connections_panel.ids = []
                for id_tag in id_tags:
                    try:
                        if int(id_tag.value) not in self.uc.connections_panel.ids:
                            self.uc.connections_panel.ids.append(int(id_tag.value))
                    except ValueError:
                        pass

            # Check lua file for multi-state
            multi_state = False
            if os.path.isfile(self.uc.temp_dir + 'driver/driver.lua'):
                with open(self.uc.temp_dir + 'driver/driver.lua', errors='ignore') as driver_lua_file:
                    driver_lua_lines = driver_lua_file.readlines()
                for line in driver_lua_lines:
                    if '_OPTIONS = { {' in line:
                        self.uc.get_states(driver_lua_lines)
                        multi_state = True
                        break
            if not multi_state:
                self.uc.disable_states()

            # Update button statuses
            if not self.file_entry_field.get().endswith('generic.c4z') and not\
                    self.file_entry_field.get() == 'Invalid driver selected...':
                # Update generic driver buttons
                self.gen_driver_button['state'] = NORMAL
                self.multi_driver_button['state'] = NORMAL
            # Update driver prev/next buttons
            if len(self.icons) <= 1:
                self.prev_icon_button['state'] = DISABLED
                self.next_icon_button['state'] = DISABLED
            else:
                self.prev_icon_button['state'] = ACTIVE
                self.next_icon_button['state'] = ACTIVE
            # Update replacement prev/next buttons
            if self.uc.replacement_selected and self.uc.driver_selected:
                self.uc.replacement_panel.replace_button['state'] = ACTIVE
                self.uc.replacement_panel.replace_all_button['state'] = ACTIVE
            else:
                self.uc.replacement_panel.replace_button['state'] = DISABLED
                self.uc.replacement_panel.replace_all_button['state'] = DISABLED
            # Update Export button(s)
            if self.uc.driver_selected:
                self.uc.export_panel.export_button['state'] = ACTIVE
                self.uc.export_panel.export_as_button['state'] = ACTIVE
            # Update 'Restore All' button in driver panel
            done = False
            self.restore_all_button['state'] = DISABLED
            for path in list_all_sub_directories(self.uc.temp_dir + 'driver/'):
                files = os.listdir(path)
                for file in files:
                    if ('.bak' in file or '.orig' in file) and '.xml' not in file:
                        self.restore_all_button['state'] = ACTIVE
                        done = True
                        break
                if done:
                    break
            # Update restore current icon button in driver panel
            if os.path.isfile(self.icons[self.current_icon].path + '.bak') or \
                    os.path.isfile(self.icons[self.current_icon].path + '.orig'):
                self.restore_button['state'] = ACTIVE
            else:
                self.restore_button['state'] = DISABLED

            # Remove temp backup directory
            if os.path.isdir(self.uc.temp_dir + temp_bak):
                shutil.rmtree(self.uc.temp_dir + temp_bak)

            # Update connections panel
            self.get_connections()

        def restore_icon(self, index=None):
            if index is None:
                index = self.current_icon
            elif 0 > index > len(self.icons):
                return

            for icon in self.icons[index].icons:
                if os.path.isfile(icon.path + '.bak'):
                    shutil.copy(icon.path + '.bak', icon.path)
                    os.remove(icon.path + '.bak')
                elif os.path.isfile(icon.path + '.orig'):
                    shutil.copy(icon.path + '.orig', icon.path)
                    os.remove(icon.path + '.orig')
            self.restore_button['state'] = DISABLED
            disable_all_button = True
            for group in self.icons:
                if os.path.isfile(group.icons[0].path + '.bak') or os.path.isfile(group.icons[0].path + '.orig'):
                    disable_all_button = False
                    break
            if disable_all_button:
                self.restore_all_button['state'] = DISABLED
            self.update_icon()

        def restore_all(self):
            for i in range(len(self.icons)):
                self.restore_icon(index=i)
            self.restore_button['state'] = DISABLED
            self.restore_all_button['state'] = DISABLED
            self.update_icon()

        def prev_icon(self):
            if not self.uc.driver_selected:
                return
            if self.current_icon - 1 < 0:
                self.current_icon = self.current_icon - 1 + len(self.icons)
            else:
                self.current_icon -= 1

            if os.path.isfile(self.icons[self.current_icon].path + '.bak') or \
                    os.path.isfile(self.icons[self.current_icon].path + '.orig'):
                self.restore_button['state'] = ACTIVE
            else:
                self.restore_button['state'] = DISABLED

            if self.show_extra_icons.get() == 0 and self.icons[self.current_icon].extra:
                while self.icons[self.current_icon].extra:
                    if self.current_icon - 1 < 0:
                        self.current_icon = self.current_icon - 1 + len(self.icons)
                    else:
                        self.current_icon -= 1

            self.update_icon()

        def next_icon(self):
            if not self.uc.driver_selected:
                return
            if self.current_icon + 1 >= len(self.icons):
                self.current_icon = self.current_icon + 1 - len(self.icons)
            else:
                self.current_icon += 1

            if os.path.isfile(self.icons[self.current_icon].path + '.bak') or \
                    os.path.isfile(self.icons[self.current_icon].path + '.orig'):
                self.restore_button['state'] = ACTIVE
            else:
                self.restore_button['state'] = DISABLED

            if self.show_extra_icons.get() == 0 and self.icons[self.current_icon].extra:
                while self.icons[self.current_icon].extra:
                    if self.current_icon + 1 >= len(self.icons):
                        self.current_icon = self.current_icon + 1 - len(self.icons)
                    else:
                        self.current_icon += 1

            self.update_icon()

        def get_connections(self):
            if not os.path.isfile(self.uc.temp_dir + 'driver/driver.xml') or not self.uc.driver_selected:
                return
            self.uc.connections_panel.reinit()

            # Get connections from xml object
            connections = []
            classname_tags = self.uc.driver_xml.get_tag('classname')
            pop_list = []
            if classname_tags is not None:
                for classname_tag in classname_tags:
                    if classname_tag.value not in self.valid_connections:
                        pop_list.append(classname_tags.index(classname_tag))
                pop_list.sort(reverse=True)
                for index in pop_list:
                    classname_tags.pop(index)
                for classname_tag in classname_tags:
                    class_tag = None
                    connection_tag = None
                    connectionname_tag = None
                    id_tag = None
                    type_tag = None
                    for parent in classname_tag.parents:
                        if parent.name == 'class':
                            class_tag = parent
                        if parent.name == 'connection':
                            connection_tag = parent
                            for child in parent.children:
                                if child.name == 'type':
                                    type_tag = child
                                if child.name == 'id':
                                    id_tag = child
                                if child.name == 'connectionname':
                                    connectionname_tag = child
                    if id_tag is None or connection_tag is None or class_tag is None or connectionname_tag is None \
                            or type_tag is None:
                        continue
                    connections.append([connectionname_tag.value, classname_tag.value, id_tag.value,
                                        connection_tag, class_tag, connectionname_tag, id_tag, type_tag, classname_tag])

            # Check that number of connections does not exceed maximum
            if len(connections) > len(self.uc.connections_panel.connections):
                conn_range = len(self.uc.connections_panel.connections) - 1
            else:
                conn_range = len(connections)

            # Assign panel connections to xml tags and update UI
            id_groups = []
            for i in range(conn_range):
                not_in_group = True
                for group in id_groups:
                    if group[0] is connections[i][3]:
                        group.append(self.uc.connections_panel.connections[i])
                        not_in_group = False
                if not_in_group:
                    id_groups.append([connections[i][3], self.uc.connections_panel.connections[i]])
                x = self.uc.connections_panel.connections[i].x
                y = self.uc.connections_panel.connections[i].y
                self.uc.connections_panel.connections[i].add_button.place(x=-420, y=-420)
                self.uc.connections_panel.connections[i].del_button.place(x=x, y=y)
                self.uc.connections_panel.connections[i].name_entry['state'] = NORMAL
                self.uc.connections_panel.connections[i].name_entry.delete(0, END)
                self.uc.connections_panel.connections[i].name_entry.insert(0, connections[i][0])
                self.uc.connections_panel.connections[i].name_entry['state'] = DISABLED
                self.uc.connections_panel.connections[i].type_menu['state'] = DISABLED
                self.uc.connections_panel.connections[i].type.set(connections[i][1])
                self.uc.connections_panel.connections[i].id = connections[i][2]
                self.uc.connections_panel.connections[i].tags = [connections[i][3], connections[i][4],
                                                                 connections[i][5], connections[i][6],
                                                                 connections[i][7], connections[i][8]]
                self.uc.connections_panel.connections[i].original = True

            # Fill in remaining empty connections
            for conn in self.uc.connections_panel.connections:
                conn.add_button['state'] = NORMAL
                if conn.original:
                    continue
                new_conn = XMLObject(xml_data=conn_template)
                name_tag = new_conn.get_tag('connectionname')[0]
                class_tag = new_conn.get_tag('class')[0]
                classname_tag = new_conn.get_tag('classname')[0]
                id_tag = new_conn.get_tag('id')[0]
                type_tag = new_conn.get_tag('type')[0]
                name_tag.value = 'Connection Name...'
                new_conn.get_tag('classname')[0].value = 'HDMI IN'
                new_conn.delete = True
                self.uc.driver_xml.get_tag('connections')[0].children.append(new_conn)
                conn.tags = [new_conn, class_tag, name_tag, id_tag, type_tag, classname_tag]

            # Form id groups
            for group in id_groups:
                first = True
                for conn in group:
                    if first:
                        first = False
                        continue
                    new_group = []
                    for conn0 in group:
                        if conn0 != conn:
                            new_group.append(conn0)
                    conn.id_group = new_group
            for conn in self.uc.connections_panel.connections:
                conn.update_id()

        def drop_in_c4z(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            if dropped_path.endswith('.c4z'):
                self.upload_c4z(given_path=dropped_path)
            elif dropped_path.endswith('.png') or dropped_path.endswith('.jpg') or \
                    dropped_path.endswith('.gif') or dropped_path.endswith('.jpeg'):
                self.uc.replacement_panel.upload_replacement(given_path=dropped_path)
            elif '.' not in dropped_path:
                image_paths = os.listdir(dropped_path)
                for new_img_path in image_paths:
                    self.uc.replacement_panel.upload_replacement(dropped_path + '/' + new_img_path)

    class ReplacementPanel:
        def __init__(self, upper_class):
            # Initialize Replacement Panel
            self.x = 303
            self.y = 20
            self.uc = upper_class
            self.img_stack = []
            self.stack_labels = []

            # Labels
            self.panel_label = tk.Label(self.uc.root, text='Replacement Icons', font=("Arial", 15))
            self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')

            self.blank_image_label = tk.Label(self.uc.root, image=self.uc.blank)
            self.blank_image_label.image = self.uc.blank
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
            self.blank_image_label.drop_target_register(DND_FILES)
            self.blank_image_label.dnd_bind('<<Drop>>', self.drop_in_replacement)

            self.stack_labels.append(tk.Label(self.uc.root, image=self.uc.stack_blank))
            self.stack_labels[-1].image = self.uc.stack_blank
            self.stack_labels[-1].place(x=31 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].bind('<Button-1>', self.select_stack0)
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack0)

            self.stack_labels.append(tk.Label(self.uc.root, image=self.uc.stack_blank))
            self.stack_labels[-1].image = self.uc.stack_blank
            self.stack_labels[-1].place(x=92 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].bind('<Button-1>', self.select_stack1)
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack1)

            self.stack_labels.append(tk.Label(self.uc.root, image=self.uc.stack_blank))
            self.stack_labels[-1].image = self.uc.stack_blank
            self.stack_labels[-1].place(x=153 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].bind('<Button-1>', self.select_stack2)
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack2)

            self.stack_labels.append(tk.Label(self.uc.root, image=self.uc.stack_blank))
            self.stack_labels[-1].image = self.uc.stack_blank
            self.stack_labels[-1].place(x=214 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].bind('<Button-1>', self.select_stack3)
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack3)

            # Buttons
            self.open_file_button = tk.Button(self.uc.root, text='Open', width=10, command=self.upload_replacement,
                                              takefocus=0)
            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

            self.replace_all_button = tk.Button(self.uc.root, text='Replace All', command=self.replace_all, takefocus=0)
            self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.replace_all_button['state'] = DISABLED

            self.replace_button = tk.Button(self.uc.root, text='Replace\nCurrent Icon', command=self.replace_icon,
                                            takefocus=0)
            self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.replace_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.uc.root, text='Prev', command=self.dec_img_stack, width=5,
                                              takefocus=0)
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.uc.root, text='Next', command=self.inc_img_stack, width=5,
                                              takefocus=0)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
            self.next_icon_button['state'] = DISABLED

            # Entry
            self.file_entry_field = tk.Entry(self.uc.root, width=25, takefocus=0)
            self.file_entry_field.insert(0, 'Select image file...')
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field['state'] = DISABLED
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_replacement)

        def upload_replacement(self, given_path=''):
            if given_path == '':
                filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"),
                                                                 ("Image", "*.gif"), ("Image", "*.jpeg")])
            else:
                filename = given_path

            if not filename:
                return
            if not filename.endswith('.png') and not filename.endswith('.jpg') and not filename.endswith('.gif') and \
                    not filename.endswith('.jpeg'):
                return

            if self.uc.replacement_selected:
                self.add_to_img_stack(self.uc.temp_dir + 'replacement_icon.png')
            shutil.copy(filename, self.uc.temp_dir + 'replacement_icon.png')

            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, filename)
            self.file_entry_field['state'] = 'readonly'

            if self.uc.driver_selected:
                self.replace_button['state'] = ACTIVE
                self.replace_all_button['state'] = ACTIVE
            else:
                self.replace_button['state'] = DISABLED
                self.replace_all_button['state'] = DISABLED

            if not os.path.isfile(self.uc.temp_dir + 'replacement_icon.png'):
                return
            self.uc.replacement_selected = True
            icon_image = Image.open(self.uc.replacement_image_path)
            icon = icon_image.resize((128, 128))
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label.configure(image=icon)
            self.blank_image_label.image = icon

        def add_to_img_stack(self, img_path: str, index=None):
            if not os.path.isfile(img_path):
                return
            if not img_path.endswith('.png') and not img_path.endswith('.jpg') and not img_path.endswith('.gif') and \
                    not img_path.endswith('.jpeg'):
                return
            for img in self.img_stack:
                if filecmp.cmp(img, img_path):
                    return

            if len(self.img_stack) >= 4:
                self.prev_icon_button['state'] = NORMAL
                self.next_icon_button['state'] = NORMAL

            new_img_path = self.uc.temp_dir + 'stack' + str(len(self.img_stack)) + '.png'
            if 'replacement_icon.png' in img_path:
                os.rename(img_path, new_img_path)
            else:
                shutil.copy(img_path, new_img_path)
            if index is None:
                self.img_stack.insert(0, new_img_path)
                self.refresh_img_stack()
                return
            if not -len(self.img_stack) < index < len(self.img_stack):
                self.img_stack.append(new_img_path)
                self.refresh_img_stack()
                return
            temp = self.img_stack[index]
            self.img_stack.pop(index)
            self.img_stack.insert(index, new_img_path)
            self.img_stack.append(temp)
            self.refresh_img_stack()

        def refresh_img_stack(self):
            if len(self.img_stack) == 0:
                return
            for i in range(len(self.img_stack)):
                if i == 4:
                    break
                icon_image = Image.open(self.img_stack[i])
                icon = icon_image.resize((60, 60))
                icon = ImageTk.PhotoImage(icon)
                self.stack_labels[i].configure(image=icon)
                self.stack_labels[i].image = icon

        def dec_img_stack(self):
            if len(self.img_stack) <= 4:
                return
            temp = self.img_stack[0]
            self.img_stack.pop(0)
            self.img_stack.append(temp)
            self.refresh_img_stack()

        def inc_img_stack(self):
            if len(self.img_stack) <= 4:
                return
            temp = self.img_stack[-1]
            self.img_stack.pop(-1)
            self.img_stack.insert(0, temp)
            self.refresh_img_stack()

        def replace_icon(self, index=None, given_path=''):
            if index is None:
                index = self.uc.c4z_panel.current_icon
            elif 0 > index > len(self.uc.c4z_panel.icons):
                return

            if given_path == '':
                replacement_icon = Image.open(self.uc.replacement_image_path)
            else:
                replacement_icon = Image.open(given_path)
            for icon in self.uc.c4z_panel.icons[index].icons:
                if not os.path.isfile(icon.path + '.bak'):
                    shutil.copy(icon.path, icon.path + '.bak')
                new_icon = replacement_icon.resize((icon.size, icon.size))
                new_icon.save(icon.path)
            self.uc.c4z_panel.restore_button['state'] = ACTIVE
            self.uc.c4z_panel.restore_all_button['state'] = ACTIVE
            self.uc.c4z_panel.update_icon()

        def replace_all(self):
            for i in range(len(self.uc.c4z_panel.icons)):
                if self.uc.c4z_panel.show_extra_icons.get() == 0 and self.uc.c4z_panel.icons[i].extra:
                    continue
                self.replace_icon(index=i)

        def drop_in_replacement(self, event):
            img_path = event.data.replace('{', '').replace('}', '')
            if '.' not in img_path:
                image_paths = os.listdir(img_path)
                for new_img_path in image_paths:
                    self.upload_replacement(img_path + '/' + new_img_path)
                return
            if not img_path.endswith('.png') and not img_path.endswith('.jpg') and not img_path.endswith('.gif') and \
                    not img_path.endswith('.jpeg'):
                return
            self.upload_replacement(given_path=img_path)

        def select_stack0(self, event):
            if len(self.img_stack) == 0:
                return event
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.uc.temp_dir + 'replacement_icon.png'):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.uc.temp_dir + 'replacement_icon.png', index=0)
                self.upload_replacement(given_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(given_path=self.img_stack[0])
                temp = self.img_stack[0]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(0)
                self.img_stack.insert(0, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(given_path=self.img_stack[0])

        def select_stack1(self, event):
            if len(self.img_stack) <= 1:
                return event
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.uc.temp_dir + 'replacement_icon.png'):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.uc.temp_dir + 'replacement_icon.png', index=1)
                self.upload_replacement(given_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(given_path=self.img_stack[1])
                temp = self.img_stack[1]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(1)
                self.img_stack.insert(1, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(given_path=self.img_stack[1])

        def select_stack2(self, event):
            if len(self.img_stack) <= 2:
                return event
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.uc.temp_dir + 'replacement_icon.png'):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.uc.temp_dir + 'replacement_icon.png', index=2)
                self.upload_replacement(given_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(given_path=self.img_stack[2])
                temp = self.img_stack[2]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(2)
                self.img_stack.insert(2, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(given_path=self.img_stack[2])

        def select_stack3(self, event):
            if len(self.img_stack) <= 3:
                return event
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.uc.temp_dir + 'replacement_icon.png'):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.uc.temp_dir + 'replacement_icon.png', index=3)
                self.upload_replacement(given_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(given_path=self.img_stack[3])
                temp = self.img_stack[3]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(3)
                self.img_stack.insert(3, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(given_path=self.img_stack[3])

        def drop_stack0(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_stack(dropped_path, index=0)

        def drop_stack1(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_stack(dropped_path, index=1)

        def drop_stack2(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_stack(dropped_path, index=2)

        def drop_stack3(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_stack(dropped_path, index=3)

    class ExportPanel:
        def __init__(self, upper_class):
            # Initialize Export Panel
            self.x = 615
            self.y = -50
            self.uc = upper_class
            self.abort = False

            # Labels
            self.panel_label = tk.Label(self.uc.root, text='Export', font=("Arial", 15))
            self.panel_label.place(x=150 + self.x, y=50 + self.y, anchor='n')

            self.driver_name_label = tk.Label(self.uc.root, text='Driver Name:')
            self.driver_name_label.place(x=65 + self.x, y=165 + self.y, anchor='w')

            # Buttons
            self.export_button = tk.Button(self.uc.root, text='Quick Export', width=20,
                                           command=self.quick_export, takefocus=0)
            self.export_button.place(x=145 + self.x, y=210 + self.y, anchor='n')
            self.export_button['state'] = DISABLED

            self.export_as_button = tk.Button(self.uc.root, text='Export As...', width=20,
                                              command=self.do_export, takefocus=0)
            self.export_as_button.place(x=145 + self.x, y=240 + self.y, anchor='n')
            self.export_as_button['state'] = DISABLED

            # Entry
            self.driver_name_var = StringVar()
            self.driver_name_var.set('New Driver')
            self.driver_name_var.trace('w', self.validate_driver_name)
            self.driver_name_entry = tk.Entry(self.uc.root, width=25, textvariable=self.driver_name_var)
            self.driver_name_entry.place(x=145 + self.x, y=175 + self.y, anchor='n')

            # Checkboxes
            self.inc_driver_version = IntVar(value=1)
            self.inc_driver_check = Checkbutton(self.uc.root, text='update driver version',
                                                variable=self.inc_driver_version, takefocus=0)
            self.inc_driver_check.place(x=63 + self.x, y=135 + self.y, anchor='w')

            self.include_backups = IntVar(value=1)
            self.include_backups_check = Checkbutton(self.uc.root, text='include backup files',
                                                     variable=self.include_backups, takefocus=0)
            self.include_backups_check.place(x=63 + self.x, y=115 + self.y, anchor='w')

        def quick_export(self, first_call=True, driver_name=''):
            if first_call:
                self.do_export(quick_export=True)
                return

            def confirm_overwrite():
                # Remove old driver
                if os.path.isfile(self.uc.cur_dir + driver_name + '.c4z'):
                    os.remove(self.uc.cur_dir + driver_name + '.c4z')
                self.export_file(driver_name)
                export_cleanup()

            def export_cleanup():
                # Restore original xml and lua file
                self.uc.driver_xml.restore()
                if os.path.isfile(self.uc.temp_dir + 'driver/driver.lua'):
                    os.remove(self.uc.temp_dir + 'driver/driver.lua')
                    os.rename(self.uc.temp_dir + 'driver/driver.lua.bak', self.uc.temp_dir + 'driver/driver.lua')
                os.remove(self.uc.temp_dir + 'driver/driver.xml')
                os.rename(self.uc.temp_dir + 'driver/driver.xml.bak', self.uc.temp_dir + 'driver/driver.xml')

                overwrite_pop_up.destroy()

            # Overwrite file popup
            if os.path.isfile(self.uc.cur_dir + driver_name + '.c4z'):
                win_x = self.uc.root.winfo_rootx() + self.x
                win_y = self.uc.root.winfo_rooty()
                overwrite_pop_up = Toplevel(self.uc.root)
                overwrite_pop_up.title('Overwrite')
                overwrite_pop_up.geometry('239x70')
                overwrite_pop_up.geometry(f'+{win_x}+{win_y}')
                overwrite_pop_up.protocol("WM_DELETE_WINDOW", export_cleanup)
                overwrite_pop_up.grab_set()
                overwrite_pop_up.focus()
                overwrite_pop_up.transient(self.uc.root)
                overwrite_pop_up.resizable(False, False)

                confirm_label = Label(overwrite_pop_up, text='Would you like to overwrite the existing file?')
                confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

                no_button = tk.Button(overwrite_pop_up, text='No', width='10', command=export_cleanup)
                no_button.grid(row=2, column=0, sticky='e', padx=5)

                yes_button = tk.Button(overwrite_pop_up, text='Yes', width='10', command=confirm_overwrite)
                yes_button.grid(row=2, column=1, sticky='w', padx=5)
                self.abort = True
                return
            self.export_file(driver_name)

        def do_export(self, quick_export=False):
            # Format driver name
            driver_name = self.driver_name_var.get()
            temp = ''
            for letter in driver_name:
                if str(letter).isalnum() or str(letter) == '_' or str(letter) == '-' or str(letter) == ' ':
                    temp += str(letter)
            driver_name = temp
            self.driver_name_entry.delete(0, 'end')
            self.driver_name_entry.insert(0, driver_name)
            if driver_name == '':
                self.driver_name_entry['background'] = 'pink'
                self.uc.counter = 7
                self.uc.root.after(150, self.uc.blink_driver_name_entry)
                return

            # Check State Validity
            invalid_states = False
            single_invalid_state = False
            for state in self.uc.state_panel.states:
                if state.name_entry['state'] == DISABLED:
                    continue
                if state.name_entry['background'] == 'pink' or state.name_entry['background'] == 'cyan':
                    self.abort = True
                    invalid_states = True
                    if not single_invalid_state:
                        single_invalid_state = True
                        continue
                    single_invalid_state = False
                    break
            if invalid_states:
                win_x = self.uc.root.winfo_rootx() + self.x
                win_y = self.uc.root.winfo_rooty()
                invalid_states_pop_up = Toplevel(self.uc.root)
                if single_invalid_state:
                    invalid_states_pop_up.title('Invalid State Found')
                    label_text = 'Cannot Export: Invalid state label'
                else:
                    invalid_states_pop_up.title('Invalid States Found')
                    label_text = 'Cannot Export: Invalid state labels'
                invalid_states_pop_up.geometry('239x70')
                invalid_states_pop_up.geometry(f'+{win_x}+{win_y}')
                invalid_states_pop_up.grab_set()
                invalid_states_pop_up.focus()
                invalid_states_pop_up.transient(self.uc.root)
                invalid_states_pop_up.resizable(False, False)
                confirm_label = Label(invalid_states_pop_up, text=label_text, justify='center')
                confirm_label.pack()
                exit_button = tk.Button(invalid_states_pop_up, text='Cancel', width='10',
                                        command=invalid_states_pop_up.destroy, justify='center')
                exit_button.pack(pady=10)
            if self.abort:
                self.abort = False
                return

            # Update state names in lua file
            # state_name_changes = [original_name, new_name, original_name_lower, new_name_lower]
            state_name_changes = []
            if os.path.isfile(self.uc.temp_dir + 'driver/driver.lua'):
                shutil.copy(self.uc.temp_dir + 'driver/driver.lua', self.uc.temp_dir + 'driver/driver.lua.bak')
                for state in self.uc.state_panel.states:
                    if state.name_entry['state'] == NORMAL:
                        state_name_changes.append([state.original_name, state.name_entry.get()])
                for name_change in state_name_changes:
                    formatted_name = ''
                    for character in name_change[1]:
                        if character == ' ' or (character not in letters and character not in capital_letters and
                                                character not in numbers):
                            continue
                        if formatted_name == '' and character in letters:
                            formatted_name += capital_letters[letters.index(character)]
                            continue
                        formatted_name += character
                    if formatted_name == '':
                        formatted_name = name_change[0]
                    name_change[1] = formatted_name
                pop_list = []
                for name_change in state_name_changes:
                    if name_change[0] == name_change[1]:
                        pop_list.insert(0, state_name_changes.index(name_change))
                        continue
                    name_change.append(name_change[0].replace(name_change[0][0],
                                                              letters[capital_letters.index(name_change[0][0])]))
                    name_change.append(name_change[1].replace(name_change[1][0],
                                                              letters[capital_letters.index(name_change[1][0])]))
                for index in pop_list:
                    state_name_changes.pop(index)

                # Modify lua file
                modified_lua_lines = []
                shutil.copy(self.uc.temp_dir + 'driver/driver.lua', self.uc.temp_dir + 'driver/driver.lua.bak')
                with open(self.uc.temp_dir + 'driver/driver.lua', errors='ignore') as driver_lua_file:
                    driver_lua_lines = driver_lua_file.readlines()
                for line in driver_lua_lines:
                    new_line = line
                    for name_change in state_name_changes:
                        if name_change[0] + ' ' in line or name_change[2] + ' ' in line:
                            new_line = new_line.replace(name_change[0] + ' ', name_change[1] + ' ')
                            new_line = new_line.replace(name_change[2] + ' ', name_change[3] + ' ')
                        elif name_change[0] + "'" in line or name_change[2] + "'" in line:
                            new_line = new_line.replace(name_change[0] + "'", name_change[1] + "'")
                            new_line = new_line.replace(name_change[2] + "'", name_change[3] + "'")
                        elif name_change[0] + '"' in line or name_change[2] + '"' in line:
                            new_line = new_line.replace(name_change[0] + '"', name_change[1] + '"')
                            new_line = new_line.replace(name_change[2] + '"', name_change[3] + '"')
                        elif name_change[0] + '=' in line or name_change[2] + '=' in line:
                            new_line = new_line.replace(name_change[0] + '=', name_change[1] + '=')
                            new_line = new_line.replace(name_change[2] + '=', name_change[3] + '=')
                    modified_lua_lines.append(new_line)
                with open(self.uc.temp_dir + 'driver/driver.lua', 'w', errors='ignore') as driver_lua_file:
                    driver_lua_file.writelines(modified_lua_lines)

            # Confirm all connections have non-conflicting ids
            for conn in self.uc.connections_panel.connections:
                conn.update_id(refresh=True)

            # Increment driver version on each export
            if self.uc.driver_version == -1:
                self.uc.driver_version = int(self.uc.driver_xml.get_tag('version')[0].value)
            self.uc.driver_version += 1
            self.uc.driver_xml.get_tag('version')[0].value = str(self.uc.driver_version)
            self.uc.driver_xml.set_restore_point()

            # Update connection names
            for conn in self.uc.connections_panel.connections:
                conn.tags[2].value = conn.name_entry.get()
                conn.tags[5].value = conn.type.get()

            # Do multi-state related changes in xml
            if state_name_changes:
                for item_tag in self.uc.driver_xml.get_tag('item'):
                    for state_name_change in state_name_changes:
                        if state_name_change[0] == item_tag.value:
                            item_tag.value = state_name_change[1]
                            break
                        if state_name_change[2] == item_tag.value:
                            item_tag.value = state_name_change[3]
                            break
                for name_tag in self.uc.driver_xml.get_tag('name'):
                    for state_name_change in state_name_changes:
                        if state_name_change[0] == name_tag.value or name_tag.value.endswith(state_name_change[0]):
                            name_tag.value = name_tag.value.replace(state_name_change[0], state_name_change[1])
                            break
                        if state_name_change[2] == name_tag.value or name_tag.value.endswith(state_name_change[2]):
                            name_tag.value = name_tag.value.replace(state_name_change[2], state_name_change[3])
                            break
                for description_tag in self.uc.driver_xml.get_tag('description'):
                    for state_name_change in state_name_changes:
                        if state_name_change[0] + ' ' in description_tag.value:
                            description_tag.value = description_tag.value.replace(state_name_change[0],
                                                                                  state_name_change[1])
                            break
                        if state_name_change[2] + ' ' in description_tag.value:
                            description_tag.value = description_tag.value.replace(state_name_change[2],
                                                                                  state_name_change[3])
                            break
                for state_tag in self.uc.driver_xml.get_tag('state'):
                    for param in state_tag.parameters:
                        if param[0] == 'id':
                            for state_name_change in state_name_changes:
                                if state_name_change[0] == param[1]:
                                    param[1] = state_name_change[1]
                                    break
                                if state_name_change[2] == param[1]:
                                    param[1] = state_name_change[3]
                                    break

            # Update xml with new driver name
            self.uc.driver_xml.get_tag('name')[0].value = driver_name
            modified_datestamp = str(datetime.now().strftime("%m/%d/%Y %H:%M"))
            self.uc.driver_xml.get_tag('modified')[0].value = modified_datestamp
            self.uc.driver_xml.get_tag('creator')[0].value = 'C4IconSwapper'
            self.uc.driver_xml.get_tag('manufacturer')[0].value = 'C4IconSwapper'
            for param in self.uc.driver_xml.get_tag('proxy')[0].parameters:
                if param[0] == 'name':
                    param[1] = driver_name
            for icon_tag in self.uc.driver_xml.get_tag('Icon'):
                result = re.search('driver/(.*)/icons', icon_tag.value)
                if result:
                    result = result.group(1)
                    icon_tag.value = icon_tag.value.replace(result, driver_name)

            # Backup xml file and write new xml
            os.rename(self.uc.temp_dir + 'driver/driver.xml', self.uc.temp_dir + 'driver/driver.xml.bak')
            with open(self.uc.temp_dir + 'driver/driver.xml', 'w', errors='ignore') as out_file:
                out_file.writelines(self.uc.driver_xml.get_lines())

            # Backup lua file if needed
            if os.path.isfile(self.uc.temp_dir + 'driver/driver.lua'):
                shutil.copy(self.uc.temp_dir + 'driver/driver.lua', self.uc.temp_dir + 'driver/driver.lua.bak')

            # Call export functions
            if quick_export:
                self.quick_export(first_call=False, driver_name=driver_name)
                if self.abort:
                    self.abort = False
                    return
            else:
                # Save As Dialog
                out_file = filedialog.asksaveasfile(initialfile=driver_name + '.c4z',
                                                    filetypes=[("Control4 Drivers", "*.c4z")])
                out_file_path = out_file.name
                out_file.close()
                flag_remove_empty_file = False
                if '.c4z' not in out_file_path:
                    flag_remove_empty_file = True
                    out_file_path += '.c4z'

                # Export file
                if os.path.isfile(out_file_path):
                    os.remove(out_file_path)
                self.export_file(driver_name, path=out_file_path)
                if flag_remove_empty_file:
                    os.remove(out_file_path.replace('.c4z', ''))

            # Restore original xml and lua
            self.uc.driver_xml.restore()
            if os.path.isfile(self.uc.temp_dir + 'driver/driver.lua'):
                os.remove(self.uc.temp_dir + 'driver/driver.lua')
                os.rename(self.uc.temp_dir + 'driver/driver.lua.bak', self.uc.temp_dir + 'driver/driver.lua')
            os.remove(self.uc.temp_dir + 'driver/driver.xml')
            os.rename(self.uc.temp_dir + 'driver/driver.xml.bak', self.uc.temp_dir + 'driver/driver.xml')

        def export_file(self, driver_name: str, path=None):
            if path is None:
                path = self.uc.cur_dir + driver_name + '.c4z'
            bak_files_dict = {}
            bak_files = []
            bak_folder = self.uc.temp_dir + 'bak_files/'

            # Backup and move all .bak files
            if self.include_backups.get() == 0:
                directories = list_all_sub_directories(self.uc.temp_dir + 'driver')
                directories.insert(0, self.uc.temp_dir + 'driver')
                if os.path.isdir(bak_folder):
                    shutil.rmtree(bak_folder)
                os.mkdir(bak_folder)
                for directory in directories:
                    for file in os.listdir(directory):
                        if file.endswith('.bak'):
                            random_tag = str(random.randint(1111111, 9999999))
                            bak_files.append(directory + '/' + file)
                            bak_files_dict[directory + '/' + file] = bak_folder + file + random_tag
                            shutil.copy(directory + '/' + file, bak_folder + file + random_tag)
                            os.remove(directory + '/' + file)

            # Create .c4z file
            shutil.make_archive(self.uc.temp_dir + driver_name, 'zip', self.uc.temp_dir + '/driver')
            base = os.path.splitext(self.uc.temp_dir + driver_name + '.zip')[0]
            os.rename(self.uc.temp_dir + driver_name + '.zip', base + '.c4z')
            shutil.copy(self.uc.temp_dir + driver_name + '.c4z', path)
            os.remove(self.uc.temp_dir + driver_name + '.c4z')

            # Restore .bak files
            if self.include_backups.get() == 0:
                for file in bak_files:
                    shutil.copy(bak_files_dict[file], file)
                shutil.rmtree(bak_folder)

        def validate_driver_name(self, *args):
            if args:  # For IDE unused argument warning
                pass

            driver_name = self.driver_name_var.get()
            temp = ''
            for letter in driver_name:
                if str(letter).isalnum() or str(letter) == '_' or str(letter) == '-' or str(letter) == ' ':
                    temp += str(letter)
            driver_name = temp
            self.driver_name_entry.delete(0, 'end')
            self.driver_name_entry.insert(0, driver_name)

    class ConnectionsPanel:
        class Connection:
            def __init__(self, upper_class, x_pos: int, y_pos: int, conn_id=0):
                # Initialize Connection UI Object
                self.uc = upper_class
                self.x = x_pos
                self.y = y_pos
                self.id = conn_id
                self.original = False
                self.in_id_group = False
                self.delete = False
                self.prior_txt = ''
                self.prior_type = ''
                # tags[0] = connection_tag, tags[1] = class_tag, tags[2] = connectionname_tag
                # tags[3] = id_tag, tags[4] = type_tag, tags[5] = classname_tag
                self.tags = []
                self.id_group = []

                # Entry
                self.name_entry = tk.Entry(self.uc.root, width=20)
                self.name_entry.insert(0, 'Connection Name...')
                self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
                self.name_entry['state'] = DISABLED

                # Dropdown
                self.type = StringVar(self.uc.root)
                self.type.set('HDMI IN')
                self.type_menu = OptionMenu(self.uc.root, self.type, 'HDMI IN', 'HDMI OUT', 'COMPOSITE IN',
                                            'COMPOSITE OUT', 'VGA IN', 'VGA OUT', 'COMPONENT IN', 'COMPONENT OUT',
                                            'DVI IN', 'DVI OUT', 'STEREO IN', 'STEREO OUT', 'DIGITAL_OPTICAL IN',
                                            'DIGITAL_OPTICAL OUT', 'IR_OUT')
                self.type_menu.place(x=self.x + 160, y=self.y, anchor='w')
                self.type.trace('w', self.update_id)
                self.type_menu['state'] = DISABLED

                # Buttons
                self.add_button = tk.Button(self.uc.root, text='Add', width=3, command=self.enable, takefocus=0)
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.add_button['state'] = DISABLED

                self.x_button = tk.Button(self.uc.root, text='x', width=1, command=self.disable, takefocus=0)
                self.x_button.place(x=-420, y=-420, anchor='w')

                self.del_button = tk.Button(self.uc.root, text='Del', width=3, command=self.flag_delete, takefocus=0)
                self.del_button.place(x=-420, y=-420, anchor='w')

            def enable(self):
                self.name_entry['state'] = NORMAL
                self.type_menu['state'] = NORMAL
                self.add_button.place(x=-420, y=-420, anchor='w')
                self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
                self.tags[0].delete = False
                self.name_entry['takefocus'] = 1

            def disable(self):
                self.name_entry['state'] = DISABLED
                self.type_menu['state'] = DISABLED
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.x_button.place(x=-420, y=-420, anchor='w')
                self.tags[0].delete = True
                self.name_entry['takefocus'] = 0

            def flag_delete(self):
                if not self.original:
                    return
                if not self.delete:
                    self.delete = True
                    self.prior_txt = self.name_entry.get()
                    self.prior_type = self.type.get()
                    self.type.set('RIP')
                    self.name_entry['state'] = NORMAL
                    self.name_entry.delete(0, END)
                    self.name_entry.insert(0, 'TO BE DELETED')
                    self.name_entry['state'] = DISABLED
                    self.del_button['text'] = 'Keep'
                    self.del_button['width'] = 4
                    self.del_button.place(x=self.del_button.winfo_x() - 6, y=self.y)
                    if len(self.id_group) > 1:
                        first = True
                        last_alive = True
                        for groupie in self.id_group:
                            if first:
                                first = False
                                continue
                            if not groupie.delete:
                                last_alive = False
                                break
                        if last_alive:
                            self.tags[0].delete = True
                        self.tags[1].delete = True
                    return
                self.delete = False
                self.name_entry['state'] = NORMAL
                self.name_entry.delete(0, END)
                self.name_entry.insert(0, self.prior_txt)
                self.prior_txt = ''
                self.name_entry['state'] = DISABLED
                self.type.set(self.prior_type)
                self.prior_type = ''
                self.tags[0].delete = False
                self.tags[1].delete = False
                self.del_button['text'] = 'Del'
                self.del_button['width'] = 3
                self.del_button.place(x=self.del_button.winfo_x() + 6, y=self.y)

            def reinit(self):
                self.id = 0
                self.original = False
                self.in_id_group = False
                self.delete = False
                self.prior_txt = ''
                self.prior_type = ''
                if self.tags:
                    self.disable()
                    self.tags = []
                self.id_group = []

                # Entry
                self.name_entry['state'] = NORMAL
                self.name_entry.delete(0, END)
                self.name_entry.insert(0, 'Connection Name...')
                self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
                self.name_entry['state'] = DISABLED
                self.name_entry['takefocus'] = 0

                # Dropdown
                self.type.set('HDMI IN')
                self.type_menu.place(x=self.x + 160, y=self.y, anchor='w')
                self.type_menu['state'] = DISABLED

                # Buttons
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.x_button.place(x=-420, y=-420, anchor='w')
                self.del_button.place(x=-420, y=-420, anchor='w')

            def update_id(self, *args, refresh=False):
                if not args:
                    args = [self.type]
                if self.original:
                    for conn in self.uc.connections_panel.connections:
                        if conn is not self and conn.original and conn.id == self.id:
                            self.in_id_group = True
                            return
                    self.in_id_group = False
                    return
                if not refresh and (args[0] != str(self.type) or self.type_menu['state'] == DISABLED):
                    return
                conn_type = self.type.get()
                valid_id = []
                if ' IN' in conn_type:
                    conn_type = conn_type.replace(' IN', '')
                    if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                        valid_id = find_valid_id(2000, self.uc.connections_panel.ids)
                        self.tags[4].value = '5'
                    elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                        valid_id = find_valid_id(4000, self.uc.connections_panel.ids)
                        self.tags[4].value = '6'
                elif ' OUT' in conn_type:
                    conn_type = conn_type.replace(' OUT', '')
                    if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                        valid_id = find_valid_id(1900, self.uc.connections_panel.ids)
                        self.tags[4].value = '5'
                    elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                        valid_id = find_valid_id(3900, self.uc.connections_panel.ids)
                        self.tags[4].value = '6'
                if conn_type == 'IR_OUT':
                    valid_id = find_valid_id(1, self.uc.connections_panel.ids)
                    self.tags[4].value = '6'

                if self.id in self.uc.connections_panel.ids:
                    self.uc.connections_panel.ids.pop(self.uc.connections_panel.ids.index(self.id))
                self.id = valid_id[0]
                self.tags[3].value = str(self.id)
                self.uc.connections_panel.ids.append(self.id)

        def __init__(self, upper_class):
            # Initialize Connection Panel
            self.x = 14
            self.y = 280
            self.uc = upper_class
            self.connections = []
            self.ids = []

            x_spacing = 318
            y_spacing = 40
            for x in range(0, 4):
                for i in range(0, 6):
                    self.connections.append(self.Connection(self.uc, (x * x_spacing) + self.x,
                                                            (i * y_spacing) + 20 + self.y))

        def reinit(self):
            for conn in self.connections:
                conn.reinit()

    class StatePanel:
        class DriverState:
            def __init__(self, upper_class, name: str, x_pos: int, y_pos: int, state_name='State69:'):
                # Initialize Driver State UI Object
                self.uc = upper_class
                self.original_name = name
                self.x = x_pos
                self.y = y_pos
                self.name = state_name

                # Label
                self.name_label = tk.Label(self.uc.root, text=self.name)
                self.name_label.place(x=self.x + 35, y=self.y, anchor='e')

                # Entry
                self.name_var = StringVar()
                self.name_var.set('')
                self.name_var.trace('w', self.validate_state)
                self.name_entry = tk.Entry(self.uc.root, width=20, textvariable=self.name_var)
                self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
                self.name_entry['state'] = DISABLED

            def validate_state(self, *args):
                if args:  # For IDE unused argument warning
                    pass
                self.format_state_name()
                if self.name_var.get() == '':
                    self.name_entry['background'] = 'pink'
                    return
                duplicate = False
                for state in self.uc.state_panel.states:
                    if state is not self and state.name_var.get() == self.name_var.get():
                        duplicate = True
                        for dupe_list in self.uc.state_panel.dupes:
                            if self in dupe_list:
                                if len(dupe_list) == 2:
                                    dupe_list[0].name_entry['background'] = 'white'
                                    dupe_list[1].name_entry['background'] = 'white'
                                    to_validate = None
                                    if dupe_list[0] is not self:
                                        to_validate = dupe_list[0]
                                    if dupe_list[1] is not self:
                                        to_validate = dupe_list[1]
                                    self.uc.state_panel.dupes.pop(self.uc.state_panel.dupes.index(dupe_list))
                                    if to_validate:
                                        to_validate.validate_state()
                                    break
                                dupe_list.pop(dupe_list.index(self))
                                break
                        append_new_list = True
                        for dupe_list in self.uc.state_panel.dupes:
                            if dupe_list[0].name_var.get() == self.name_var.get():
                                if self not in dupe_list:
                                    dupe_list.append(self)
                                append_new_list = False
                                break
                        if append_new_list:
                            self.uc.state_panel.dupes.append([self, state])
                        self.name_entry['background'] = 'pink'
                        state.name_entry['background'] = 'pink'
                        break
                if not duplicate:
                    for dupe_list in self.uc.state_panel.dupes:
                        if self in dupe_list:
                            if len(dupe_list) == 2:
                                dupe_list[0].name_entry['background'] = 'white'
                                dupe_list[1].name_entry['background'] = 'white'
                                to_validate = None
                                if dupe_list[0] is not self:
                                    to_validate = dupe_list[0]
                                if dupe_list[1] is not self:
                                    to_validate = dupe_list[1]
                                self.uc.state_panel.dupes.pop(self.uc.state_panel.dupes.index(dupe_list))
                                if to_validate:
                                    to_validate.validate_state()
                                break
                            dupe_list.pop(dupe_list.index(self))
                            break
                    self.name_entry['background'] = 'white'

                for state in self.uc.state_panel.states:
                    if state is self:
                        continue
                    using_existing_name = False
                    for orig_name in self.uc.states_orig_names:
                        if self.uc.state_panel.states.index(self) == self.uc.states_orig_names.index(orig_name):
                            continue
                        if self.name_var.get() in orig_name:
                            using_existing_name = True
                            break
                    if using_existing_name:
                        if self.name_entry['background'] != 'pink':
                            self.name_entry['background'] = 'cyan'
                        break

            def format_state_name(self):
                formatted_name = ''
                for character in self.name_entry.get():
                    if character == ' ' or (character not in letters and character not in capital_letters and
                                            character not in numbers):
                        continue
                    if formatted_name == '' and character in letters:
                        formatted_name += capital_letters[letters.index(character)]
                        continue
                    formatted_name += character
                if formatted_name == self.name_entry.get():
                    return
                self.name_entry.delete(0, 'end')
                self.name_entry.insert(0, formatted_name)

        def __init__(self, upper_class):
            # Initialize State Panel
            self.x = 930
            self.y = 27
            self.uc = upper_class
            self.states = []
            self.dupes = []
            x_spacing = 200
            y_spacing = 34
            for i in range(13):
                self.states.append(self.DriverState(self.uc, 'state' + str(i + 1),
                                                    (int(i / 7) * x_spacing) + self.x,
                                                    ((i % 7) * y_spacing) + 20 + self.y,
                                   state_name='state' + str(i + 1) + ':'))

            # Label
            self.panel_label = tk.Label(self.uc.root, text='Multi-State Labels', font=("Arial", 15))
            self.panel_label.place(x=185 + self.x, y=-27 + self.y, anchor='n')

    def __init__(self):
        # Initialize main program
        self.root = TkinterDnD.Tk()
        self.root.bind('<KeyRelease>', self.key_release)

        # Root window properties
        self.root.geometry('915x270')
        self.root.title('C4 Icon Swapper')
        self.root.resizable(False, False)

        # Creating temporary directory
        self.cur_dir = os.getcwd() + '/'
        self.temp_dir = self.cur_dir + 'C4IconSwapperTemp/'
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.mkdir(self.temp_dir)

        # Class variables
        self.counter = 0
        self.states_orig_names = []
        self.driver_xml = None
        self.states_shown = False
        self.device_icon_dir = self.temp_dir + 'driver/www/icons/device'
        self.icon_dir = self.temp_dir + 'driver/www/icons'
        self.replacement_image_path = self.temp_dir + 'replacement_icon.png'
        self.orig_file_dir = ''
        self.orig_file_path = ''
        self.driver_selected = False
        self.replacement_selected = False
        self.schedule_entry_restore = False
        self.restore_entry_string = ''
        self.time_var = 0
        self.driver_version = -1
        self.conn_dict = {}
        for key in ['HDMI IN', 'COMPOSITE IN', 'VGA IN', 'COMPONENT IN', 'DVI IN']:
            self.conn_dict[key] = '\t\t\t<type>5</type>\n\t\t\t' \
                                  '<connectionname>REPLACE</connectionname>\n' \
                                  '\t\t\t<consumer>True</consumer>\n\t\t\t<linelevel>True</linelevel>'
        for key in ['HDMI OUT', 'COMPOSITE OUT', 'VGA OUT', 'COMPONENT OUT', 'DVI OUT']:
            self.conn_dict[key] = '\t\t\t<type>5</type>\n\t\t\t' \
                                  '<connectionname>REPLACE</connectionname>\n' \
                                  '\t\t\t<consumer>False</consumer>\n\t\t\t<linelevel>True</linelevel>'
        for key in ['STEREO IN', 'DIGITAL_OPTICAL IN']:
            self.conn_dict[key] = '\t\t\t<type>6</type>\n\t\t\t' \
                                  '<connectionname>REPLACE</connectionname>\n' \
                                  '\t\t\t<consumer>True</consumer>\n\t\t\t<linelevel>True</linelevel>'
        for key in ['STEREO OUT', 'DIGITAL_OPTICAL OUT']:
            self.conn_dict[key] = '\t\t\t<type>6</type>\n\t\t\t' \
                                  '<connectionname>REPLACE</connectionname>\n' \
                                  '\t\t\t<consumer>False</consumer>\n\t\t\t<linelevel>True</linelevel>'

        self.conn_dict['IR_OUT'] = '\t\t\t<facing>6</facing>\n\t\t\t' \
                                   '<connectionname>REPLACE</connectionname>\n' \
                                   '\t\t\t<type>1</type>\n\t\t\t<consumer>False</consumer>\n\t\t\t' \
                                   '<audiosource>False</audiosource>\n' \
                                   '\t\t\t<videosource>False</videosource>\n\t\t\t<linelevel>False</linelevel>'

        # Panels; Creating blank image for panels
        temp_image_file = self.temp_dir + 'blank.gif'
        with open(temp_image_file, 'wb') as blank_img_file:
            blank_img_file.write(base64.b64decode(blank_img_b64))
        blank_image = Image.open(temp_image_file)
        blank = blank_image.resize((128, 128))
        self.blank = ImageTk.PhotoImage(blank)
        stack_blank = blank_image.resize((60, 60))
        self.stack_blank = ImageTk.PhotoImage(stack_blank)
        blank_image.close()
        os.remove(temp_image_file)

        # Initialize Panels
        self.c4z_panel = self.C4zPanel(self)
        self.replacement_panel = self.ReplacementPanel(self)
        self.export_panel = self.ExportPanel(self)
        self.connections_panel = self.ConnectionsPanel(self)
        self.state_panel = self.StatePanel(self)

        for conn in self.connections_panel.connections:
            conn.name_entry['takefocus'] = 0
        for state in self.state_panel.states:
            state.name_entry['takefocus'] = 0

        # Separators
        self.separator0 = ttk.Separator(self.root, orient='vertical')
        self.separator0.place(x=305, y=0, height=270)
        self.separator1 = ttk.Separator(self.root, orient='vertical')
        self.separator1.place(x=610, y=0, height=270)
        self.separator2 = ttk.Separator(self.root, orient='horizontal')
        self.separator2.place(x=0, y=270, relwidth=1)
        self.separator3 = ttk.Separator(self.root, orient='vertical')
        self.separator3.place(x=915, y=0, height=270)

        # Buttons
        self.toggle_conn_button = tk.Button(self.root, text='Show Connections', width=15,
                                            command=self.toggle_connections_panel, takefocus=0)
        self.toggle_conn_button.place(x=700, y=240, anchor='n')

        self.show_states_button = tk.Button(self.root, text='Show States', width=15, command=self.show_states_panel,
                                            takefocus=0)
        self.show_states_button.place(x=820, y=240, anchor='n')

        # Version Label
        self.version_label = Label(self.root, text=version)
        self.version_label.place(relx=1, rely=1.01, anchor='se')

        # Creating window icon
        temp_icon_file = self.temp_dir + 'icon.ico'
        with open(temp_icon_file, 'wb') as icon_file:
            icon_file.write(base64.b64decode(win_icon))
        self.root.wm_iconbitmap(temp_icon_file)
        os.remove(temp_icon_file)

        # Main Loop
        self.root.after(0, self.restore_entry_text)
        self.root.mainloop()
        shutil.rmtree(self.temp_dir)

    def toggle_connections_panel(self):
        if not self.states_shown:
            if self.toggle_conn_button['text'] == 'Show Connections':
                self.toggle_conn_button['text'] = 'Hide Connections'
                self.root.geometry('915x530')
                for conn in self.connections_panel.connections:
                    if conn.name_entry['state'] == NORMAL:
                        conn.name_entry['takefocus'] = 1
                return
            self.toggle_conn_button['text'] = 'Show Connections'
            self.root.geometry('915x270')
            for conn in self.connections_panel.connections:
                conn.name_entry['takefocus'] = 0
            return
        if self.toggle_conn_button['text'] == 'Show Connections':
            self.toggle_conn_button['text'] = 'Hide Connections'
            self.root.geometry('1300x530')
            for conn in self.connections_panel.connections:
                if conn.name_entry['state'] == NORMAL:
                    conn.name_entry['takefocus'] = 1
            return
        self.toggle_conn_button['text'] = 'Show Connections'
        self.root.geometry('1300x270')
        for conn in self.connections_panel.connections:
            conn.name_entry['takefocus'] = 0
        return

    def show_states_panel(self):
        if not self.states_shown:
            if self.toggle_conn_button['text'] == 'Show Connections':
                self.root.geometry('1300x270')
                self.states_shown = True
            else:
                self.root.geometry('1300x530')
                self.states_shown = True
            self.show_states_button['text'] = 'Hide States'
            for i in range(7):
                if self.connections_panel.connections[-i].name_entry['state'] == NORMAL:
                    self.connections_panel.connections[-i].name_entry['takefocus'] = 1
            for state in self.state_panel.states:
                if state.name_entry['state'] == NORMAL:
                    state.name_entry['takefocus'] = 1
            return
        elif self.toggle_conn_button['text'] == 'Show Connections':
            self.root.geometry('915x270')
            self.states_shown = False
        else:
            self.root.geometry('915x530')
            self.states_shown = False
        for i in range(7):
            if self.connections_panel.connections[-i].name_entry['state'] == NORMAL:
                self.connections_panel.connections[-i].name_entry['takefocus'] = 0
        for state in self.state_panel.states:
            state.name_entry['takefocus'] = 0
        self.show_states_button['text'] = 'Show States'

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

    def key_release(self, event):
        if event.keysym == 'Right':
            self.c4z_panel.next_icon()
        elif event.keysym == 'Left':
            self.c4z_panel.prev_icon()
        elif event.keysym == 'Up':
            self.replacement_panel.inc_img_stack()
        elif event.keysym == 'Down':
            self.replacement_panel.dec_img_stack()

    def get_states(self, lua_file):
        state_names = []
        find_names = False
        self.states_orig_names = []
        for line in lua_file:
            if '_OPTIONS = {' in line or find_names:
                find_names = True
                build_name = False
                working_name = ''
                for character in line:
                    if build_name:
                        if character == '{':
                            build_name = False
                            continue
                        if character == '=':
                            working_name = working_name[0:-1]
                            state_names.append(working_name)
                            self.states_orig_names.append([working_name])
                            if self.states_orig_names[-1][0][0] in capital_letters:
                                self.states_orig_names[-1].append(
                                    self.states_orig_names[-1][0].replace(
                                        self.states_orig_names[-1][0][0],
                                        letters[capital_letters.index(self.states_orig_names[-1][0][0])]))
                            else:
                                self.states_orig_names[-1].insert(
                                    0, self.states_orig_names[-1][0].replace(
                                        self.states_orig_names[-1][0][0],
                                        capital_letters[letters.index(self.states_orig_names[-1][0][0])]))
                            working_name = ''
                            build_name = False
                            continue
                        working_name += character
                        continue
                    working_name += character
                    if len(working_name) > 2:
                        working_name = working_name[1:len(working_name)]
                    if working_name == '{ ':
                        build_name = True
                        working_name = ''
            if 'States, LED = {},' in line or 'States = {}' in line:
                break

        for state_name in state_names:
            self.state_panel.states[state_names.index(state_name)].name_entry['state'] = NORMAL
            if self.states_shown:
                self.state_panel.states[state_names.index(state_name)].name_entry['takefocus'] = 1
            self.state_panel.states[state_names.index(state_name)].name_entry.delete(0, END)
            self.state_panel.states[state_names.index(state_name)].name_entry.insert(0, state_name)
            self.state_panel.states[state_names.index(state_name)].original_name = state_name

    def disable_states(self):
        for state in self.state_panel.states:
            state.name_entry['state'] = DISABLED
            state.name_entry['takefocus'] = 0
            state.original_name = ''

    def show_loading_image(self):
        self.c4z_panel.load_gen_multi(show_loading_image=False)

    def blink_driver_name_entry(self):
        if self.counter > 0:
            self.counter -= 1
            if self.export_panel.driver_name_entry['background'] != 'white':
                self.export_panel.driver_name_entry['background'] = 'white'
            else:
                self.export_panel.driver_name_entry['background'] = 'pink'
            self.root.after(150, self.blink_driver_name_entry)


def list_all_sub_directories(directory):
    subs = []
    for dir_name in os.listdir(directory):
        if '.' not in dir_name:
            subs.append(directory + '/' + dir_name)
    if len(subs) != 0:
        new_subs = []
        for sub_dir in subs:
            next_subs = list_all_sub_directories(sub_dir)
            for new_sub in next_subs:
                new_subs.append(new_sub)
        for new_sub in new_subs:
            subs.append(new_sub)
    subs.sort()
    return subs


def find_valid_id(id_seed: int, list_of_ids: list, inc_up=True, inc_count=0):
    if id_seed not in list_of_ids:
        return [id_seed, inc_count]
    if inc_up:
        id_seed += 1
    else:
        id_seed -= 1
    inc_count += 1
    return find_valid_id(id_seed, list_of_ids, inc_count=inc_count)


def natural_key(string):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]
