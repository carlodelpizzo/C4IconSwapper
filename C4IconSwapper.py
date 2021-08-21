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

version = '3.1b'

# Root Window
root = tk.Tk()
root.geometry('915x250')
root.title('C4 Icon Swapper')
root.resizable(False, False)
entry_font = 'Helvetica'

# Creating temporary directory
cur_dir = os.getcwd() + '/'
temp_dir = cur_dir + 'temp/'
if not os.path.isdir(temp_dir):
    os.mkdir(temp_dir)

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

shutil.rmtree(temp_dir)

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
        self.open_file_button = tk.Button(root, text='Open', width=10, command=self.upload_c4z)
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

    def upload_c4z(self):
        global driver_selected
        global replacement_selected
        global c4_driver
        global schedule_entry_restore
        global restore_entry_string
        global orig_file_dir
        global orig_file_path

        if self.file_entry_field.get() != 'Select .c4z file...' and \
                self.file_entry_field.get() != 'Invalid driver selected...':
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
                self.file_entry_field['state'] = NORMAL
                self.file_entry_field.delete(0, 'end')
                self.file_entry_field.insert(0, filename)
                self.file_entry_field['state'] = 'readonly'
                orig_file_path = filename
                orig_driver_name = ''
                for i in reversed(range(len(orig_file_path))):
                    if orig_file_path[i] == '/':
                        orig_file_dir = orig_file_path[0:i + 1]
                        break
                    if orig_file_path[i] == '.':
                        orig_driver_name = '.'
                    if orig_driver_name != '':
                        if orig_driver_name == '.':
                            orig_driver_name = orig_file_path[i]
                        else:
                            orig_driver_name = orig_file_path[i] + orig_driver_name
                export_panel.driver_name_entry.delete(0, 'end')
                export_panel.driver_name_entry.insert(0, orig_driver_name)
                driver_selected = True
                self.update_icon()
            else:
                self.file_entry_field['state'] = NORMAL
                if self.file_entry_field.get() != 'Select .c4z file...' and \
                        self.file_entry_field.get() != 'Invalid driver selected...':
                    # noinspection PyUnboundLocalVariable
                    c4_driver = c4_driver_bak
                    schedule_entry_restore = True
                    restore_entry_string = self.file_entry_field.get()
                    preserve_prev_next = True
                    if os.path.isdir(temp_dir + '/driver/'):
                        shutil.rmtree(temp_dir + '/driver/')
                    shutil.copytree(temp_dir + '/bak/', temp_dir + '/driver/')
                self.file_entry_field.delete(0, 'end')
                self.file_entry_field.insert(0, 'Invalid driver selected...')
                self.file_entry_field['state'] = DISABLED

            if not preserve_prev_next:
                if len(c4_driver.icon_groups) <= 1:
                    self.prev_icon_button['state'] = DISABLED
                    self.next_icon_button['state'] = DISABLED
                    replacement_panel.prev_icon_button['state'] = DISABLED
                    replacement_panel.next_icon_button['state'] = DISABLED
                elif len(c4_driver.icon_groups) > 1:
                    self.prev_icon_button['state'] = ACTIVE
                    self.next_icon_button['state'] = ACTIVE
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


class ReplacementPanel:
    def __init__(self):
        self.x = 310
        self.y = 5

        # Labels
        self.blank_image_label = tk.Label(root, image=blank)
        self.blank_image_label.image = blank
        self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

        # Buttons
        self.open_file_button = tk.Button(root, text='Open', width=10, command=self.upload_replacement)
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

    def update_icon(self):
        if replacement_selected:
            icon_image = Image.open(replacement_image_path)
            icon = icon_image.resize((128, 128), Image.ANTIALIAS)
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label = tk.Label(root, image=icon)
            self.blank_image_label.image = icon
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

    def upload_replacement(self):
        global driver_selected
        global replacement_selected

        filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"), ("Image", "*.gif"),
                                                         ("Image", "*.jpeg")])

        if filename:
            shutil.copy(filename, temp_dir + 'replacement_icon.png')

            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, filename)
            self.file_entry_field['state'] = 'readonly'

            if driver_selected:
                self.replace_button['state'] = ACTIVE
                self.replace_all_button['state'] = ACTIVE
            else:
                self.replace_button['state'] = DISABLED
                self.replace_all_button['state'] = DISABLED

            if os.path.isfile(temp_dir + 'replacement_icon.png'):
                replacement_selected = True
                self.update_icon()


class ExportPanel:
    def __init__(self):
        self.x = 615
        self.y = -20

        # Labels
        self.driver_name_label = tk.Label(root, text='Driver Name:')
        self.driver_name_label.place(x=65 + self.x, y=160 + self.y, anchor='w')

        # Buttons
        self.export_button = tk.Button(root, text='Export', width=20, command=self.export_c4z)
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

        if self.modify_xml.get() == 1:
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
                if os.path.isfile(cur_dir + ran_file_name + '.c4z'):
                    os.remove(cur_dir + ran_file_name + '.c4z')
                if os.path.isfile(cur_dir + ran_file_name + '.zip'):
                    os.remove(cur_dir + ran_file_name + '.zip')
                shutil.make_archive(ran_file_name, 'zip', temp_dir + '/driver')
                base_path = os.path.splitext(cur_dir + ran_file_name + '.zip')[0]
                os.rename(cur_dir + ran_file_name + '.zip', base_path + '.c4z')
            else:
                if os.path.isfile(cur_dir + driver_name + '.c4z'):
                    os.remove(cur_dir + driver_name + '.c4z')
                if os.path.isfile(cur_dir + driver_name + '.zip'):
                    os.remove(cur_dir + driver_name + '.zip')
                shutil.make_archive(driver_name, 'zip', temp_dir + '/driver')
                base_path = os.path.splitext(cur_dir + driver_name + '.zip')[0]
                os.rename(cur_dir + driver_name + '.zip', base_path + '.c4z')

            pop.destroy()

        if self.over_orig.get() == 1:
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
                base = os.path.splitext(cur_dir + temp_name + '.zip')[0]
                os.rename(cur_dir + temp_name + '.zip', base + '.c4z')
                os.remove(orig_file_path)
                shutil.copy(base + '.c4z', orig_file_path)
                os.remove(base + '.c4z')
            except IOError as _:
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
            if os.path.isfile(cur_dir + driver_name + '.c4z') or os.path.isfile(
                    cur_dir + driver_name + '.zip'):
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
                base = os.path.splitext(cur_dir + driver_name + '.zip')[0]
                os.rename(cur_dir + driver_name + '.zip', base + '.c4z')


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


c4z_panel = C4zPanel()

separator0 = ttk.Separator(root, orient='vertical')
separator0.place(x=305, y=0, relwidth=0.2, relheight=1)

replacement_panel = ReplacementPanel()

separator1 = ttk.Separator(root, orient='vertical')
separator1.place(x=610, y=0, relwidth=0.2, relheight=1)

export_panel = ExportPanel()

# Version Label
version_label = Label(root, text=version).place(relx=1, rely=1.01, anchor='se')
