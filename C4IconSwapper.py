import filecmp
import os
import shutil
import base64
import time
import random
import re
import tkinter as tk
import PIL.Image
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import ImageTk, Image
from datetime import datetime
from Base64Assets import *

version = '4.7a'


class C4IconSwapper:
    class C4zPanel:
        class Icon:
            def __init__(self, root_path: str, path: str, name: str, size: int):
                self.root = root_path
                self.path = path
                self.name = name
                self.size = size

                for i in reversed(range(len(path))):
                    if path[i] != '.':
                        self.type = path[i: len(path)]
                        break

        class IconGroup:
            def __init__(self, icons: list):
                self.name = icons[0].name
                self.path = icons[0].path
                self.icons = icons

        def __init__(self, upper_class):
            self.x = 5
            self.y = 0
            self.uc = upper_class
            self.current_icon = 0
            self.icon_groups = []
            self.valid_connections = ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI', 'STEREO', 'DIGITAL_OPTICAL',
                                      'IR_OUT']

            # Labels
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
            self.open_file_button = tk.Button(self.uc.root, text='Open', width=10, command=self.upload_c4z)
            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

            self.restore_button = tk.Button(self.uc.root, text='Restore\nOriginal Icon', command=self.restore_icon)
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
            self.gen_driver_button.place(x=228 + self.x, y=219 + self.y, anchor='n')

            # Entry
            self.file_entry_field = tk.Entry(self.uc.root, width=25)
            self.file_entry_field.insert(0, 'Select .c4z file...')
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field['state'] = DISABLED
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_c4z)

        def load_gen_driver(self):
            temp_gen_driver = self.uc.temp_dir + 'generic.c4z'
            if self.file_entry_field.get() == temp_gen_driver:
                return
            with open(temp_gen_driver, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_driver))
            self.upload_c4z(temp_gen_driver)
            self.gen_driver_button['state'] = DISABLED
            self.uc.export_panel.over_orig_check['state'] = DISABLED

        def update_icon(self):
            if len(self.icon_groups) == 0:
                return
            if abs(self.current_icon) >= len(self.icon_groups):
                self.current_icon = abs(self.current_icon) % len(self.icon_groups)
            icon_image = Image.open(self.icon_groups[self.current_icon].path)
            icon = icon_image.resize((128, 128), Image.ANTIALIAS)
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label.configure(image=icon)
            self.blank_image_label.image = icon

            self.icon_label.config(text='icon: ' + str(self.current_icon + 1) + ' of ' + str(len(self.icon_groups)))
            self.icon_name_label.config(text='name: ' + self.icon_groups[self.current_icon].name)

        def blank_icon(self):
            self.blank_image_label.configure(image=self.uc.blank)
            self.blank_image_label.image = self.uc.blank
            self.icon_label.config(text='icon: 0 of 0')
            self.icon_name_label.config(text='name:')
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
            self.uc.replacement_panel.prev_icon_button['state'] = DISABLED
            self.uc.replacement_panel.next_icon_button['state'] = DISABLED

        def upload_c4z(self, given_path=''):
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
            temp_bak = '/bak' + str(random.randint(11111111, 99999999)) + '/'
            if len(self.icon_groups) != 0:
                icons_groups_bak = self.icon_groups
                if os.path.isdir(self.uc.temp_dir + 'driver'):
                    shutil.copytree(self.uc.temp_dir + 'driver', self.uc.temp_dir + temp_bak)
            else:
                icons_groups_bak = None

            if given_path == '':
                filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])
            else:
                filename = given_path

            if not filename:
                if os.path.isdir(self.uc.temp_dir + temp_bak):
                    shutil.rmtree(self.uc.temp_dir + temp_bak)
                return

            self.uc.driver_selected = False
            if os.path.isdir(self.uc.temp_dir + '/driver/'):
                shutil.rmtree(self.uc.temp_dir + '/driver/')

            shutil.unpack_archive(filename, self.uc.temp_dir + 'driver', 'zip')

            with open(self.uc.temp_dir + '/driver/driver.xml', errors='ignore') as driver_xml_file:
                driver_xml_lines = driver_xml_file.readlines()
            for line in driver_xml_lines:
                if '<id>' not in line:
                    continue
                result = re.search('<id>(.*)</id>', line)
                try:
                    if int(result.group(1)) not in self.uc.connections_panel.ids:
                        self.uc.connections_panel.ids.append(int(result.group(1)))
                except ValueError:
                    pass

            def get_icons(directory):
                icons_out = []
                if not os.path.isdir(directory):
                    return
                path_list = os.listdir(directory)
                sub_list = []
                for string in path_list:
                    if '.bak' in string or '.orig' in string:
                        continue
                    if '.' not in string:
                        if 'original_icons' in string or 'old' in string:
                            continue
                        sub_list.append(string)
                        continue
                    if 'device_lg' in string:
                        icon_objects.append(self.Icon(directory, directory + '/' + string, 'device', 32))
                        continue
                    elif 'device_sm' in string:
                        icon_objects.append(self.Icon(directory, directory + '/' + string, 'device', 16))
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
                    icons_out.append(self.Icon(directory, directory + '/' + string, temp_name, int(temp_size)))

                if len(sub_list) == 0:
                    return icons_out
                for sub_dir in sub_list:
                    to_add = get_icons(directory + '/' + sub_dir)
                    for icon_path in to_add:
                        icons_out.append(icon_path)
                return icons_out

            icon_objects = []
            try:
                for icon in get_icons(self.uc.icon_dir):
                    icon_objects.append(icon)
            except TypeError:
                pass

            # Form icon groups
            self.icon_groups = []
            temp_list = []
            for icon in icon_objects:
                if not temp_list or (icon.name == temp_list[0].name and icon.root == temp_list[0].root):
                    temp_list.append(icon)
                    continue
                else:
                    self.icon_groups.append(self.IconGroup(temp_list))
                    temp_list = [icon]
                    continue

            if len(temp_list) != 0:
                self.icon_groups.append(self.IconGroup(temp_list))

            # Update entry fields
            if len(self.icon_groups) == 0:
                self.file_entry_field['state'] = NORMAL
                if self.file_entry_field.get() != 'Select .c4z file...' and \
                        self.file_entry_field.get() != 'Invalid driver selected...':
                    self.icon_groups = icons_groups_bak
                    self.uc.schedule_entry_restore = True
                    self.uc.restore_entry_string = self.file_entry_field.get()
                    if os.path.isdir(self.uc.temp_dir + '/driver/'):
                        shutil.rmtree(self.uc.temp_dir + '/driver/')
                    shutil.copytree(self.uc.temp_dir + temp_bak, self.uc.temp_dir + '/driver/')
                    if os.path.isdir(self.uc.temp_dir + temp_bak):
                        shutil.rmtree(self.uc.temp_dir + temp_bak)
                    self.uc.driver_selected = True
                self.file_entry_field.delete(0, 'end')
                self.file_entry_field.insert(0, 'Invalid driver selected...')
                self.file_entry_field['state'] = DISABLED
                return

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
            if orig_driver_name != 'generic':
                self.uc.export_panel.driver_name_entry.delete(0, 'end')
                self.uc.export_panel.driver_name_entry.insert(0, orig_driver_name)
            self.uc.driver_selected = True
            self.update_icon()

            # Update button statuses
            if not self.file_entry_field.get().endswith('generic.c4z') and not\
                    self.file_entry_field.get() == 'Invalid driver selected...':
                self.gen_driver_button['state'] = ACTIVE
                self.uc.export_panel.over_orig_check['state'] = NORMAL

            if len(self.icon_groups) <= 1:
                self.prev_icon_button['state'] = DISABLED
                self.next_icon_button['state'] = DISABLED
            else:
                self.prev_icon_button['state'] = ACTIVE
                self.next_icon_button['state'] = ACTIVE

            if self.uc.replacement_selected and self.uc.driver_selected:
                self.uc.replacement_panel.replace_button['state'] = ACTIVE
                self.uc.replacement_panel.replace_all_button['state'] = ACTIVE
            else:
                self.uc.replacement_panel.replace_button['state'] = DISABLED
                self.uc.replacement_panel.replace_all_button['state'] = DISABLED
            if self.uc.driver_selected:
                self.uc.export_panel.export_button['state'] = ACTIVE

            done = False
            self.restore_all_button['state'] = DISABLED
            for path in list_all_sub_directories(self.uc.temp_dir + '/driver/'):
                files = os.listdir(path)
                for file in files:
                    if ('.bak' in file or '.orig' in file) and '.xml' not in file:
                        self.restore_all_button['state'] = ACTIVE
                        done = True
                        break
                if done:
                    break

            if os.path.isfile(self.icon_groups[self.current_icon].path + '.bak') or \
                    os.path.isfile(self.icon_groups[self.current_icon].path + '.orig'):
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
            elif 0 > index > len(self.icon_groups):
                return print('icon restore index out of range')

            for icon in self.icon_groups[index].icons:
                if os.path.isfile(icon.path + '.bak'):
                    shutil.copy(icon.path + '.bak', icon.path)
                    os.remove(icon.path + '.bak')
                elif os.path.isfile(icon.path + '.orig'):
                    shutil.copy(icon.path + '.orig', icon.path)
                    os.remove(icon.path + '.orig')
            self.restore_button['state'] = DISABLED
            disable_all_button = True
            for group in self.icon_groups:
                if os.path.isfile(group.icons[0].path + '.bak') or os.path.isfile(group.icons[0].path + '.orig'):
                    disable_all_button = False
                    break
            if disable_all_button:
                self.restore_all_button['state'] = DISABLED
            self.update_icon()

        def restore_all(self):
            for i in range(len(self.icon_groups)):
                self.restore_icon(index=i)
            self.restore_button['state'] = DISABLED
            self.restore_all_button['state'] = DISABLED
            self.update_icon()

        def prev_icon(self):
            if not self.uc.driver_selected:
                return
            if self.current_icon - 1 < 0:
                self.current_icon = self.current_icon - 1 + len(self.icon_groups)
            else:
                self.current_icon -= 1

            if os.path.isfile(self.icon_groups[self.current_icon].path + '.bak') or \
                    os.path.isfile(self.icon_groups[self.current_icon].path + '.orig'):
                self.restore_button['state'] = ACTIVE
            else:
                self.restore_button['state'] = DISABLED

            self.update_icon()

        def next_icon(self):
            if not self.uc.driver_selected:
                return
            if self.current_icon + 1 >= len(self.icon_groups):
                self.current_icon = self.current_icon + 1 - len(self.icon_groups)
            else:
                self.current_icon += 1

            if os.path.isfile(self.icon_groups[self.current_icon].path + '.bak') or \
                    os.path.isfile(self.icon_groups[self.current_icon].path + '.orig'):
                self.restore_button['state'] = ACTIVE
            else:
                self.restore_button['state'] = DISABLED

            self.update_icon()

        def get_connections(self):
            if not os.path.isfile(self.uc.temp_dir + '/driver/driver.xml') or not self.uc.driver_selected:
                return
            self.uc.connections_panel.reinit()

            with open(self.uc.temp_dir + '/driver/driver.xml', errors='ignore') as driver_xml_file:
                driver_xml_lines = driver_xml_file.readlines()

            in_connection = False
            name_found = False
            connections = []
            conn_name = ''
            conn_id = 0
            # Get connections from xml
            for line in driver_xml_lines:
                if '<connection>' in line:
                    in_connection = True
                    continue
                if not in_connection:
                    continue
                if '</connection>' in line:
                    in_connection = False
                    name_found = False
                    continue
                if '<id>' in line:
                    conn_id = re.search('<id>(.*)</id>', line).group(1)
                if not name_found and '<connectionname>' in line:
                    conn_name = re.search('<connectionname>(.*)</connectionname>', line).group(1)
                    name_found = True
                elif name_found and '<classname>' in line:
                    connections.append([conn_name, re.search('<classname>(.*)</classname>', line).group(1), conn_id])

            pop_list = []
            # Filter connections through valid connections
            for i in range(len(connections)):
                if connections[i][1] not in self.valid_connections:
                    pop_list.insert(0, i)
            for index in pop_list:
                connections.pop(index)

            # Check that number of connections does not exceed maximum
            if len(connections) > len(self.uc.connections_panel.connections):
                conn_range = len(self.uc.connections_panel.connections) - 1
            elif len(connections) == 0:
                self.uc.connections_panel.connections[0].add_button['state'] = NORMAL
                return
            else:
                conn_range = len(connections) - 1

            self.uc.connections_panel.connections[conn_range].add_button['state'] = NORMAL
            for i in range(conn_range):
                self.uc.connections_panel.connections[i].add_button.place(x=-420, y=-420)
                self.uc.connections_panel.connections[i].name_entry['state'] = NORMAL
                self.uc.connections_panel.connections[i].name_entry.delete(0, END)
                self.uc.connections_panel.connections[i].name_entry.insert(0, connections[i][0])
                self.uc.connections_panel.connections[i].name_entry['state'] = DISABLED
                self.uc.connections_panel.connections[i].type_menu['state'] = DISABLED
                self.uc.connections_panel.connections[i].type.set(connections[i][1])
                self.uc.connections_panel.connections[i].id = connections[i][2]
                self.uc.connections_panel.connections[i].original = True
            for conn in self.uc.connections_panel:
                conn.update_id()

        def drop_in_c4z(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            if dropped_path.endswith('.c4z'):
                self.upload_c4z(given_path=dropped_path)
                return
            elif not self.uc.driver_selected:
                return
            if dropped_path.endswith('.png') or dropped_path.endswith('.jpg') or \
                    dropped_path.endswith('.gif') or dropped_path.endswith('.jpeg'):
                self.uc.replacement_panel.replace_icon(given_path=dropped_path)

    class ReplacementPanel:
        def __init__(self, upper_class):
            self.x = 303
            self.y = 0
            self.uc = upper_class
            self.img_stack = []
            self.stack_labels = []

            # Labels
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
            self.open_file_button = tk.Button(self.uc.root, text='Open', width=10, command=self.upload_replacement)
            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

            self.replace_all_button = tk.Button(self.uc.root, text='Replace All', command=self.replace_all)
            self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.replace_all_button['state'] = DISABLED

            self.replace_button = tk.Button(self.uc.root, text='Replace\nCurrent Icon', command=self.replace_icon)
            self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.replace_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.uc.root, text='Prev', command=self.dec_img_stack, width=5)
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.uc.root, text='Next', command=self.inc_img_stack, width=5)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
            self.next_icon_button['state'] = DISABLED

            # Entry
            self.file_entry_field = tk.Entry(self.uc.root, width=25)
            self.file_entry_field.insert(0, 'Select image file...')
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field['state'] = DISABLED
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_replacement)

        def upload_replacement(self, give_path=''):
            if give_path == '':
                filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"),
                                                                 ("Image", "*.gif"), ("Image", "*.jpeg")])
            else:
                filename = give_path

            if not filename:
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
            icon = icon_image.resize((128, 128), Image.ANTIALIAS)
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
                icon = icon_image.resize((60, 60), Image.ANTIALIAS)
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
            elif 0 > index > len(self.uc.c4z_panel.icon_groups):
                return print('icon replace index out of range')

            if given_path == '':
                replacement_icon = Image.open(self.uc.replacement_image_path)
            else:
                replacement_icon = Image.open(given_path)
            for icon in self.uc.c4z_panel.icon_groups[index].icons:
                if not os.path.isfile(icon.path + '.bak'):
                    shutil.copy(icon.path, icon.path + '.bak')
                new_icon = replacement_icon.resize((icon.size, icon.size))
                new_icon.save(icon.path)
            self.uc.c4z_panel.restore_button['state'] = ACTIVE
            self.uc.c4z_panel.restore_all_button['state'] = ACTIVE
            self.uc.c4z_panel.update_icon()

        def replace_all(self):
            for i in range(len(self.uc.c4z_panel.icon_groups)):
                self.replace_icon(index=i)

        def drop_in_replacement(self, event):
            img_path = event.data.replace('{', '').replace('}', '')
            if not img_path.endswith('.png') and not img_path.endswith('.jpg') and not img_path.endswith('.gif') and \
                    not img_path.endswith('.jpeg'):
                return
            self.upload_replacement(give_path=img_path)

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
                self.upload_replacement(give_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(give_path=self.img_stack[0])
                temp = self.img_stack[0]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(0)
                self.img_stack.insert(0, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(give_path=self.img_stack[0])

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
                self.upload_replacement(give_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(give_path=self.img_stack[1])
                temp = self.img_stack[1]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(1)
                self.img_stack.insert(1, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(give_path=self.img_stack[1])

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
                self.upload_replacement(give_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(give_path=self.img_stack[2])
                temp = self.img_stack[2]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(2)
                self.img_stack.insert(2, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(give_path=self.img_stack[2])

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
                self.upload_replacement(give_path=self.img_stack[-1])
                return
            if len(self.img_stack) > 4 and replacement_index > 3:
                self.upload_replacement(give_path=self.img_stack[3])
                temp = self.img_stack[3]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(3)
                self.img_stack.insert(3, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return
            self.upload_replacement(give_path=self.img_stack[3])

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
            self.x = 615
            self.y = -25
            self.uc = upper_class

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
            self.inc_driver_check = Checkbutton(self.uc.root, text='update driver version',
                                                variable=self.inc_driver_version)
            self.inc_driver_check.place(x=63 + self.x, y=135 + self.y, anchor='w')

            self.over_orig = IntVar()
            self.over_orig_check = Checkbutton(self.uc.root, text='overwrite original file', variable=self.over_orig)
            self.over_orig_check.place(x=63 + self.x, y=115 + self.y, anchor='w')

            self.remove_backups = IntVar()
            self.remove_backups_check = Checkbutton(self.uc.root, text='remove backup files',
                                                    variable=self.remove_backups)
            self.remove_backups_check.place(x=63 + self.x, y=95 + self.y, anchor='w')

        def export_c4z(self):
            def append_line(array: list, string: str):
                encoded_str = string.encode("ascii", "ignore")
                decoded_str = encoded_str.decode()
                array.append(decoded_str)

            def confirm_overwrite():
                if os.path.isfile(self.uc.cur_dir + driver_name + '.c4z'):
                    os.remove(self.uc.cur_dir + driver_name + '.c4z')
                if os.path.isfile(self.uc.cur_dir + driver_name + '.zip'):
                    os.remove(self.uc.cur_dir + driver_name + '.zip')
                shutil.make_archive(driver_name, 'zip', self.uc.temp_dir + '/driver')
                base_path = os.path.splitext(self.uc.cur_dir + driver_name + '.zip')[0]
                os.rename(self.uc.cur_dir + driver_name + '.zip', base_path + '.c4z')

                pop_up.destroy()

            for conn in self.uc.connections_panel.connections:
                conn.update_id(refresh=True)

            driver_name = self.driver_name_entry.get()
            temp = ''
            for letter in driver_name:
                if str(letter).isalnum() or str(letter) == '_' or str(letter) == '-' or str(letter) == ' ':
                    temp += str(letter)
            driver_name = temp
            self.driver_name_entry.delete(0, 'end')
            self.driver_name_entry.insert(0, driver_name)

            with open(self.uc.temp_dir + '/driver/driver.xml', errors='ignore') as driver_xml_file:
                driver_xml_lines = driver_xml_file.readlines()

            modified_xml_lines = []
            if self.inc_driver_version.get():
                for line in driver_xml_lines:
                    if '<version>' in line:
                        result = re.search('<version>(.*)</version>', line)
                        result_int = int(result.group(1))
                        result_int += 1
                        line = line.replace(result.group(1), str(result_int))
                    append_line(modified_xml_lines, line)

                with open(self.uc.temp_dir + '/driver/driver.xml', 'w', errors='ignore') as driver_xml_file:
                    driver_xml_file.writelines(modified_xml_lines)
                shutil.copy(self.uc.temp_dir + '/driver/driver.xml', self.uc.temp_dir + '/driver/driver.xml.bak')

            if modified_xml_lines:
                driver_xml_lines = modified_xml_lines
                modified_xml_lines = []
            else:
                with open(self.uc.temp_dir + '/driver/driver.xml', errors='ignore') as driver_xml_file:
                    driver_xml_lines = driver_xml_file.readlines()
            do_name_swap = True
            update_modified_date = True
            replace_creator = True
            replace_manufacturer = True
            creator = 'C4IconSwapper'
            manufacturer = 'C4IconSwapper'
            proxy_step2 = False
            icon_step2 = False
            old_driver_name = ''
            old_icon_path = ''
            insert_connections = True
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
                        for character in line:
                            if not temp_step2:
                                if len(temp_str) < 6:
                                    temp_str += character
                                else:
                                    temp_str = temp_str[1:len(temp_str)]
                                    temp_str += character
                            else:
                                if character != '"':
                                    old_driver_name += character
                                else:
                                    break
                            if temp_str == 'name="':
                                temp_step2 = True
                        line = line.replace(old_driver_name, driver_name)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                        proxy_step2 = True
                    elif 'name="' + old_driver_name + '"' in line:
                        line = line.replace('name="' + old_driver_name + '"', 'name="' + driver_name + '"')
                        append_line(modified_xml_lines, line)
                        printed_line = True
                elif '<Icon' in line:
                    result = re.search('driver/(.*)/icons', line)
                    if not icon_step2 and result:
                        old_icon_path = result.group(1)
                        line = line.replace(old_icon_path, driver_name)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                    elif old_icon_path in line:
                        line = line.replace(old_icon_path, driver_name)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                elif '<creator>' in line and replace_creator:
                    result = re.search('<creator>(.*)</creator>', line)
                    if result:
                        line = line.replace(result.group(1), creator)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                elif '<manufacturer>' in line and replace_manufacturer:
                    result = re.search('<manufacturer>(.*)</manufacturer>', line)
                    if result:
                        line = line.replace(result.group(1), manufacturer)
                        append_line(modified_xml_lines, line)
                        printed_line = True
                elif '</connections>' in line and insert_connections:
                    insert_connections = False
                    for conn in reversed(self.uc.connections_panel.connections):
                        if conn.original or conn.name_entry['state'] == DISABLED:
                            continue
                        modified_xml_lines.append('\t\t<connection>\n')
                        conn_type = conn.type.get()
                        value = self.uc.conn_dict[conn_type]
                        modified_xml_lines.append('\t\t\t<id>' + str(conn.id) + '</id>\n')
                        value = value.replace('REPLACE', conn.name_entry.get())
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

            with open(self.uc.temp_dir + '/driver/driver.xml', 'w', errors='ignore') as driver_xml_file:
                driver_xml_file.writelines(modified_xml_lines)

            bak_files = []
            temp_temp_dir = self.uc.cur_dir + '/temp_bak_files/'
            if self.remove_backups.get() == 1:
                if not os.path.isdir(temp_temp_dir):
                    os.mkdir(temp_temp_dir)
                directories = list_all_sub_directories(self.uc.temp_dir)
                for directory in directories:
                    files = os.listdir(directory)
                    for file in files:
                        if '.bak' in file or '.orig' in file:
                            bak_files.append([directory, file, str(random.randint(1111111111, 9999999999)) + '.bak'])
                for file_list in bak_files:
                    shutil.copy(file_list[0] + '/' + file_list[1], temp_temp_dir + '/' + file_list[2])
                    os.remove(file_list[0] + '/' + file_list[1])

            if self.over_orig.get() == 1:
                temp_name = 'IcnSwp'
                for _ in range(0, 6):
                    temp_name += str(random.randint(0, 9))
                try:
                    if not os.path.isfile(self.uc.orig_file_path + '.bak'):
                        shutil.copy(self.uc.orig_file_path, self.uc.orig_file_path + '.bak')
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
                    pop_up = Toplevel(self.uc.root)
                    pop_up.title('Cannot Overwrite Original File')
                    pop_up.geometry('239x95')
                    pop_up.grab_set()
                    pop_up.transient(self.uc.root)
                    pop_up.resizable(False, False)

                    label_text = 'Access Denied to: ' + self.uc.orig_file_dir
                    access_label = Label(pop_up, text=label_text)
                    access_label.grid(row=0, column=0, columnspan=2, sticky='w')
                    pop_up.update()
                    if 240 <= access_label.winfo_width():
                        new_size = str(access_label.winfo_width()) + 'x95'
                        pop_up.geometry(new_size)
                        pop_up.update()

                    write_label = Label(pop_up, text='Export to Current Directory Instead?')
                    write_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=10)

                    no_button = tk.Button(pop_up, text='No', width='10', command=pop_up.destroy)
                    no_button.grid(row=2, column=0, sticky='w', padx=5)

                    yes_button = tk.Button(pop_up, text='Yes', width='10', command=confirm_overwrite)
                    yes_button.grid(row=2, column=0, sticky='w', padx=90)
            else:
                if os.path.isfile(self.uc.cur_dir + driver_name + '.c4z') or \
                        os.path.isfile(self.uc.cur_dir + driver_name + '.zip'):
                    pop_up = Toplevel(self.uc.root)
                    pop_up.title('Overwrite')
                    pop_up.geometry('239x70')
                    pop_up.grab_set()
                    pop_up.transient(self.uc.root)
                    pop_up.resizable(False, False)

                    confirm_label = Label(pop_up, text='Would you like to overwrite the existing file?')
                    confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

                    no_button = tk.Button(pop_up, text='No', width='10', command=pop_up.destroy)
                    no_button.grid(row=2, column=0, sticky='e', padx=5)

                    yes_button = tk.Button(pop_up, text='Yes', width='10', command=confirm_overwrite)
                    yes_button.grid(row=2, column=1, sticky='w', padx=5)
                else:
                    shutil.make_archive(driver_name, 'zip', self.uc.temp_dir + '/driver')
                    base = os.path.splitext(self.uc.cur_dir + driver_name + '.zip')[0]
                    os.rename(self.uc.cur_dir + driver_name + '.zip', base + '.c4z')

            if len(bak_files) != 0 and os.path.isdir(temp_temp_dir):
                for file_list in bak_files:
                    shutil.copy(temp_temp_dir + '/' + file_list[2], file_list[0] + '/' + file_list[1])
                shutil.rmtree(temp_temp_dir)
            os.remove(self.uc.temp_dir + '/driver/driver.xml')
            os.rename(self.uc.temp_dir + '/driver/driver.xml.bak', self.uc.temp_dir + '/driver/driver.xml')

    class ConnectionsPanel:
        class Connection:
            def __init__(self, upper_class, x_pos: int, y_pos: int, conn_id=0):
                self.uc = upper_class
                self.x = x_pos
                self.y = y_pos
                self.id = conn_id
                self.original = False
                self.in_id_group = False
                self.export = ''

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
                self.add_button = tk.Button(self.uc.root, text='Add', width=3, command=self.enable)
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.add_button['state'] = DISABLED

                self.x_button = tk.Button(self.uc.root, text='x', width=1, command=self.disable)
                self.x_button.place(x=-420, y=-420, anchor='w')
                self.x_button['state'] = DISABLED

            def enable(self):
                self.name_entry['state'] = NORMAL
                self.type_menu['state'] = NORMAL
                self.add_button.place(x=-420, y=-420, anchor='w')
                self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
                self.x_button['state'] = NORMAL
                self.export = 'add'

                self_index = self.uc.connections_panel.connections.index(self)
                if 0 <= self_index < len(self.uc.connections_panel.connections) - 1:
                    self.uc.connections_panel.connections[self_index + 1].add_button['state'] = NORMAL

            def disable(self):
                self.name_entry['state'] = DISABLED
                self.type_menu['state'] = DISABLED
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.x_button.place(x=-420, y=-420, anchor='w')
                self.x_button['state'] = NORMAL
                self.export = ''

            def reinit(self):
                self.export = ''
                self.id = 0

                # Entry
                self.name_entry['state'] = NORMAL
                self.name_entry.delete(0, END)
                self.name_entry.insert(0, 'Connection Name...')
                self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
                self.name_entry['state'] = DISABLED

                # Dropdown
                self.type.set('HDMI IN')
                self.type_menu.place(x=self.x + 160, y=self.y, anchor='w')
                self.type_menu['state'] = DISABLED

                # Buttons
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.add_button['state'] = DISABLED

                self.x_button.place(x=-420, y=-420, anchor='w')
                self.x_button['state'] = DISABLED

            def update_id(self, *args, refresh=False):
                if self.original:
                    for conn in self.uc.connections_panel.connections:
                        if conn.original and conn.id == self.id:
                            self.in_id_group = True
                            break
                    return
                if not refresh and (args[0] != str(self.type) or self.type_menu['state'] == DISABLED):
                    return
                conn_type = self.type.get()
                valid_id = []
                if ' IN' in conn_type:
                    conn_type = conn_type.replace(' IN', '')
                    if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                        valid_id = find_valid_id(2000, self.uc.connections_panel.ids)
                    elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                        valid_id = find_valid_id(4000, self.uc.connections_panel.ids)
                elif ' OUT' in conn_type:
                    conn_type = conn_type.replace(' OUT', '')
                    if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                        valid_id = find_valid_id(1900, self.uc.connections_panel.ids)
                    elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                        valid_id = find_valid_id(3900, self.uc.connections_panel.ids)
                if conn_type == 'IR_OUT':
                    valid_id = find_valid_id(1, self.uc.connections_panel.ids)

                if self.id in self.uc.connections_panel.ids:
                    self.uc.connections_panel.ids.pop(self.uc.connections_panel.ids.index(self.id))
                self.id = valid_id[0]
                self.uc.connections_panel.ids.append(self.id)

        def __init__(self, upper_class):
            self.x = 14
            self.y = 260
            self.uc = upper_class
            self.connections = []
            self.ids = []

            x_spacing = 318
            y_spacing = 40
            for x in range(0, 3):
                for i in range(0, 6):
                    self.connections.append(self.Connection(self.uc, (x * x_spacing) + self.x,
                                                            (i * y_spacing) + 20 + self.y))

        def reinit(self):
            for conn in self.connections:
                conn.reinit()

    def __init__(self):
        # Create root window
        self.root = TkinterDnD.Tk()
        self.root.bind('<KeyRelease>', self.key_release)

        # Root window properties
        self.root.geometry('915x250')
        self.root.title('C4 Icon Swapper')
        self.root.resizable(False, False)

        # Creating temporary directory
        self.cur_dir = os.getcwd() + '/'
        self.temp_dir = self.cur_dir + 'C4IconSwapperTemp' + str(random.randint(111, 999)) + '/'
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
        temp_image_file = self.temp_dir + 'blank.gif'
        with open(temp_image_file, 'wb') as blank_img_file:
            blank_img_file.write(base64.b64decode(blank_img_b64))
        blank_image = Image.open(temp_image_file)
        blank = blank_image.resize((128, 128), Image.ANTIALIAS)
        self.blank = ImageTk.PhotoImage(blank)
        stack_blank = blank_image.resize((60, 60), Image.ANTIALIAS)
        self.stack_blank = ImageTk.PhotoImage(stack_blank)
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

        # Buttons
        self.open_conn_button = tk.Button(self.root, text='Show Connections', width=15,
                                          command=self.open_connections)
        self.open_conn_button.place(x=760, y=220, anchor='n')

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

    def open_connections(self):
        if self.open_conn_button['text'] == 'Show Connections':
            self.open_conn_button['text'] = 'Hide Connections'
            self.root.geometry('915x510')
            return
        self.open_conn_button['text'] = 'Show Connections'
        self.root.geometry('915x250')

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
    return subs


def find_valid_id(id_seed: int, list_of_ids: list, inc_up=True, inc_count=0):
    if id_seed not in list_of_ids:
        return [id_seed, inc_count]
    if inc_up:
        id_seed += 1
        inc_count += 1
        return find_valid_id(id_seed, list_of_ids, inc_count=inc_count)
    else:
        id_seed -= 1
        inc_count += 1
        return find_valid_id(id_seed, list_of_ids, inc_count=inc_count)
