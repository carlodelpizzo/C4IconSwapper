import os
import shutil
import base64
import time
import random
import re
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import ImageTk, Image
from datetime import datetime
from Base64Assets import *

version = '4.0a'


# This shit is a mess
class C4IconSwapper:
    class C4zPanel:
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

        def __init__(self, upper_class):
            self.x = 5
            self.y = 5
            self.uc = upper_class
            self.current_icon = 0
            self.icon_groups = []
            self.valid_connections = ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI', 'STEREO', 'DIGITAL_OPTICAL',
                                      'IR_OUT']

            # Labels
            self.blank_image_label = tk.Label(self.uc.root, image=self.uc.blank)
            self.blank_image_label.image = self.uc.blank
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

            self.icon_label = tk.Label(self.uc.root, text='0 of 0')
            self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

            self.icon_name_label = tk.Label(self.uc.root, text='icon name')
            self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

            # Buttons
            self.open_file_button = tk.Button(self.uc.root, text='Open', width=10, command=self.upload_c4z)
            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

            self.restore_button = tk.Button(self.uc.root, text='Restore \n Original Icon', command=self.restore_icon)
            self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.restore_button['state'] = DISABLED

            self.restore_all_button = tk.Button(self.uc.root, text='Restore All', command=self.restore_all)
            self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.restore_all_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.uc.root, text='Prev', command=self.prev_icon, width=5)
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.uc.root, text='Next', command=self.next_icon, width=5)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
            self.next_icon_button['state'] = DISABLED

            self.gen_driver_button = tk.Button(self.uc.root, text='Load Generic Driver', command=self.load_gen_driver)
            self.gen_driver_button.place(x=228 + self.x, y=189 + self.y, anchor='n')

            # Entry
            self.file_entry_field = tk.Entry(self.uc.root, width=25)
            self.file_entry_field.insert(0, 'Select .c4z file...')
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field['state'] = DISABLED

        def load_gen_driver(self):
            temp_gen_driver = self.uc.temp_dir + 'generic.c4z'
            if self.file_entry_field.get() == temp_gen_driver:
                return
            gen_driver = open(temp_gen_driver, 'wb')
            gen_driver.write(base64.b64decode(generic_driver))
            gen_driver.close()
            self.upload_c4z(temp_gen_driver)

        def update_icon(self):
            icon_image = Image.open(self.icon_groups[self.current_icon].path)

            icon = icon_image.resize((128, 128), Image.ANTIALIAS)
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label = tk.Label(self.uc.root, image=icon)
            self.blank_image_label.image = icon
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

            self.icon_label.config(text='icon: ' + str(self.current_icon + 1) + ' of ' + str(len(self.icon_groups)))
            self.icon_name_label.config(text='name: ' + self.icon_groups[self.current_icon].name)

        def blank_icon(self):
            self.blank_image_label = tk.Label(self.uc.root, image=self.uc.blank)
            self.blank_image_label.image = self.uc.blank
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
            self.icon_label.config(text='icon: 0 of 0')
            self.icon_name_label.config(text='name:')
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
            self.uc.replacement_panel.prev_icon_button['state'] = DISABLED
            self.uc.replacement_panel.next_icon_button['state'] = DISABLED

        def upload_c4z(self, given_path=''):
            if len(self.icon_groups) != 0:
                icons_groups_bak = self.icon_groups
                if os.path.isdir(self.uc.temp_dir + 'driver'):
                    shutil.copytree(self.uc.temp_dir + 'driver', self.uc.temp_dir + '/bak/')
            else:
                icons_groups_bak = None

            icon_objects = []
            if given_path == '':
                filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])
            else:
                filename = given_path

            if filename:
                if os.path.isdir(self.uc.temp_dir + 'driver'):
                    shutil.rmtree(self.uc.temp_dir + 'driver')

                shutil.unpack_archive(filename, self.uc.temp_dir + 'driver', 'zip')

                if os.path.isdir(self.uc.device_icon_dir):
                    icon_list = os.listdir(self.uc.device_icon_dir)
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
                        icon_objects.append(self.Icon(self.uc.device_icon_dir + str(icon_list[i]),
                                                      temp_name, int(temp_size)))
                if os.path.isdir(self.uc.icon_dir):
                    icon_list = os.listdir(self.uc.icon_dir)
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
                                icon_objects.append(self.Icon(self.uc.icon_dir + str(icon_list[i]),
                                                              temp_name, int(temp_size)))
                    for i in range(len(icon_list)):
                        if icon_list[i][len(icon_list[i]) - 4] == '.':
                            if 'device_lg' in icon_list[i]:
                                icon_objects.append(self.Icon(self.uc.icon_dir + str(icon_list[i]), 'device', 32))
                            elif 'device_sm' in icon_list[i]:
                                icon_objects.append(self.Icon(self.uc.icon_dir + str(icon_list[i]), 'device', 16))

                self.icon_groups = []
                temp_list = []
                for i in range(len(icon_objects)):
                    if not temp_list:
                        temp_list.append(icon_objects[i])
                    elif icon_objects[i].name == temp_list[0].name:
                        temp_list.append(icon_objects[i])
                    else:
                        new_icon_group = self.IconGroup(temp_list)
                        self.icon_groups.append(new_icon_group)
                        temp_list = [icon_objects[i]]
                    if i == len(icon_objects) - 1:
                        new_icon_group = self.IconGroup(temp_list)
                        self.icon_groups.append(new_icon_group)
                        temp_list = ''

                preserve_prev_next = False
                if len(self.icon_groups) > 0:
                    self.file_entry_field['state'] = NORMAL
                    self.file_entry_field.delete(0, 'end')
                    self.file_entry_field.insert(0, filename)
                    self.file_entry_field['state'] = 'readonly'
                    orig_file_path = filename
                    orig_driver_name = ''
                    for i in reversed(range(len(orig_file_path))):
                        if orig_file_path[i] == '/':
                            self.uc.orig_file_dir = orig_file_path[0:i + 1]
                            break
                        if orig_file_path[i] == '.':
                            orig_driver_name = '.'
                        if orig_driver_name != '':
                            if orig_driver_name == '.':
                                orig_driver_name = orig_file_path[i]
                            else:
                                orig_driver_name = orig_file_path[i] + orig_driver_name
                    self.uc.export_panel.driver_name_entry.delete(0, 'end')
                    self.uc.export_panel.driver_name_entry.insert(0, orig_driver_name)
                    self.uc.driver_selected = True
                    self.update_icon()
                else:
                    self.file_entry_field['state'] = NORMAL
                    if self.file_entry_field.get() != 'Select .c4z file...' and \
                            self.file_entry_field.get() != 'Invalid driver selected...':
                        self.icon_groups = icons_groups_bak
                        self.uc.schedule_entry_restore = True
                        self.uc.restore_entry_string = self.file_entry_field.get()
                        preserve_prev_next = True
                        if os.path.isdir(self.uc.temp_dir + '/driver/'):
                            shutil.rmtree(self.uc.temp_dir + '/driver/')
                        shutil.copytree(self.uc.temp_dir + '/bak/', self.uc.temp_dir + '/driver/')
                    self.file_entry_field.delete(0, 'end')
                    self.file_entry_field.insert(0, 'Invalid driver selected...')
                    self.file_entry_field['state'] = DISABLED

                if not preserve_prev_next:
                    if len(self.icon_groups) <= 1:
                        self.prev_icon_button['state'] = DISABLED
                        self.next_icon_button['state'] = DISABLED
                        self.uc.replacement_panel.prev_icon_button['state'] = DISABLED
                        self.uc.replacement_panel.next_icon_button['state'] = DISABLED
                    elif len(self.icon_groups) > 1:
                        self.prev_icon_button['state'] = ACTIVE
                        self.next_icon_button['state'] = ACTIVE
                        self.uc.replacement_panel.prev_icon_button['state'] = ACTIVE
                        self.uc.replacement_panel.next_icon_button['state'] = ACTIVE

                if self.uc.replacement_selected:
                    if self.uc.driver_selected:
                        self.uc.replacement_panel.replace_button['state'] = ACTIVE
                        self.uc.replacement_panel.replace_all_button['state'] = ACTIVE
                    else:
                        self.uc.replacement_panel.replace_button['state'] = DISABLED
                        self.uc.replacement_panel.replace_all_button['state'] = DISABLED
                if self.uc.driver_selected:
                    self.uc.export_panel.export_button['state'] = ACTIVE

                if os.path.isdir(self.uc.temp_dir + '/bak/'):
                    shutil.rmtree(self.uc.temp_dir + '/bak/')

            self.update_connections()

        def restore_icon(self, index=None):
            if index is None:
                index = self.current_icon
            elif 0 > index > len(self.icon_groups):
                return print('icon restore index out of range')

            for icon in self.icon_groups[index].icons:
                if os.path.isfile(icon.path + '.orig'):
                    shutil.copy(icon.path + '.orig', icon.path)
                    os.remove(icon.path + '.orig')
            self.restore_button['state'] = DISABLED
            disable_all_button = True
            for group in self.icon_groups:
                if os.path.isfile(group.icons[0].path + '.orig'):
                    disable_all_button = False
            if disable_all_button:
                self.restore_all_button['state'] = DISABLED
            self.update_icon()

        def restore_all(self):
            for i in range(len(self.icon_groups)):
                self.restore_icon(index=i)
            self.restore_button['state'] = DISABLED
            self.restore_all_button['state'] = DISABLED
            self.update_icon()

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
                self.restore_button['state'] = ACTIVE
            else:
                self.restore_button['state'] = DISABLED

            self.update_icon()

        def prev_icon(self):
            self.inc_current_icon(step=-1)

        def next_icon(self):
            self.inc_current_icon()

        def update_connections(self):
            if not os.path.isfile(self.uc.temp_dir + '/driver/driver.xml'):
                return
            self.uc.connections_panel.reinit()

            os.rename(self.uc.temp_dir + '/driver/driver.xml', self.uc.temp_dir + '/driver/driver.txt')
            driver_xml_file = open(self.uc.temp_dir + '/driver/driver.txt', errors='ignore')
            driver_xml_lines = driver_xml_file.readlines()
            driver_xml_file.close()

            in_connection = False
            name_found = False
            connections = []
            conn_name = ''
            for line in driver_xml_lines:
                if in_connection:
                    if '</connection>' in line:
                        in_connection = False
                        name_found = False
                        continue
                    if not name_found and '<connectionname>' in line:
                        conn_name = re.search('<connectionname>(.*)</connectionname>', line).group(1)
                        name_found = True
                    elif name_found and '<classname>' in line:
                        connections.append([conn_name, re.search('<classname>(.*)</classname>', line).group(1)])
                elif '<connection>' in line:
                    in_connection = True

            os.rename(self.uc.temp_dir + '/driver/driver.txt', self.uc.temp_dir + '/driver/driver.xml')

            pop_list = []
            for i in range(len(connections)):
                if connections[i][1] not in self.valid_connections:
                    pop_list.insert(0, i)
            for index in pop_list:
                connections.pop(index)

            if len(connections) > len(self.uc.connections_panel.connection_types):
                conn_range = len(self.uc.connections_panel.connection_types)
            else:
                conn_range = len(connections)

            self.uc.connections_panel.buttons[conn_range]['state'] = NORMAL
            if conn_range == 0:
                return
            for i in range(0, conn_range):
                self.uc.connections_panel.buttons[i].place(x=-10000, y=-10000)
                self.uc.connections_panel.connection_entries[i]['state'] = NORMAL
                self.uc.connections_panel.connection_entries[i].delete(0, END)
                self.uc.connections_panel.connection_entries[i].insert(0, connections[i][0])
                self.uc.connections_panel.connection_entries[i]['state'] = DISABLED
                self.uc.connections_panel.connection_menus[i]['state'] = DISABLED
                self.uc.connections_panel.connection_types[i].set(connections[i][1])

    class ReplacementPanel:
        def __init__(self, upper_class):
            self.x = 310
            self.y = 5
            self.uc = upper_class

            # Labels
            self.blank_image_label = tk.Label(self.uc.root, image=self.uc.blank)
            self.blank_image_label.image = self.uc.blank
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

            # Buttons
            self.open_file_button = tk.Button(self.uc.root, text='Open', width=10, command=self.upload_replacement)
            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

            self.replace_all_button = tk.Button(self.uc.root, text='Replace All', command=self.replace_all)
            self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.replace_all_button['state'] = DISABLED

            self.replace_button = tk.Button(self.uc.root, text='Replace \n Current Icon', command=self.replace_icon)
            self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.replace_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.uc.root, text='Prev', command=self.uc.c4z_panel.prev_icon, width=5)
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.uc.root, text='Next', command=self.uc.c4z_panel.next_icon, width=5)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
            self.next_icon_button['state'] = DISABLED

            self.open_conn_button = tk.Button(self.uc.root, text='Open Connections', width=15,
                                              command=self.open_connections)
            self.open_conn_button.place(x=95 + self.x, y=227 + self.y, anchor='w')

            # Entry
            self.file_entry_field = tk.Entry(self.uc.root, width=25)
            self.file_entry_field.insert(0, 'Select image file...')
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field['state'] = DISABLED

        def update_icon(self):
            if self.uc.replacement_selected:
                icon_image = Image.open(self.uc.replacement_image_path)
                icon = icon_image.resize((128, 128), Image.ANTIALIAS)
                icon = ImageTk.PhotoImage(icon)
                self.blank_image_label = tk.Label(self.uc.root, image=icon)
                self.blank_image_label.image = icon
                self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        def upload_replacement(self):
            filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"),
                                                             ("Image", "*.gif"), ("Image", "*.jpeg")])

            if filename:
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

                if os.path.isfile(self.uc.temp_dir + 'replacement_icon.png'):
                    self.uc.replacement_selected = True
                    self.update_icon()

        def replace_icon(self, index=None):
            if index is None:
                index = self.uc.c4z_panel.current_icon
            elif 0 > index > len(self.uc.c4z_panel.icon_groups):
                return print('icon replace index out of range')

            replacement_icon = Image.open(self.uc.replacement_image_path)
            for icon in self.uc.c4z_panel.icon_groups[index].icons:
                if not os.path.isfile(icon.path + '.orig'):
                    shutil.copy(icon.path, icon.path + '.orig')
                new_icon = replacement_icon.resize((icon.size, icon.size))
                new_icon.save(icon.path)
            self.uc.c4z_panel.restore_button['state'] = ACTIVE
            self.uc.c4z_panel.restore_all_button['state'] = ACTIVE
            self.uc.c4z_panel.update_icon()

        def replace_all(self):
            for i in range(len(self.uc.c4z_panel.icon_groups)):
                self.replace_icon(index=i)

        def open_connections(self):
            if self.open_conn_button['text'] == 'Open Connections':
                self.open_conn_button['text'] = 'Close Connections'
                self.uc.root.geometry('915x500')
            else:
                self.open_conn_button['text'] = 'Open Connections'
                self.uc.root.geometry('915x250')

    class ExportPanel:
        def __init__(self, upper_class):
            self.x = 615
            self.y = -20
            self.uc = upper_class
            self.video_in_count = 0
            self.video_out_count = 0
            self.audio_in_count = 0
            self.audio_out_count = 0
            self.ir_count = 0

            # Labels
            self.driver_name_label = tk.Label(self.uc.root, text='Driver Name:')
            self.driver_name_label.place(x=65 + self.x, y=160 + self.y, anchor='w')

            # Buttons
            self.export_button = tk.Button(self.uc.root, text='Export', width=20, command=self.export_c4z)
            self.export_button.place(x=145 + self.x, y=195 + self.y, anchor='n')
            self.export_button['state'] = DISABLED

            # Entry
            self.driver_name_entry = tk.Entry(self.uc.root, width=25)
            self.driver_name_entry.insert(0, 'New Driver')
            self.driver_name_entry.place(x=145 + self.x, y=170 + self.y, anchor='n')

            # Checkboxes
            self.inc_driver_version = IntVar(value=1)
            self.inc_driver_check = Checkbutton(self.uc.root, text="update driver version",
                                                variable=self.inc_driver_version)
            self.inc_driver_check.place(x=63 + self.x, y=135 + self.y, anchor='w')

            self.over_orig = IntVar()
            self.over_orig_check = Checkbutton(self.uc.root, text="overwrite original file", variable=self.over_orig)
            self.over_orig_check.place(x=63 + self.x, y=105 + self.y, anchor='w')

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

            dir_list = os.listdir(self.uc.icon_dir)
            for i in range(len(dir_list)):
                if '.orig' in dir_list[i]:
                    if not os.path.isdir(self.uc.icon_dir + '/original_icons'):
                        os.mkdir(self.uc.icon_dir + '/original_icons')
                    shutil.copy(self.uc.icon_dir + dir_list[i],
                                self.uc.icon_dir + '/original_icons/' + dir_list[i].replace('.orig', ''))
                    os.remove(self.uc.icon_dir + dir_list[i])
            dir_list = os.listdir(self.uc.device_icon_dir)
            for i in range(len(dir_list)):
                if '.orig' in dir_list[i]:
                    if not os.path.isdir(self.uc.device_icon_dir + '/original_icons'):
                        os.mkdir(self.uc.device_icon_dir + '/original_icons')
                    shutil.copy(self.uc.device_icon_dir + dir_list[i],
                                self.uc.device_icon_dir + '/original_icons/' +
                                dir_list[i].replace('.orig', ''))
                    os.remove(self.uc.device_icon_dir + dir_list[i])

            os.rename(self.uc.temp_dir + '/driver/driver.xml', self.uc.temp_dir + '/driver/driver.txt')
            driver_xml_file = open(self.uc.temp_dir + '/driver/driver.txt', errors='ignore')
            driver_xml_lines = driver_xml_file.readlines()
            driver_xml_file.close()
            modified_xml_lines = []
            for line in driver_xml_lines:
                if '<version>' in line and self.inc_driver_version.get():
                    result = re.search('<version>(.*)</version>', line)
                    result_int = int(result.group(1))
                    result_int += 1
                    line = line.replace(result.group(1), str(result_int))
                append_line(modified_xml_lines, line)

            driver_xml_file = open(self.uc.temp_dir + '/driver/driver.txt', 'w', errors='ignore')
            driver_xml_file.writelines(modified_xml_lines)
            driver_xml_file.close()

            shutil.copy(self.uc.temp_dir + '/driver/driver.txt', self.uc.temp_dir + '/driver/driver.xml.bak')
            driver_xml_file = open(self.uc.temp_dir + '/driver/driver.txt', errors='ignore')
            driver_xml_lines = driver_xml_file.readlines()
            driver_xml_file.close()
            modified_xml_lines = []

            do_name_swap = True
            update_modified_date = True
            proxy_step2 = False
            icon_step2 = False
            old_driver_name = ''
            old_icon_path = ''
            insertion = True
            for line in driver_xml_lines:
                printed_line = False
                if '<name>' in line and do_name_swap:
                    result = re.search('<name>(.*)</name>', line)
                    if result:
                        line = line.replace(result.group(1), driver_name)
                    do_name_swap = False
                    append_line(modified_xml_lines, line)
                    printed_line = True
                elif '<modified>' in line and update_modified_date:
                    result = re.search('<modified>(.*)</modified>', line)
                    if result:
                        modified_datestamp = str(datetime.now().strftime("%m/%d/%Y %H:%M"))
                        line = line.replace(result.group(1), modified_datestamp)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                elif '<proxy' in line:
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
                elif '<Icon' in line:
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
                elif '<creator>' in line:
                    result = re.search('<creator>(.*)</creator>', line)
                    if result:
                        line = line.replace(result.group(1), 'C4IconSwapper')
                        append_line(modified_xml_lines, line)
                        printed_line = True
                elif '<manufacturer>' in line:
                    result = re.search('<manufacturer>(.*)</manufacturer>', line)
                    if result:
                        line = line.replace(result.group(1), 'C4IconSwapper')
                        append_line(modified_xml_lines, line)
                        printed_line = True
                if insertion and '</connections>' in line:
                    insertion = False
                    for i in reversed(range(len(self.uc.connections_panel.buttons))):
                        if self.uc.connections_panel.connection_entries[i]['state'] == NORMAL:
                            modified_xml_lines.append('\t\t<connection>\n')
                            conn_type = self.uc.connections_panel.connection_types[i].get()
                            value = self.uc.conn_dict[conn_type]
                            if ' IN' in conn_type:
                                conn_type = conn_type.replace(' IN', '')
                                if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                                    modified_xml_lines.append('\t\t\t<id>' + str(2000 - self.video_in_count) + '</id>')
                                    self.video_in_count += 1
                                elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                                    modified_xml_lines.append('\t\t\t<id>' + str(4000 - self.audio_in_count) + '</id>')
                                    self.audio_in_count += 1
                            elif ' OUT' in conn_type:
                                conn_type = conn_type.replace(' OUT', '')
                                if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                                    modified_xml_lines.append('\t\t\t<id>' + str(1900 - self.video_out_count) + '</id>')
                                    self.video_out_count += 1
                                elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                                    modified_xml_lines.append('\t\t\t<id>' + str(3900 - self.audio_out_count) + '</id>')
                                    self.audio_out_count += 1
                            if conn_type == 'IR_OUT':
                                modified_xml_lines.append('\t\t\t<id>' + str(1 + self.ir_count) + '</id>')
                                self.ir_count += 1
                            value = value.replace('REPLACE', self.uc.connections_panel.connection_entries[i].get())
                            modified_xml_lines.append(value + '\n')
                            modified_xml_lines.append('\t\t\t<classes>\n')
                            modified_xml_lines.append('\t\t\t\t<class>\n')
                            temp_line = '\t\t\t\t\t<classname>' + conn_type + '</classname>\n'
                            modified_xml_lines.append(temp_line)
                            modified_xml_lines.append('\t\t\t\t</class>\n')
                            modified_xml_lines.append('\t\t\t</classes>\n')
                            modified_xml_lines.append('\t\t</connection>\n')
                if not printed_line:
                    append_line(modified_xml_lines, line)

            driver_xml_file = open(self.uc.temp_dir + '/driver/driver.txt', 'w', errors='ignore')
            driver_xml_file.writelines(modified_xml_lines)
            driver_xml_file.close()
            os.rename(self.uc.temp_dir + '/driver/driver.txt', self.uc.temp_dir + '/driver/driver.xml')

            def confirm_write(ran_name=False):
                if ran_name:
                    ran_file_name = 'IcnSwp_'
                    for _ in range(0, 6):
                        ran_file_name += str(random.randint(0, 9))
                    if os.path.isfile(self.uc.cur_dir + ran_file_name + '.c4z'):
                        os.remove(self.uc.cur_dir + ran_file_name + '.c4z')
                    if os.path.isfile(self.uc.cur_dir + ran_file_name + '.zip'):
                        os.remove(self.uc.cur_dir + ran_file_name + '.zip')
                    shutil.make_archive(ran_file_name, 'zip', self.uc.temp_dir + '/driver')
                    base_path = os.path.splitext(self.uc.cur_dir + ran_file_name + '.zip')[0]
                    os.rename(self.uc.cur_dir + ran_file_name + '.zip', base_path + '.c4z')
                else:
                    if os.path.isfile(self.uc.cur_dir + driver_name + '.c4z'):
                        os.remove(self.uc.cur_dir + driver_name + '.c4z')
                    if os.path.isfile(self.uc.cur_dir + driver_name + '.zip'):
                        os.remove(self.uc.cur_dir + driver_name + '.zip')
                    shutil.make_archive(driver_name, 'zip', self.uc.temp_dir + '/driver')
                    base_path = os.path.splitext(self.uc.cur_dir + driver_name + '.zip')[0]
                    os.rename(self.uc.cur_dir + driver_name + '.zip', base_path + '.c4z')

                pop.destroy()

            if self.over_orig.get() == 1:
                temp_name = 'IcnSwp'
                for _ in range(0, 6):
                    temp_name += str(random.randint(0, 9))
                try:
                    if not os.path.isfile(self.uc.orig_file_path + '.orig'):
                        shutil.copy(self.uc.orig_file_path, self.uc.orig_file_path + '.orig')
                    else:
                        shutil.copy(self.uc.orig_file_path, self.uc.orig_file_path + '.' + temp_name)
                        os.remove(self.uc.orig_file_path + '.' + temp_name)
                    shutil.make_archive(temp_name, 'zip', self.uc.temp_dir + '/driver')
                    base = os.path.splitext(self.uc.cur_dir + temp_name + '.zip')[0]
                    os.rename(self.uc.cur_dir + temp_name + '.zip', base + '.c4z')
                    os.remove(self.uc.orig_file_path)
                    shutil.copy(base + '.c4z', self.uc.orig_file_path)
                    os.remove(base + '.c4z')
                except IOError as _:
                    pop = Toplevel(self.uc.root)
                    pop.title('Cannot Overwrite Original File')
                    pop.geometry('239x95')
                    pop.grab_set()
                    pop.transient(self.uc.root)
                    pop.resizable(False, False)

                    label_text = 'Access Denied to: ' + self.uc.orig_file_dir
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
                if os.path.isfile(self.uc.cur_dir + driver_name + '.c4z') or os.path.isfile(
                        self.uc.cur_dir + driver_name + '.zip'):
                    pop = Toplevel(self.uc.root)
                    pop.title('Overwrite')
                    pop.geometry('239x70')
                    pop.grab_set()
                    pop.transient(self.uc.root)
                    pop.resizable(False, False)

                    confirm_label = Label(pop, text='Would you like to overwrite the existing file?')
                    confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

                    no_button = tk.Button(pop, text='No', width='10', command=pop.destroy)
                    no_button.grid(row=2, column=0, sticky='e', padx=5)

                    yes_button = tk.Button(pop, text='Yes', width='10', command=confirm_write)
                    yes_button.grid(row=2, column=1, sticky='w', padx=5)
                else:
                    shutil.make_archive(driver_name, 'zip', self.uc.temp_dir + '/driver')
                    base = os.path.splitext(self.uc.cur_dir + driver_name + '.zip')[0]
                    os.rename(self.uc.cur_dir + driver_name + '.zip', base + '.c4z')

            os.remove(self.uc.temp_dir + '/driver/driver.xml')
            os.rename(self.uc.temp_dir + '/driver/driver.xml.bak', self.uc.temp_dir + '/driver/driver.xml')

        def get_version_number(self):
            if not os.path.isdir(self.uc.temp_dir + '/driver/driver.xml'):
                return
            os.rename(self.uc.temp_dir + '/driver/driver.xml', self.uc.temp_dir + '/driver/driver.txt')
            driver_xml_file = open(self.uc.temp_dir + '/driver/driver.txt', errors='ignore')
            driver_xml_lines = driver_xml_file.readlines()
            driver_xml_file.close()

            for line in driver_xml_lines:
                if '<version>' in line:
                    result = re.search('<version>(.*)</version>', line)
                    os.rename(self.uc.temp_dir + '/driver/driver.txt', self.uc.temp_dir + '/driver/driver.xml')
                    return result.group(1)

            os.rename(self.uc.temp_dir + '/driver/driver.txt', self.uc.temp_dir + '/driver/driver.xml')

    class ConnectionsPanel:
        def __init__(self, upper_class):
            self.x = 30
            self.y = 257
            self.uc = upper_class
            self.connection_entries = []
            self.connection_menus = []
            self.connection_types = []
            self.buttons = []

            x_spacing = 300
            y_spacing = 40
            for x in range(0, 3):
                for i in range(0, 6):
                    # Entries
                    self.connection_entries.append(tk.Entry(self.uc.root, width=20))
                    self.connection_entries[-1].insert(0, 'Connection Name...')
                    self.connection_entries[-1].place(x=(x * x_spacing) + self.x, y=(i * y_spacing) + 20 + self.y,
                                                      anchor='w')
                    self.connection_entries[-1]['state'] = DISABLED

                    # Dropdowns
                    self.connection_types.append(StringVar(self.uc.root))
                    self.connection_types[-1].set('HDMI IN')
                    self.connection_menus.append(OptionMenu(self.uc.root, self.connection_types[-1], 'HDMI IN',
                                                            'HDMI OUT', 'COMPOSITE IN', 'COMPOSITE OUT', 'VGA IN',
                                                            'VGA OUT', 'COMPONENT IN', 'COMPONENT OUT', 'DVI IN',
                                                            'DVI OUT', 'STEREO IN', 'STEREO OUT', 'DIGITAL_OPTICAL IN',
                                                            'DIGITAL_OPTICAL OUT', 'IR_OUT'))
                    self.connection_menus[-1].place(x=(x * x_spacing) + 120 + self.x, y=(i * y_spacing) + 20 + self.y,
                                                    anchor='w')
                    self.connection_menus[-1]['state'] = DISABLED

                    # Buttons
                    self.buttons.append(tk.Button(self.uc.root, text='Add', width=4, command=self.enable_conn))
                    self.buttons[-1].place(x=(x * x_spacing) + 220 + self.x, y=(i * y_spacing) + 20 + self.y,
                                           anchor='w')
                    self.buttons[-1]['state'] = DISABLED

        def enable_conn(self):
            for i in range(len(self.buttons)):
                if self.buttons[i]['state'] == NORMAL and self.connection_entries[i]['state'] == DISABLED:
                    self.connection_entries[i]['state'] = NORMAL
                    self.connection_entries[i].delete(0, END)
                    self.connection_entries[i].insert(0, 'Connection ' + str(i + 1))
                    self.connection_menus[i]['state'] = NORMAL
                    self.buttons[i].place(x=-10000, y=-10000)
                    if i != len(self.connection_entries) - 1:
                        self.buttons[i + 1]['state'] = NORMAL
                    break

        def reinit(self):
            x_spacing = 300
            y_spacing = 40
            for x in range(0, 3):
                for i in range(0, 6):
                    # Entries
                    self.connection_entries[6 * x + i].delete(0, END)
                    self.connection_entries[6 * x + i].insert(0, 'Connection Name...')
                    self.connection_entries[6 * x + i]['state'] = DISABLED

                    # Dropdowns
                    self.connection_types[6 * x + i].set('HDMI IN')
                    self.connection_menus[6 * x + i]['state'] = DISABLED

                    # Buttons
                    self.buttons[6 * x + i].place(x=(x * x_spacing) + 220 + self.x, y=(i * y_spacing) + 20 + self.y,
                                                  anchor='w')
                    self.buttons[6 * x + i]['state'] = DISABLED

    def __init__(self):
        # Create root window
        self.root = tk.Tk()

        # Root window properties
        self.root.geometry('915x250')
        self.root.title('C4 Icon Swapper')
        self.root.resizable(False, False)

        # Creating temporary directory
        self.cur_dir = os.getcwd() + '/'
        self.temp_dir = self.cur_dir + 'temp' + str(random.randint(1111111, 9999999)) + '/'
        if not os.path.isdir(self.temp_dir):
            os.mkdir(self.temp_dir)

        # Class variables
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
        temp_image_file = self.temp_dir + 'blank_img.gif'
        blank_img_file = open(temp_image_file, 'wb')
        blank_img_file.write(base64.b64decode(blank_img_b64))
        blank_img_file.close()
        blank_image = Image.open(temp_image_file)
        blank = blank_image.resize((128, 128), Image.ANTIALIAS)
        self.blank = ImageTk.PhotoImage(blank)
        blank_image.close()
        os.remove(temp_image_file)

        self.c4z_panel = self.C4zPanel(self)
        self.replacement_panel = self.ReplacementPanel(self)
        self.export_panel = self.ExportPanel(self)
        self.connections_panel = self.ConnectionsPanel(self)

        # Separators
        self.separator0 = ttk.Separator(self.root, orient='vertical')
        self.separator0.place(x=305, y=0, height=250)
        self.separator1 = ttk.Separator(self.root, orient='vertical')
        self.separator1.place(x=610, y=0, height=250)
        self.separator2 = ttk.Separator(self.root, orient='horizontal')
        self.separator2.place(x=0, y=250, relwidth=1)

        # Version Label
        self.version_label = Label(self.root, text=version)
        self.version_label.place(relx=1, rely=1.01, anchor='se')

        # Creating window icon
        temp_icon_file = self.temp_dir + 'icon.ico'
        icon_file = open(temp_icon_file, 'wb')
        icon_file.write(base64.b64decode(win_icon))
        icon_file.close()
        self.root.wm_iconbitmap(temp_icon_file)
        os.remove(temp_icon_file)

        # Main Loop
        self.root.after(0, self.restore_entry_text)
        self.root.after(100, self.supervisor)
        self.root.mainloop()
        shutil.rmtree(self.temp_dir)

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

    def supervisor(self):
        self.root.after(100, self.supervisor)
