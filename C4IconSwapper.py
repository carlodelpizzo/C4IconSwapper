import base64
import contextlib
import filecmp
import itertools
import os
import pickle
import platform
import random
import re
import shutil
import time
from datetime import datetime

from tkinter import Tk, filedialog, Toplevel, Checkbutton, IntVar, StringVar, Label, Menu, OptionMenu
from tkinter import DISABLED, NORMAL, END, INSERT, Button, Entry
from tkinter.ttk import Separator
from PIL import ImageTk, Image

from Base64Assets import *
from XMLObject import XMLObject

if platform.system() == 'Darwin':
    import subprocess
    # noinspection PyUnresolvedReferences
    from AppKit import NSBundle
    on_mac = True
else:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    on_mac = False

version = '1.2.2'

label_font, light_entry_bg, dark_entry_bg = 'Arial', '#FFFFFF', '#282830'
letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
           'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
capital_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                   'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
valid_chars = ['_', '-', ' ', *letters, *capital_letters, *numbers]
conn_template = ['connection', '', '', [['id', '0', '', []], ['type', '0', '', []],
                                        ['connectionname', 'REPLACE', '', []],
                                        ['consumer', 'False', '', []], ['linelevel', 'True', '', []],
                                        ['classes', '', '', [['class', '', '', [['classname', 'REPLACE', '', []]]]]]]]
selectable_connections = ('HDMI IN', 'HDMI OUT', 'COMPOSITE IN', 'COMPOSITE OUT', 'VGA IN', 'VGA OUT', 'COMPONENT IN',
                          'COMPONENT OUT', 'DVI IN', 'DVI OUT', 'STEREO IN', 'STEREO OUT', 'DIGITAL_OPTICAL IN',
                          'DIGITAL_OPTICAL OUT', 'IR_OUT')
valid_connections = {'HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI', 'STEREO', 'DIGITAL_OPTICAL',
                     *selectable_connections}

if on_mac:
    no_dark_mode = None


class C4IconSwapper:
    def __init__(self):
        self.root = Tk() if on_mac else TkinterDnD.Tk()

        def valid_instance_id(instance_ids: list):
            valid_id = str(random.randint(111111, 999999))
            if f'{valid_id}\n' in instance_ids:
                valid_id = valid_instance_id(instance_ids)
            return valid_id

        # Create temporary directory
        self.instance_id = str(random.randint(111111, 999999))
        if on_mac:
            is_dark_mode()
            self.cur_dir = f'{get_path("/tmp")}/'
        else:
            self.cur_dir = f'{os.getcwd()}/'
        self.global_temp = f'{self.cur_dir}C4IconSwapperTemp/'
        self.instance_temp = f'{self.global_temp}{self.instance_id}/'
        self.checked_in, self.recovery_wait, self.recover_instance, checked_in_instances = False, False, '', []
        if os.path.isdir(self.global_temp):
            if os.path.isfile(instance_path := f'{self.global_temp}instance'):
                if on_mac:
                    with open(get_path(instance_path), 'r', errors='ignore') as instance_file:
                        current_instances = instance_file.readlines()
                else:
                    with open(instance_path, 'r', errors='ignore') as instance_file:
                        current_instances = instance_file.readlines()
                if current_instances:
                    if not os.path.isdir(check_in_path := f'{self.global_temp}check_in'):
                        os.mkdir(check_in_path)
                    waiting = True
                    # I'm sure there is a better way to format this timestamp lol
                    begin_time = float(time.mktime(datetime.now().timetuple()))
                    while waiting:
                        checked_in_instances = os.listdir(check_in_path)
                        if len(checked_in_instances) == len(current_instances):
                            waiting = False
                        if float(time.mktime(datetime.now().timetuple())) - begin_time >= 2:
                            waiting = False
                    failed_to_check_in = []
                    for instance_id in current_instances:
                        if instance_id.replace('\n', '') not in checked_in_instances:
                            failed_to_check_in.append(instance_id.replace('\n', ''))

                    # Offer project recovery if applicable
                    if not os.path.isdir(self.global_temp + failed_to_check_in[0]):
                        # Hack to deal with bug cause by crash during recovery
                        failed_to_check_in = []
                    if failed_to_check_in and os.listdir(self.global_temp + failed_to_check_in[0]):
                        def win_close():
                            self.recovery_wait = False
                            recovery_win.destroy()

                        def flag_recovery():
                            self.recover_instance = failed_to_check_in[0]
                            win_close()

                        self.recovery_wait = True
                        recovery_win = Tk()
                        recovery_win.focus()
                        recovery_win.protocol('WM_DELETE_WINDOW', win_close)
                        recovery_win.title('Driver Recovery')
                        recovery_win.geometry('300x100')
                        recovery_win.resizable(False, False)
                        label_text = 'Existing driver found.'
                        recovery_label = Label(recovery_win, text=label_text)
                        recovery_label.pack()
                        label_text = 'Would you like to recover previous driver?'
                        recovery_label2 = Label(recovery_win, text=label_text)
                        recovery_label2.pack()
                        recovery_button = Button(recovery_win, text='Recover Driver', command=flag_recovery)
                        recovery_button.pack()
                        recovery_win.mainloop()

                    while self.recovery_wait:
                        pass

                    for failed_id in failed_to_check_in:
                        if failed_id == self.recover_instance:
                            continue
                        if os.path.isdir(self.global_temp + failed_id):
                            shutil.rmtree(self.global_temp + failed_id)
                    current_instances = []
                    for instance_id in os.listdir(check_in_path):
                        current_instances.append(f'{instance_id}\n')
                    shutil.rmtree(check_in_path)
                if f'{self.instance_id}\n' in current_instances:
                    self.instance_id = valid_instance_id(current_instances)
                current_instances.append(f'{self.instance_id}\n')
                if on_mac:
                    with open(get_path(instance_path), 'w', errors='ignore') as out_file:
                        out_file.writelines(current_instances)
                else:
                    with open(instance_path, 'w', errors='ignore') as out_file:
                        out_file.writelines(current_instances)
                if self.recover_instance and os.path.isdir(self.global_temp + self.recover_instance):
                    os.rename(self.global_temp + self.recover_instance, self.instance_temp)
            else:
                shutil.rmtree(self.global_temp)
                os.mkdir(self.global_temp)
                if on_mac:
                    with open(get_path(instance_path), 'w', errors='ignore') as out_file:
                        out_file.writelines(f'{self.instance_id}\n')
                else:
                    with open(instance_path, 'w', errors='ignore') as out_file:
                        out_file.writelines(f'{self.instance_id}\n')
        else:
            os.mkdir(self.global_temp)
            if on_mac:
                with open(get_path(f'{self.global_temp}instance'), 'w', errors='ignore') as out_file:
                    out_file.writelines(f'{self.instance_id}\n')
            else:
                with open(f'{self.global_temp}instance', 'w', errors='ignore') as out_file:
                    out_file.writelines(f'{self.instance_id}\n')
        if not self.recover_instance:
            os.mkdir(self.instance_temp)

        # Common Directories
        self.device_icon_dir = f'{self.instance_temp}driver/www/icons/device/'
        self.icon_dir = f'{self.instance_temp}driver/www/icons/'
        self.images_dir = f'{self.instance_temp}driver/www/images/'
        self.replacement_image_path = f'{self.instance_temp}replacement_icon.png'

        # Root window properties
        self.root.title(f'C4 Icon Swapper ({self.instance_id})' if checked_in_instances else 'C4 Icon Swapper')

        # Class variables
        self.driver_xml = None
        self.driver_manufac_var = StringVar()
        self.driver_manufac_new_var = StringVar(value='C4IconSwapper')
        self.driver_creator_var = StringVar()
        self.driver_creator_new_var = StringVar(value='C4IconSwapper')
        self.driver_ver_orig = StringVar()
        self.driver_version_var = StringVar()
        self.driver_version_new_var = StringVar(value='1')
        self.multi_state_driver, self.ask_to_save = False, False
        self.counter, self.easter_counter = 0, 0
        self.schedule_entry_restore = False
        self.restore_entry_string = ''
        self.orig_file_dir = ''
        self.taken_conn_ids = []
        self.connections = [Connection(self) for _ in range(18)]
        self.states_orig_names = []
        self.states, self.state_dupes = [State('') for _ in range(13)], []
        self.driver_selected, self.replacement_selected = False, False

        # Creating blank image for panels
        temp_image_file = f'{self.global_temp}blank.gif'
        if on_mac:
            with open(get_path(temp_image_file), 'wb') as blank_img_file:
                blank_img_file.write(base64.b64decode(blank_img_b64))
        else:
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
        self.c4z_panel = C4zPanel(self)
        self.replacement_panel = ReplacementPanel(self)
        self.export_panel = ExportPanel(self)

        # Popup window variables
        self.driver_info_win, self.states_win, self.connections_win = None, None, None

        # Panel Separators
        self.separator0 = Separator(self.root, orient='vertical')
        self.separator0.place(x=350 if on_mac else 305, y=0, height=290 if on_mac else 270)
        self.separator1 = Separator(self.root, orient='vertical')
        self.separator1.place(x=700 if on_mac else 610, y=0, height=290 if on_mac else 270)

        # Version Label
        self.version_label = Label(self.root, text=version)
        self.version_label.place(relx=1, rely=1.01, anchor='se')
        self.version_label.bind('<Button-1>', self.easter)

        # Menus
        self.menu = Menu(self.root)

        # File Menu
        self.file = Menu(self.menu, tearoff=0)
        self.file.add_command(label='Open Project', command=self.load_project)
        self.file.add_command(label='Save Project', command=self.save_project)
        self.file.add_separator()
        self.file.add_command(label='Open C4z', command=self.c4z_panel.load_c4z)
        self.file.add_command(label='Open Replacement Image', command=self.replacement_panel.process_image)
        self.file.add_separator()
        self.file.add_command(label='Load Generic Driver', command=self.c4z_panel.load_gen_driver)
        self.file.add_command(label='Load Multi Driver', command=self.c4z_panel.load_gen_multi)

        # Edit Menu
        self.edit = Menu(self.menu, tearoff=0)
        self.edit.add_command(label='Connections', command=lambda: self.open_edit_win(self.connections_win, 'conn'))
        self.edit.add_command(label='Driver Info', command=lambda: self.open_edit_win(self.driver_info_win, 'driver'))
        self.edit.add_command(label='States', command=lambda: self.open_edit_win(self.states_win, 'states'))
        self.edit.add_separator()
        self.edit.add_command(label='Undo', command=self.undo)
        self.states_pos = 2
        self.edit.entryconfig(self.states_pos, state=DISABLED)
        self.undo_pos = 4
        self.edit.entryconfig(self.undo_pos, state=DISABLED)

        self.menu.add_cascade(label='File', menu=self.file)
        self.menu.add_cascade(label='Edit', menu=self.edit)

        # Create window icon
        if not on_mac:
            temp_icon_file = f'{self.global_temp}icon.ico'
            with open(temp_icon_file, 'wb') as icon_file:
                icon_file.write(base64.b64decode(win_icon))
            self.root.wm_iconbitmap(temp_icon_file)
            os.remove(temp_icon_file)

        # Do recovery if necessary
        if self.recover_instance:
            # Recover Driver
            self.c4z_panel.load_c4z(recovery=True)
            # Recover replacement images; Need to make this more efficient
            first_time = True
            for file in os.listdir(self.instance_temp):
                if is_valid_image(file):
                    if first_time:
                        os.mkdir(f'{self.instance_temp}img_recovery')
                        first_time = False
                    shutil.move(self.instance_temp + file, f'{self.instance_temp}img_recovery/{file}')
            if not first_time:
                multi_images = False
                multi_check = 0
                stack_size = 5 if on_mac else 4
                for file in os.listdir(f'{self.instance_temp}img_recovery'):
                    self.replacement_panel.process_image(file_path=f'{self.instance_temp}img_recovery/{file}')
                    if multi_check > stack_size + 1:
                        multi_images = True
                        continue
                    multi_check += 1
                shutil.rmtree(f'{self.instance_temp}img_recovery')
                self.replacement_panel.file_entry_field['state'] = NORMAL
                self.replacement_panel.file_entry_field.delete(0, END)
                self.replacement_panel.file_entry_field.insert(0, 'Recovered Image')
                self.replacement_panel.file_entry_field['state'] = 'readonly'
                if multi_images:
                    self.replacement_panel.next_icon_button['state'] = NORMAL
                    self.replacement_panel.prev_icon_button['state'] = NORMAL

        # Initialize root window
        if not on_mac:
            self.root.after(150, self.instance_check)  # type: ignore
        else:
            self.dark_mode = is_dark_mode()
            self.wait_to_check = False
            if not no_dark_mode:
                self.root.after(150, self.dark_mode_check)  # type: ignore
        self.root.geometry('1055x267' if on_mac else '915x287')
        self.root.resizable(False, False)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.bind('<Control-s>', self.save_project)
        self.root.bind('<Control-o>', self.load_project)
        self.root.bind('<Control-z>', self.undo)
        self.root.config(menu=self.menu)
        self.root.protocol('WM_DELETE_WINDOW', self.on_program_exit)
        self.root.mainloop()

    def on_key_release(self, event):
        match event.keysym:
            case 'Right':
                self.c4z_panel.next_icon()
            case 'Left':
                self.c4z_panel.prev_icon()
            case 'Up':
                self.replacement_panel.inc_img_stack()
            case 'Down':
                self.replacement_panel.dec_img_stack()
            case 'c':
                if self.easter_counter >= 10:
                    self.version_label.config(text='\u262D', font=('Arial', 25))
                    rel_x, rel_y = (0.9999, 1.01) if on_mac else (1.005, 1.02)
                    self.version_label.place(relx=rel_x, rely=rel_y, anchor='se')
                    self.easter_counter = -1

    def blink_driver_name_entry(self):
        if not self.counter:
            return
        self.counter -= 1
        if on_mac and not no_dark_mode and is_dark_mode():
            self.export_panel.driver_name_entry['background'] = dark_entry_bg \
                if self.export_panel.driver_name_entry['background'] != dark_entry_bg else 'pink'
        elif self.export_panel.driver_name_entry['background'] != light_entry_bg:
            self.export_panel.driver_name_entry['background'] = light_entry_bg
        else:
            self.export_panel.driver_name_entry['background'] = 'pink'
        # noinspection PyTypeChecker
        self.root.after(150, self.blink_driver_name_entry)

    def restore_entry_text(self):
        if self.schedule_entry_restore:
            self.schedule_entry_restore = False
            if self.restore_entry_string:
                self.c4z_panel.file_entry_field['state'] = NORMAL
                self.c4z_panel.file_entry_field.delete(0, 'end')
                self.c4z_panel.file_entry_field.insert(0, self.restore_entry_string)
                self.c4z_panel.file_entry_field['state'] = 'readonly'
                self.restore_entry_string = ''

    def validate_man_and_creator(self, string_var=None, entry=None):
        if not string_var or not entry:
            return
        name = string_var.get()
        name_compare = [char for char in name if char in valid_chars]
        if self.driver_info_win and (str_diff := len(name) - len(name_compare)):
            cursor_pos = entry.index(INSERT)
            entry.icursor(cursor_pos - str_diff)
            string_var.set(''.join(name_compare))

        self.ask_to_save = True

    def validate_driver_ver(self, *_):
        version_str = self.driver_version_new_var.get()
        version_compare = [char for char in version_str.lstrip('0') if char in numbers]

        if self.driver_info_win and (str_diff := len(version_str) - len(version_compare)):
            cursor_pos = self.driver_info_win.driver_ver_new_entry.index(INSERT)
            self.driver_info_win.driver_ver_new_entry.icursor(cursor_pos - str_diff)
            self.driver_version_new_var.set(''.join(version_compare))

        self.ask_to_save = True

    def get_states(self, lua_file):
        self.states_orig_names = []
        find_names = False
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
                            working_name = working_name[:-1]
                            self.states_orig_names.append(working_name)
                            working_name = ''
                            build_name = False
                            continue
                        working_name += character
                        continue
                    working_name += character
                    if len(working_name) > 2:
                        working_name = working_name[1:]
                    if working_name == '{ ':
                        build_name = True
                        working_name = ''
            if 'States, LED = {},' in line or 'States = {}' in line:
                break
        for i, state_name in enumerate(self.states_orig_names):
            if self.states_win:
                self.states_win.state_entries[i].name_entry['state'] = NORMAL
            self.states[i].name_var.set(state_name)
            self.states[i].original_name = state_name

    def open_edit_win(self, window, win_type: str):
        if window:
            window.window.deiconify()
            window.window.focus()
            return
        match win_type:
            case 'conn':
                self.connections_win = ConnectionsWin(self)
            case 'driver':
                self.driver_info_win = DriverInfoWin(self)
            case 'states':
                self.states_win = StatesWin(self)

    def save_project(self, *_):
        out_file = filedialog.asksaveasfile(initialfile=f'{self.export_panel.driver_name_var.get()}.c4is',
                                            filetypes=[('C4IconSwapper Project', '*.c4is')])
        if not out_file:
            return
        if not (out_file_path := out_file.name).endswith('.c4is'):
            out_file.close()
            os.rename(out_file_path, (out_file_path := f'{out_file_path}.c4is'))
        with open(out_file_path, 'wb') as output:
            # noinspection PyTypeChecker
            pickle.dump(C4IS(self), output)
        self.ask_to_save = False

    def load_project(self, *_):
        if filename := filedialog.askopenfilename(filetypes=[('C4IconSwapper Project', '*.c4is')]):
            self.load_c4is(filename)

    def load_c4is(self, file_path: str):
        with open(file_path, 'rb') as file:
            save_state = pickle.load(file)
        if type(save_state) is not C4IS:
            raise TypeError

        # C4z Panel (and export button)
        self.c4z_panel.icons = []
        self.c4z_panel.current_icon = 0
        self.c4z_panel.c4_icon_label.configure(image=self.blank)
        if os.path.isdir(driver_folder := f'{self.instance_temp}driver/'):
            shutil.rmtree(driver_folder)
        self.c4z_panel.restore_button['state'] = DISABLED
        if save_state.driver_selected:
            with open(saved_driver_path := f'{self.instance_temp}saved_driver.c4z', 'wb') as driver_zip:
                driver_zip.write(save_state.driver_zip)
            self.c4z_panel.load_c4z(saved_driver_path)
            os.remove(saved_driver_path)
            self.export_panel.export_button['state'] = NORMAL
            if not on_mac:
                self.export_panel.export_as_button['state'] = NORMAL
            if os.path.isfile(f'{self.c4z_panel.icons[self.c4z_panel.current_icon].path}.bak'):
                self.c4z_panel.restore_button['state'] = NORMAL
        else:
            self.export_panel.export_button['state'] = DISABLED
            if not on_mac:
                self.export_panel.export_as_button['state'] = DISABLED
            self.c4z_panel.icon_name_label.config(text='icon name')
            self.c4z_panel.icon_num_label.config(text='0 of 0')
        self.driver_selected = save_state.driver_selected

        self.c4z_panel.extra_icons = save_state.extra_icons
        self.c4z_panel.show_extra_icons.set(save_state.show_extra_icons)
        self.c4z_panel.restore_all_button['state'] = save_state.c4z_panel['restore_all']
        self.c4z_panel.prev_icon_button['state'] = save_state.c4z_panel['prev']
        self.c4z_panel.next_icon_button['state'] = save_state.c4z_panel['next']

        # Root class
        self.driver_xml = save_state.driver_xml
        self.driver_manufac_var.set(save_state.driver_manufac_var)
        self.driver_manufac_new_var.set(save_state.driver_manufac_new_var)
        self.driver_creator_var.set(save_state.driver_creator_var)
        self.driver_creator_new_var.set(save_state.driver_creator_new_var)
        self.driver_ver_orig.set(save_state.driver_ver_orig)
        self.driver_version_var.set(save_state.driver_version_var)
        self.driver_version_new_var.set(save_state.driver_version_new_var)
        self.multi_state_driver = save_state.multi_state_driver
        self.states_orig_names = save_state.states_orig_names
        self.replacement_selected = save_state.replacement_selected
        if self.multi_state_driver:
            self.edit.entryconfig(self.states_pos, state=NORMAL)
        else:
            self.edit.entryconfig(self.states_pos, state=DISABLED)

        # State Panel
        for i, state in enumerate(save_state.states):
            self.states[i].original_name = state['original_name']
            self.states[i].name_var.set(state['name_var'])

        # Connection Panel
        self.taken_conn_ids = save_state.ids
        for i, conn in enumerate(save_state.connections):
            self.connections[i].id = conn['id']
            self.connections[i].original = conn['original']
            self.connections[i].in_id_group = conn['in_id_group']
            self.connections[i].delete = conn['delete']
            self.connections[i].prior_txt = conn['prior_txt']
            self.connections[i].prior_type = conn['prior_type']
            self.connections[i].tags = conn['tags']
            self.connections[i].id_group = conn['id_group']
            self.connections[i].type.set(conn['type'])
            self.connections[i].name_entry_var.set(conn['name'])
            self.connections[i].enabled = conn['state']

        # Export Panel
        self.export_panel.driver_name_var.set(save_state.driver_name_var)
        self.export_panel.inc_driver_version.set(save_state.inc_driver_version)
        self.export_panel.include_backups.set(save_state.include_backups)

        # Replacement Panel
        if save_state.replacement:
            if os.path.isfile(self.replacement_image_path):
                os.remove(self.replacement_image_path)
            save_state.replacement.save(self.replacement_image_path)
            save_state.replacement.close()
            icon_image = Image.open(self.replacement_image_path)
            icon = icon_image.resize((128, 128))
            icon = ImageTk.PhotoImage(icon)
            self.replacement_panel.replacement_img_label.configure(image=icon)
            self.replacement_panel.replacement_img_label.image = icon
        for img in self.replacement_panel.img_bank:
            os.remove(img)
        self.replacement_panel.img_bank = []
        for stack_label in self.replacement_panel.img_bank_tk_labels:
            stack_label.configure(image=self.stack_blank)
        for img in save_state.img_bank:
            img_path = f'{self.instance_temp}stack{len(self.replacement_panel.img_bank)}.png'
            img.save(img_path)
            img.close()
            self.replacement_panel.img_bank.append(img_path)
        self.replacement_panel.refresh_img_bank()
        self.replacement_panel.replace_button['state'] = save_state.replacement_panel['replace']
        self.replacement_panel.replace_all_button['state'] = save_state.replacement_panel['replace_all']
        self.replacement_panel.prev_icon_button['state'] = save_state.replacement_panel['prev']
        self.replacement_panel.next_icon_button['state'] = save_state.replacement_panel['next']

        self.ask_to_save = False

    def recall_load_gen_multi(self):
        self.c4z_panel.load_gen_multi(show_loading_image=False)

    def undo(self, *_):
        # I'm doing this bootleg af... too lazy to make this efficient
        if not os.path.isfile(file_path := f'{self.instance_temp}undo_history.c4is'):
            return
        current_icon = self.c4z_panel.current_icon
        self.load_c4is(file_path)
        self.c4z_panel.current_icon = current_icon
        self.c4z_panel.update_icon()
        if os.path.isfile(f'{self.c4z_panel.icons[current_icon].path}.bak'):
            self.c4z_panel.restore_button['state'] = NORMAL
        else:
            self.c4z_panel.restore_button['state'] = DISABLED

        os.remove(file_path)
        self.edit.entryconfig(self.undo_pos, state=DISABLED)

    def update_undo_history(self):
        with open(f'{self.instance_temp}undo_history.c4is', 'wb') as output:
            # noinspection PyTypeChecker
            pickle.dump(C4IS(self), output)

        self.edit.entryconfig(self.undo_pos, state=NORMAL)

    if not on_mac:
        def instance_check(self):
            if self.checked_in and not os.path.isdir(f'{self.global_temp}check_in'):
                self.checked_in = False
            elif not self.checked_in and os.path.isdir(f'{self.global_temp}check_in'):
                with open(f'{self.global_temp}check_in/{self.instance_id}', 'w', errors='ignore') as check_in_file:
                    check_in_file.writelines('')
                self.checked_in = True
                self.root.title(f'C4 Icon Swapper ({self.instance_id})')

            # noinspection PyTypeChecker
            self.root.after(150, self.instance_check)
    else:
        def dark_mode_check(self):
            # noinspection PyTypeChecker
            self.root.after(150, self.dark_mode_check)
            if self.wait_to_check or self.dark_mode == (dark_mode_status := is_dark_mode()):
                return
            self.wait_to_check = True
            self.dark_mode = dark_mode_status
            background = dark_entry_bg if self.dark_mode else light_entry_bg
            if self.connections_win:
                for entry in self.connections_win.connections:
                    entry.name_entry['background'] = background
            self.export_panel.driver_name_entry['background'] = background
            for state in self.states:
                if state.bg_color not in ['pink', 'cyan']:
                    state.bg_color = background
            if self.states_win:
                for state_entry in self.states_win.state_entries:
                    state_entry.refresh(bg_only=True)
            self.wait_to_check = False

    def ask_to_save_dialog(self, *return_args, on_exit=True, root_destroy=False, return_to=''):
        def cancel_dialog():
            self.ask_to_save = True
            save_dialog.destroy()

        def exit_save_dialog():
            save_dialog.destroy()
            if root_destroy:
                self.end_program()
            elif return_to == 'generic':
                self.c4z_panel.load_gen_driver()
            elif return_to == 'multi':
                self.c4z_panel.load_gen_multi()
            elif return_to == 'load_c4z':
                if return_args:
                    self.c4z_panel.load_c4z(given_path=return_args[0], recovery=return_args[1])
                    return
                self.c4z_panel.load_c4z()

        def do_project_save():
            self.save_project()
            exit_save_dialog()

        save_dialog = Toplevel(self.root)
        save_dialog.title('Save current project?')
        if on_mac:
            save_dialog.geometry('274x70')
        else:
            save_dialog.geometry('239x70')
        if on_exit and not on_mac:
            win_x = self.root.winfo_rootx() + self.root.winfo_width() - 250
            save_dialog.geometry(f'+{win_x}+{self.root.winfo_rooty()}')
        else:
            save_dialog.geometry(f'+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}')
        save_dialog.protocol('WM_DELETE_WINDOW', cancel_dialog)
        save_dialog.grab_set()
        save_dialog.focus()
        save_dialog.transient(self.root)
        save_dialog.resizable(False, False)

        confirm_label = Label(save_dialog, text='Would you like to save the current project?')
        confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

        yes_button = Button(save_dialog, text='Yes', width='10', command=do_project_save)
        yes_button.grid(row=2, column=0, sticky='e', padx=5)

        no_button = Button(save_dialog, text='No', width='10', command=exit_save_dialog)
        no_button.grid(row=2, column=1, sticky='w', padx=5)

        self.ask_to_save = False

    def on_program_exit(self):
        if self.ask_to_save:
            self.ask_to_save_dialog(root_destroy=True)
            return
        self.end_program()

    def end_program(self):
        if on_mac:
            shutil.rmtree(self.global_temp)
            self.root.destroy()
            return
        with open(instance_path := f'{self.global_temp}instance', 'r', errors='ignore') as instance_file:
            current_instances = instance_file.readlines()
        if len(current_instances) > 1:
            if os.path.isdir(check_in_path := f'{self.global_temp}check_in') and not self.checked_in:
                return
            elif os.path.isdir(check_in_path):
                begin_time = float(time.mktime(datetime.now().timetuple()))
                while os.path.isdir(check_in_path):
                    if float(time.mktime(datetime.now().timetuple())) - begin_time >= 5:
                        return
            os.mkdir(check_in_path)
            waiting = True
            begin_time = float(time.mktime(datetime.now().timetuple()))
            while waiting:
                if len(os.listdir(check_in_path)) == len(current_instances):
                    waiting = False
                if float(time.mktime(datetime.now().timetuple())) - begin_time >= 2:
                    waiting = False
            failed_to_check_in = []
            for instance_id in current_instances:
                if instance_id == f'{self.instance_id}\n':
                    continue
                if instance_id.replace('\n', '') not in os.listdir(check_in_path):
                    failed_to_check_in.append(instance_id.replace('\n', ''))
            for failed_id in failed_to_check_in:
                if os.path.isdir(self.global_temp + failed_id):
                    shutil.rmtree(self.global_temp + failed_id)
            current_instances = [f'{instance_id}\n' for instance_id in os.listdir(check_in_path)]
            shutil.rmtree(check_in_path)
            if current_instances:
                with open(instance_path, 'w', errors='ignore') as out_file:
                    out_file.writelines(current_instances)
                shutil.rmtree(self.instance_temp)
            else:
                shutil.rmtree(self.global_temp)
        else:
            shutil.rmtree(self.global_temp)

        self.root.destroy()

    def easter(self, *_, decay=False):
        if self.easter_counter < 0:
            return
        if not decay:
            if not self.easter_counter:
                # noinspection PyTypeChecker
                self.root.after(2000, lambda: self.easter(decay=True))
            self.easter_counter += 1
            return
        self.easter_counter -= 1
        if not self.easter_counter:
            return
        # noinspection PyTypeChecker
        self.root.after(2000, lambda: self.easter(decay=True))


class C4SubIcon:
    def __init__(self, root_path: str, path: str, name: str, size: int):
        # Initialize Icon
        self.root = root_path  # Path to directory containing image
        self.path = path  # Full path to image file
        self.name, self.size, self.size_alt, self.name_alt, self.alt_format = name, size, None, '', False
        for char in reversed(self.root):
            if char == '/':
                break
            self.name_alt = char + self.name_alt
        # Check for alt format of icon
        if 'x' in self.name_alt:
            size0 = ''
            size1 = ''
            check_size0 = True
            for char in self.name_alt:
                if char == 'x':
                    check_size0 = False
                    continue
                if check_size0:
                    size0 += char
                    continue
                size1 += char
            with contextlib.suppress(ValueError):
                if (size0_int := int(size0)) and (size1_int := int(size1)):
                    self.alt_format = True
                    if size0_int != size1_int:
                        self.size_alt = (size0_int, size1_int)


class C4Icon:
    def __init__(self, icons: list, extra=False):
        # Initialize Icon Group
        self.name, self.name_orig = icons[0].name, icons[0].name
        self.name_alt, self.path, self.root = icons[0].name_alt, icons[0].path, icons[0].root
        self.icons, self.extra, self.dupe_number = icons, extra, 0


class DriverInfoWin:
    def __init__(self, main):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Edit Driver Info')
        w, h = (347, 240) if on_mac else (255, 240)
        self.window.geometry(f'{w}x{h}+{main.root.winfo_rootx() + main.export_panel.x}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        # Validate driver version
        if main.export_panel.inc_driver_version.get() and main.driver_version_var.get() and \
                main.driver_version_new_var.get() and \
                int(main.driver_version_new_var.get()) <= int(main.driver_version_var.get()):
            main.driver_version_new_var.set(str(int(main.driver_version_var.get()) + 1))

        # Labels
        instance_id_label = Label(self.window, text=f'instance id: {main.instance_id}')

        man_y = 20
        man_arrow = Label(self.window, text='\u2192', font=('', 15))

        creator_y = man_y + 55
        creator_arrow = Label(self.window, text='\u2192', font=('', 15))

        version_y = creator_y + 55
        version_arrow = Label(self.window, text='\u2192', font=('', 15))

        font_size = 13 if on_mac else 10
        title_size = 11 if on_mac else 8
        driver_ver_orig_label = Label(self.window, text='Original Version:', font=(label_font, title_size))

        driver_man_label = Label(self.window, text='Driver Manufacturer', font=(label_font, font_size))

        driver_creator_label = Label(self.window, text='Driver Creator', font=(label_font, font_size))

        driver_ver_label = Label(self.window, text='Driver Version', font=(label_font, font_size))

        # Entry
        entry_width = 16 if on_mac else 17
        driver_man_entry = Entry(self.window, width=entry_width, textvariable=main.driver_manufac_var)
        driver_man_entry['state'] = DISABLED
        self.driver_man_new_entry = Entry(self.window, width=entry_width, textvariable=main.driver_manufac_new_var)
        main.driver_manufac_new_var.trace('w', lambda name, index, mode: main.validate_man_and_creator(
            string_var=main.driver_manufac_new_var, entry=self.driver_man_new_entry))

        driver_creator_entry = Entry(self.window, width=entry_width, textvariable=main.driver_creator_var)
        driver_creator_entry['state'] = DISABLED
        self.driver_creator_new_entry = Entry(self.window, width=entry_width,
                                              textvariable=main.driver_creator_new_var)
        main.driver_creator_new_var.trace('w', lambda name, index, mode: main.validate_man_and_creator(
            string_var=main.driver_creator_new_var, entry=self.driver_creator_new_entry))

        driver_ver_entry = Entry(self.window, width=entry_width, textvariable=main.driver_version_var)
        driver_ver_entry['state'] = DISABLED
        self.driver_ver_new_entry = Entry(self.window, width=entry_width, textvariable=main.driver_version_new_var)
        self.driver_ver_new_entry.bind('<FocusOut>', main.export_panel.update_driver_version)
        main.driver_version_new_var.trace('w', main.validate_driver_ver)
        driver_ver_orig_entry = Entry(self.window, width=6, textvariable=main.driver_ver_orig)
        driver_ver_orig_entry['state'] = DISABLED
        if not on_mac:
            instance_id_label.place(x=127, y=220, anchor='n')
            man_arrow.place(x=115, y=man_y, anchor='nw')
            creator_arrow.place(x=115, y=creator_y, anchor='nw')
            version_arrow.place(x=115, y=version_y, anchor='nw')
            driver_man_label.place(x=127, y=man_y - 15, anchor='n')
            driver_creator_label.place(x=127, y=creator_y - 15, anchor='n')
            driver_ver_label.place(x=127, y=version_y - 15, anchor='n')
            driver_ver_orig_label.place(x=110, y=version_y + 30, anchor='ne')
            driver_man_entry.place(x=10, y=man_y + 7, anchor='nw')
            self.driver_man_new_entry.place(x=140, y=man_y + 7, anchor='nw')
            driver_creator_entry.place(x=10, y=creator_y + 7, anchor='nw')
            self.driver_creator_new_entry.place(x=140, y=creator_y + 7, anchor='nw')
            driver_ver_entry.place(x=10, y=version_y + 7, anchor='nw')
            self.driver_ver_new_entry.place(x=140, y=version_y + 7, anchor='nw')
            driver_ver_orig_entry.place(x=110, y=version_y + 30, anchor='nw')
        else:
            instance_id_label.place(x=173, y=220, anchor='n')

            man_arrow.place(x=163, y=man_y + 7, anchor='nw')
            creator_arrow.place(x=163, y=creator_y + 7, anchor='nw')
            version_arrow.place(x=163, y=version_y + 7, anchor='nw')

            driver_man_label.place(x=173, y=man_y - 15, anchor='n')
            driver_creator_label.place(x=173, y=creator_y - 15, anchor='n')
            driver_ver_label.place(x=173, y=version_y - 15, anchor='n')
            driver_ver_orig_label.place(x=140, y=version_y + 35, anchor='ne')

            driver_man_entry.place(x=10, y=man_y + 7, anchor='nw')
            self.driver_man_new_entry.place(x=180, y=man_y + 7, anchor='nw')
            driver_creator_entry.place(x=10, y=creator_y + 7, anchor='nw')
            self.driver_creator_new_entry.place(x=180, y=creator_y + 7, anchor='nw')
            driver_ver_entry.place(x=10, y=version_y + 7, anchor='nw')
            self.driver_ver_new_entry.place(x=180, y=version_y + 7, anchor='nw')
            driver_ver_orig_entry.place(x=140, y=version_y + 35, anchor='nw')

    def close(self):
        if not self.main.driver_version_new_var.get():
            self.main.driver_version_new_var.set('0')
        if not self.main.driver_creator_new_var.get():
            self.main.driver_creator_new_var.set('C4IconSwapper')
        if not self.main.driver_manufac_new_var.get():
            self.main.driver_manufac_new_var.set('C4IconSwapper')
        if not self.main.driver_version_new_var.get():
            if self.main.driver_version_var.get():
                self.main.driver_version_new_var.set(str(int(self.main.driver_version_var.get()) + 1))
            else:
                self.main.driver_version_new_var.set('1')
        if self.main.export_panel.inc_driver_version.get() and self.main.driver_version_var.get() and \
                int(self.main.driver_version_new_var.get()) <= int(self.main.driver_version_var.get()):
            self.main.driver_version_new_var.set(str(int(self.main.driver_version_var.get()) + 1))
        self.window.destroy()
        self.main.driver_info_win = None


class ConnectionsWin:
    def __init__(self, main):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Edit Driver Connections')
        x_spacing, y_spacing = (370, 40) if on_mac else (330, 40)
        w, h = (1125, 250) if on_mac else (975, 250)
        self.window.geometry(f'{w}x{h}+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        self.connections = [ConnectionEntry(self, main.connections[(x * 6) + y],
                                            x * x_spacing + 15, y * y_spacing + 25)
                            for x, y in itertools.product(range(3), range(6))]

    def refresh(self):
        for conn_entry in self.connections:
            conn_entry.refresh()

    def close(self):
        self.window.destroy()
        self.main.connections_win = None


class Connection:
    def __init__(self, main):
        self.main = main
        self.id = 0
        self.original, self.in_id_group, self.delete, self.enabled = False, False, False, False
        self.prior_txt, self.prior_type = '', ''
        self.tags, self.id_group = [], []
        self.name_entry_var = StringVar(value='Connection Name...')
        self.type = StringVar(value='HDMI IN')

    def update_id(self, *_, refresh=False):
        if not self.tags:
            return
        self.main.ask_to_save = True
        if self.original:
            for conn in self.main.connections:
                if conn is not self and conn.original and conn.id == self.id:
                    self.in_id_group = True
                    return
            self.in_id_group = False
            return
        if not refresh:
            return
        conn_type = self.type.get()
        valid_id = []
        if ' IN' in conn_type:
            conn_type = conn_type.replace(' IN', '')
            if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                valid_id = find_valid_id(2000, self.main.taken_conn_ids)
                self.tags[4].value = '5'
            elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                valid_id = find_valid_id(4000, self.main.taken_conn_ids)
                self.tags[4].value = '6'
        elif ' OUT' in conn_type:
            conn_type = conn_type.replace(' OUT', '')
            if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                valid_id = find_valid_id(1900, self.main.taken_conn_ids)
                self.tags[4].value = '5'
            elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                valid_id = find_valid_id(3900, self.main.taken_conn_ids)
                self.tags[4].value = '6'
        if conn_type == 'IR_OUT':
            valid_id = find_valid_id(1, self.main.taken_conn_ids)
            self.tags[4].value = '6'

        if self.id in self.main.taken_conn_ids:
            self.main.taken_conn_ids.pop(self.main.taken_conn_ids.index(self.id))
        self.id = valid_id[0]
        self.tags[3].value = str(self.id)
        self.main.taken_conn_ids.append(self.id)


class ConnectionEntry:
    def __init__(self, parent, conn_obj, x_pos: int, y_pos: int):
        # Initialize Connection UI Object
        self.main = parent.main
        self.window = parent.window
        self.conn_object = conn_obj
        self.x, self.y = x_pos, y_pos

        # Entry
        self.name_entry_var = conn_obj.name_entry_var
        self.name_entry_var.trace('w', self.name_update)
        self.name_entry = Entry(self.window, width=(15 if on_mac else 20), textvariable=self.name_entry_var)
        self.name_entry.place(x=self.x + (60 if on_mac else 35), y=self.y, anchor='w')
        if not self.conn_object.enabled:
            self.name_entry['state'] = DISABLED

        # Dropdown
        self.type = conn_obj.type
        self.type_menu = OptionMenu(self.window, self.type, *selectable_connections)
        self.type_menu.place(x=self.x + (207 if on_mac else 160), y=self.y, anchor='w')
        self.type.trace('w', self.conn_object.update_id)
        if not self.conn_object.enabled:
            self.type_menu['state'] = DISABLED

        # Buttons
        self.add_button = Button(self.window, text='Add', width=3, command=self.add, takefocus=0)
        y_offset = -3 if on_mac else 0
        if not self.conn_object.enabled and not self.conn_object.original:
            self.add_button.place(x=self.x, y=self.y + y_offset, anchor='w')
        if not self.main.driver_selected:
            self.add_button['state'] = DISABLED

        self.x_button = Button(self.window, text='x', width=1, command=self.delete, takefocus=0)
        if self.conn_object.enabled and not self.conn_object.original:
            self.x_button.place(x=self.x + (18 if on_mac else 14), y=self.y + y_offset, anchor='w')

        self.del_button = Button(self.window, text='Del', width=3, command=self.toggle_delete, takefocus=0)
        if self.conn_object.original:
            self.del_button.place(x=self.x, y=self.y + y_offset, anchor='w')
        if self.conn_object.delete:
            self.del_button['text'] = 'Keep'
            self.del_button['width'] = 4
            self.del_button.place(x=self.x + self.del_button.winfo_x() - 6, y=self.y)

    def refresh(self):
        self.name_entry_var.set(self.conn_object.name_entry_var.get())
        self.type.set(self.conn_object.type.get())
        if self.conn_object.enabled:
            self.type_menu['state'] = NORMAL
            self.name_entry['state'] = NORMAL
        else:
            self.type_menu['state'] = DISABLED
            self.name_entry['state'] = DISABLED

        if self.conn_object.enabled or self.conn_object.original:
            self.add_button.place_forget()
        else:
            self.add_button.place(x=self.x, y=self.y + (-3 if on_mac else 0), anchor='w')
        self.add_button['state'] = NORMAL if self.main.driver_selected else DISABLED

        if self.conn_object.enabled and not self.conn_object.original:
            self.x_button.place(x=self.x + (18 if on_mac else 14), y=self.y + (-3 if on_mac else 0), anchor='w')
        else:
            self.x_button.place_forget()

        if self.conn_object.original:
            self.del_button.place(x=self.x, y=self.y + (-3 if on_mac else 0), anchor='w')
        else:
            self.del_button.place_forget()

        if self.conn_object.delete:
            self.del_button['text'] = 'Keep'
            self.del_button['width'] = 4
            self.del_button.place(x=self.x + self.del_button.winfo_x() - 6, y=self.y)

    def add(self):
        self.conn_object.enabled = True
        self.name_entry['state'] = NORMAL
        self.type_menu['state'] = NORMAL
        self.add_button.place_forget()
        self.x_button.place(x=self.x + (18 if on_mac else 14), y=self.y + (-3 if on_mac else 0), anchor='w')
        self.name_entry['takefocus'] = 1
        if self.conn_object.tags:
            self.conn_object.tags[0].delete = False

    def delete(self):
        self.conn_object.enabled = False
        self.name_entry['state'] = DISABLED
        self.type_menu['state'] = DISABLED
        self.add_button.place(x=self.x, y=self.y + (-3 if on_mac else 0), anchor='w')
        self.x_button.place_forget()
        if self.conn_object.tags:
            self.conn_object.tags[0].delete = True
        self.name_entry['takefocus'] = 0

    def toggle_delete(self):
        if not self.conn_object.original:
            return
        if not self.conn_object.delete:
            self.conn_object.delete = True
            self.conn_object.prior_txt = self.name_entry_var.get()
            self.conn_object.prior_type = self.type.get()
            self.type.set('RIP')
            self.name_entry['state'] = NORMAL
            self.name_entry_var.set('TO BE DELETED')
            self.name_entry['state'] = DISABLED
            self.del_button['text'] = 'Keep'
            self.del_button['width'] = 4
            self.del_button.place(x=self.del_button.winfo_x() - 6, y=self.y)
            if len(self.conn_object.id_group) > 1:
                if all(groupie.delete for i, groupie in enumerate(self.conn_object.id_group) if i):
                    self.conn_object.tags[0].delete = True
                self.conn_object.tags[1].delete = True
            return
        self.conn_object.delete = False
        self.name_entry['state'] = NORMAL
        self.name_entry_var.set(self.conn_object.prior_txt)
        self.conn_object.prior_txt = ''
        self.name_entry['state'] = DISABLED
        self.type.set(self.conn_object.prior_type)
        self.conn_object.prior_type = ''
        if self.conn_object.tags:
            self.conn_object.tags[0].delete, self.conn_object.tags[1].delete = False, False
        self.del_button['text'] = 'Del'
        self.del_button['width'] = 3
        self.del_button.place(x=self.del_button.winfo_x() + 6, y=self.y)

    def name_update(self, *_):
        self.main.ask_to_save = True


class StatesWin:
    def __init__(self, main):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Edit Driver States')
        w, h = (405, 287) if on_mac else (385, 287)
        self.window.geometry(f'{w}x{h}+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        self.state_entries = []
        x_spacing, y_spacing = (190, 34) if on_mac else (200, 34)
        x_offset, y_offset = (25, 30) if on_mac else (10, 30)
        self.state_entries.extend(StateEntry(self, main.states[i], int(i / 7) * x_spacing + x_offset,
                                             (i % 7) * y_spacing + y_offset, label=f'state{i + 1}:')
                                  for i in range(13))

    def refresh(self):
        for state_entry in self.state_entries:
            state_entry.refresh()

    def close(self):
        self.refresh()
        self.window.destroy()
        self.main.states_win = None


class State:
    def __init__(self, name: str):
        self.original_name = name
        self.name_var = StringVar(value=name)
        background = light_entry_bg
        if on_mac and is_dark_mode():
            background = dark_entry_bg
        self.bg_color = background


class StateEntry:
    def __init__(self, parent, state_obj, x_pos: int, y_pos: int, label='State#:'):
        # Initialize Driver State UI Object
        self.main = parent.main
        self.window = parent.window
        self.state_object = state_obj
        self.original_name = state_obj.original_name
        self.x, self.y = x_pos, y_pos

        # Label
        self.name_label = Label(self.window, text=label)
        self.name_label.place(x=self.x + 35, y=self.y, anchor='e')

        # Entry
        self.name_var = StringVar(value=state_obj.name_var.get())
        self.name_var.trace('w', self.validate_state)
        self.name_entry = Entry(self.window, width=(13 if on_mac else 20), textvariable=self.name_var)
        self.name_entry.place(x=self.x + (36 if on_mac else 35), y=self.y, anchor='w')
        self.name_entry['background'] = state_obj.bg_color
        if not parent.main.multi_state_driver:
            self.name_entry['state'] = DISABLED

    def refresh(self, bg_only=False):
        self.name_entry['background'] = self.state_object.bg_color
        if bg_only:
            return
        self.name_var.set(self.state_object.name_var.get())

    def validate_state(self, *_):
        def state_object(obj_index):
            return self.main.states_win.state_entries[obj_index]

        def original_name_check(obj_index):
            orig_name_check = [*self.main.states_orig_names]
            orig_name_check.pop(obj_index)
            if state_object(obj_index).state_object.bg_color != 'pink' and \
                    state_object(obj_index).name_var.get() in orig_name_check:
                state_object(obj_index).state_object.bg_color = 'cyan'

        self.main.ask_to_save = True
        if not self.main.states_win:
            return
        self.update_state_name()
        self_index = self.main.states_win.state_entries.index(self)
        background_color = light_entry_bg
        if on_mac and is_dark_mode():
            background_color = dark_entry_bg
        in_dupe_list = False
        if not (self_name := self.name_var.get()):
            self.state_object.bg_color = 'pink'
            in_dupe_list = True
        for dupe_list in self.main.state_dupes:
            if self_index in dupe_list and \
                    ((dupe_list[0] is not self_index and state_object(dupe_list[0]).name_var.get() != self_name)
                     or state_object(dupe_list[-1]).name_var.get() != self_name):
                self.state_object.bg_color = background_color
                dupe_list.pop(dupe_list.index(self_index))
                if len(dupe_list) == 1:
                    state_object(dupe_list[0]).state_object.bg_color = background_color
                    original_name_check(dupe_list[0])
                    self.main.state_dupes.pop(self.main.state_dupes.index(dupe_list))
            elif self_index in dupe_list:
                in_dupe_list = True
            elif state_object(dupe_list[0]).name_var.get() == self_name and self_index not in dupe_list:
                dupe_list.append(self_index)
                self.state_object.bg_color = 'pink'
                in_dupe_list = True
        if not in_dupe_list:
            state_names = [state.name_var.get() for state in self.main.states_win.state_entries if state is not self]
            if self_name in state_names:
                dupe_list = [self.main.states_win.state_entries.index(state)
                             for state in self.main.states_win.state_entries if state.name_var.get() == self_name]
                for state_index in dupe_list:
                    state_object(state_index).state_object.bg_color = 'pink'
                self.main.state_dupes.append(dupe_list)
            else:
                self.state_object.bg_color = background_color

        original_name_check(self_index)

        for state_entry in self.main.states_win.state_entries:
            state_entry.refresh(bg_only=True)
        self.state_object.name_var.set(self_name)

    def update_state_name(self):
        name = self.name_var.get()
        formatted_name = [char for char in name if char != ' ' and (
                char in letters or char in capital_letters or char in numbers)]
        if not formatted_name:
            self.name_var.set('')
            return
        if formatted_name[0] in letters:
            formatted_name[0] = capital_letters[letters.index(formatted_name[0])]
        if str_diff := len(name) - len(formatted_name):
            cursor_pos = self.name_entry.index(INSERT)
            self.name_entry.icursor(cursor_pos - str_diff)
        self.name_var.set(''.join(formatted_name))


class C4zPanel:
    def __init__(self, main):
        # Initialize C4z Panel
        self.main = main
        self.x, self.y = 5, 20
        self.current_icon, self.extra_icons = 0, 0
        self.icons = []

        # Labels
        self.panel_label = Label(main.root, text='Driver Selection', font=(label_font, 15))
        self.panel_label.place(x=(165 if on_mac else 150) + self.x, y=-20 + self.y, anchor='n')

        self.c4_icon_label = Label(main.root, image=main.blank)
        self.c4_icon_label.image = main.blank
        self.c4_icon_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        if not on_mac:
            self.c4_icon_label.drop_target_register(DND_FILES)
            self.c4_icon_label.dnd_bind('<<Drop>>', self.drop_in_c4z)

        self.icon_num_label = Label(main.root, text='0 of 0')
        self.icon_num_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

        self.icon_name_label = Label(main.root, text='icon name')
        self.icon_name_label.place(x=108 + self.x, y=193 + self.y, anchor='n')

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.load_c4z, takefocus=0)
        self.open_file_button.place(x=(203 if on_mac else 187) + self.x, y=(27 if on_mac else 30) + self.y, anchor='w')

        self.restore_button = Button(main.root, text='Restore\nOriginal Icon', command=self.restore, takefocus=0)
        self.restore_button.place(x=(258 if on_mac else 228) + self.x, y=91 + self.y, anchor='n')
        self.restore_button['state'] = DISABLED

        self.restore_all_button = Button(
            main.root, text='Restore All', command=lambda: self.restore(do_all=True), takefocus=0)
        self.restore_all_button.place(x=(258 if on_mac else 225) + self.x, y=58 + self.y, anchor='n')
        self.restore_all_button['state'] = DISABLED

        self.prev_icon_button = Button(main.root, text='Prev', command=self.prev_icon, width=5, takefocus=0)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = Button(main.root, text='Next', command=self.next_icon, width=5, takefocus=0)
        self.next_icon_button['state'] = DISABLED
        self.next_icon_button.place(x=(260 if on_mac else 230) + self.x, y=146 + self.y)

        # Entry
        self.file_entry_field = Entry(main.root, width=(22 if on_mac else 25), takefocus=0)
        self.file_entry_field.place(x=(101 if on_mac else 108) + self.x, y=(15 if on_mac else 21) + self.y, anchor='n')
        if not on_mac:
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_c4z)
        self.file_entry_field.insert(0, 'Select .c4z file...')
        self.file_entry_field['state'] = DISABLED

        # Checkboxes
        self.show_extra_icons = IntVar(value=0)
        self.show_extra_icons.trace('w', self.toggle_extra_icons)
        self.show_sub_icons_check = Checkbutton(main.root, text='show extra icons',
                                                variable=self.show_extra_icons, takefocus=0)
        self.show_sub_icons_check.place(x=self.x + 177, y=self.y + 176, anchor='nw')

    def load_gen_driver(self):
        if self.main.ask_to_save:
            self.main.ask_to_save_dialog(on_exit=False, return_to='generic')
            return
        # Load generic two-state driver from Base64Assets
        gen_driver_path = f'{self.main.instance_temp}generic.c4z'
        if self.file_entry_field.get() == gen_driver_path:
            return
        if on_mac:
            with open(get_path(gen_driver_path), 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_driver))
        else:
            with open(gen_driver_path, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_driver))

        if os.path.isdir(temp_driver_path := f'{self.main.instance_temp}driver'):
            shutil.rmtree(temp_driver_path)

        shutil.unpack_archive(gen_driver_path, temp_driver_path, 'zip')
        os.remove(gen_driver_path)

        sizes = [(70, 70), (90, 90), (300, 300), (512, 512)]
        pictures = os.listdir(self.main.device_icon_dir)
        for picture in pictures:
            resized_icon = Image.open(self.main.device_icon_dir + picture)
            for size in sizes:
                new_icon = resized_icon.resize(size)
                new_icon.save(self.main.device_icon_dir + picture.replace('1024', str(size[0])))

        shutil.make_archive(gen_driver_path.replace('.c4z', ''), 'zip', f'{self.main.instance_temp}driver')

        os.rename(gen_driver_path.replace('.c4z', '.zip'), gen_driver_path)

        self.load_c4z(gen_driver_path)
        self.main.export_panel.driver_name_entry.delete(0, 'end')
        self.main.export_panel.driver_name_entry.insert(0, 'New Driver')
        self.main.ask_to_save = False
        os.remove(gen_driver_path)

    def load_gen_multi(self, show_loading_image=True):
        if self.main.ask_to_save:
            self.main.ask_to_save_dialog(on_exit=False, return_to='multi')
            return
        # Shows loading image then recalls function with show_loading_image=False
        if show_loading_image:
            self.show_loading_image()
            return
        # Load generic multi-state driver from Base64Assets
        multi_driver_path = f'{self.main.instance_temp}multi generic.c4z'
        if self.file_entry_field.get() == multi_driver_path:
            return
        if on_mac:
            with open(get_path(multi_driver_path), 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_multi))
        else:
            with open(multi_driver_path, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(generic_multi))

        if os.path.isdir(temp_driver_path := f'{self.main.instance_temp}driver'):
            shutil.rmtree(temp_driver_path)

        shutil.unpack_archive(multi_driver_path, temp_driver_path, 'zip')
        os.remove(multi_driver_path)

        sizes = [(90, 90), (300, 300), (512, 512), (1024, 1024)]
        pictures = os.listdir(self.main.device_icon_dir)
        for picture in pictures:
            resized_icon = Image.open(self.main.device_icon_dir + picture)
            for size in sizes:
                new_icon = resized_icon.resize(size)
                new_icon.save(self.main.device_icon_dir + picture.replace('70', str(size[0])))

        shutil.make_archive(multi_driver_path.replace('.c4z', ''), 'zip', f'{self.main.instance_temp}driver')

        os.rename(multi_driver_path.replace('.c4z', '.zip'), multi_driver_path)

        self.load_c4z(multi_driver_path)
        self.main.export_panel.driver_name_entry.delete(0, 'end')
        self.main.export_panel.driver_name_entry.insert(0, 'New Driver')
        self.main.ask_to_save = False
        os.remove(multi_driver_path)
        os.remove(f'{self.main.instance_temp}loading_icon.gif')

    def load_c4z(self, given_path=None, recovery=False):
        # Could improve this
        def get_icons(directory):
            if not os.path.isdir(directory):
                return []
            icons_out = []
            sub_list = []
            path_list = os.listdir(directory)
            path_list.sort()
            for string in path_list:
                if '.bak' in string or string[0] == '.':
                    continue
                if os.path.isdir(sub_path := f'{directory}/{string}'):
                    sub_list.append(sub_path)
                    continue
                if 'device_lg' in string or 'icon_large' in string:
                    icon_objects.append(C4SubIcon(directory, f'{directory}/{string}', 'device', 32))
                    continue
                elif 'device_sm' in string or 'icon_small' in string:
                    icon_objects.append(C4SubIcon(directory, f'{directory}/{string}', 'device', 16))
                    continue
                temp_name = ''
                read_size = False
                read_name = False
                alt_sized = False
                for character in reversed(string):
                    if character == '.':
                        read_size = True
                        continue
                    if read_size:
                        try:
                            int(character)
                        except ValueError:
                            if character != '_':
                                temp_name = character + temp_name
                            read_size = False
                            read_name = True
                        continue
                    if read_name:
                        temp_name = character + temp_name
                temp_img = Image.open(f'{directory}/{string}')
                temp_size = str(temp_img.size[0])
                if temp_img.size[0] != temp_img.size[1]:
                    alt_sized = True
                icons_out.append(C4SubIcon(directory, f'{directory}/{string}', temp_name, int(temp_size)))
                if alt_sized:
                    icons_out[-1].size_alt = temp_img.size
                temp_img.close()

            if not sub_list:
                return icons_out
            for sub_dir in sorted(sub_list):
                icons_out.extend(get_icons(sub_dir))
            return icons_out

        # Could improve this
        def check_dupe_names(recalled=False):
            recall = False
            if not recalled:
                checked_list = []
                for icon_cmp0 in self.icons:
                    checked_list.append(icon_cmp0)
                    dupe_count = 0
                    for icon_cmp1 in self.icons:
                        if icon_cmp1 not in checked_list and icon_cmp0.name == icon_cmp1.name:
                            dupe_count += 1
                            checked_list.append(icon_cmp1)
                            icon_cmp1.dupe_number = dupe_count
            for icon_cmp0 in self.icons:
                for icon_cmp1 in self.icons:
                    if icon_cmp0 is not icon_cmp1 and icon_cmp0.name == icon_cmp1.name:
                        recall = True
                        if recalled:
                            # This code should never run
                            print('debug testing: recalled dupe name check')
                            icon_cmp1.name = f'{icon_cmp1.name} ({icon_cmp1.dupe_number})'
                            continue
                        icon_cmp0.name = icon_cmp0.name_alt
                        icon_cmp1.name = icon_cmp1.name_alt
                        break
            if recall:
                check_dupe_names(recalled=True)

        if self.main.ask_to_save:
            self.main.ask_to_save_dialog(given_path, recovery, on_exit=False, return_to='load_c4z')
            return

        if self.file_entry_field.get() == 'Invalid driver selected...':
            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            if self.main.restore_entry_string:
                self.file_entry_field.insert(0, self.main.restore_entry_string)
            else:
                self.file_entry_field.insert(0, 'Select .c4z file...')
            self.file_entry_field['state'] = 'readonly'
            self.main.restore_entry_string = ''
            self.main.time_var = 0
            self.main.schedule_entry_restore = False

        # Backup existing driver data
        temp_bak = f'{self.main.instance_temp}temp_driver_backup/'
        icons_bak = None
        if self.icons:
            icons_bak = self.icons
            if os.path.isdir(temp_driver_path := f'{self.main.instance_temp}driver'):
                shutil.copytree(temp_driver_path, temp_bak)

        # File select dialog
        if given_path is None and not recovery:
            filename = filedialog.askopenfilename(filetypes=[('Control4 Drivers', '*.c4z')])
            # If no file selected
            if not filename:
                if os.path.isdir(temp_bak):
                    shutil.rmtree(temp_bak)
                return
        elif recovery:
            filename = 'Recovered Driver'
        else:
            filename = given_path

        # Delete existing driver
        self.main.driver_selected = False
        if os.path.isdir(driver_folder := f'{self.main.instance_temp}driver/') and not recovery:
            shutil.rmtree(driver_folder)

        # Unpack selected driver
        if not recovery:
            shutil.unpack_archive(filename, f'{self.main.instance_temp}driver', 'zip')

        # Get all individual icons from driver
        icon_objects = []
        with contextlib.suppress(TypeError):
            icon_objects.extend(get_icons(self.main.icon_dir))
            icon_objects.extend(get_icons(self.main.images_dir))

        # Form icon groups
        self.icons = []
        if icon_objects:
            unique_icons = []
            if not icon_objects[0].alt_format:
                unique_icons = [icon_objects[0]]
            alt_format_icons = [icon for icon in icon_objects if icon.alt_format]
            for icon in icon_objects:
                if icon.alt_format or any((icon.name == unique_icon.name and icon.root == unique_icon.root)
                                          for unique_icon in unique_icons):
                    continue
                unique_icons.append(icon)
            for unique_icon in unique_icons:
                icon_group = [icon for icon in icon_objects if icon.name == unique_icon.name and
                              icon.root == unique_icon.root]
                if all('device' not in x for x in [icon_group[0].path, icon_group[0].root, icon_group[0].name]):
                    self.icons.append(C4Icon(icon_group, extra=True))
                else:
                    self.icons.append(C4Icon(icon_group))
            # Form icon groups with alt format
            if alt_format_icons:
                unique_icons = [alt_format_icons[0]]
                for icon in alt_format_icons:
                    if all(icon.name != unique_icon.name for unique_icon in unique_icons):
                        unique_icons.append(icon)
                for unique_icon in unique_icons:
                    icon_group = [unique_icon]
                    for icon in alt_format_icons:
                        if icon is not unique_icon and icon.name == unique_icon.name:
                            icon_group.append(icon)
                    check_list = [icon_group[0].path, icon_group[0].root, icon_group[0].name]
                    added = False
                    for check_string in check_list:
                        if all(string not in check_string for string in ['device', 'branding', 'icon']):
                            self.icons.append(C4Icon(icon_group, extra=True))
                            added = True
                            break
                    if not added:
                        self.icons.append(C4Icon(icon_group))
            # Rename icons with duplicate names
            check_dupe_names()

        # Update entry fields and restore driver if necessary
        elif not self.icons:
            self.file_entry_field['state'] = NORMAL
            if self.file_entry_field.get() not in ['Select .c4z file...', 'Invalid driver selected...']:
                # Restore existing driver data if invalid driver selected
                self.icons = icons_bak
                if os.path.isdir(temp_bak):
                    if os.path.isdir(driver_folder):
                        shutil.rmtree(driver_folder)
                    shutil.copytree(temp_bak, driver_folder)
                    shutil.rmtree(temp_bak)
                self.main.root.after(3000, self.main.restore_entry_text)
                self.main.schedule_entry_restore = True
                self.main.restore_entry_string = self.file_entry_field.get()
                self.main.driver_selected = True
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, 'Invalid driver selected...')
            self.file_entry_field['state'] = DISABLED
            return

        # Count extra icons & naturally sort icon order
        not_extra_icons = []
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
            not_extra_icons.append(icon)
            self.icons.pop(self.icons.index(icon))
        # Sort extra icons
        temp_name_list = [icon.name for icon in self.icons]
        temp_name_list.sort(key=natural_key)
        temp_icons = [*self.icons]
        temp_name_dict = {}
        for icon in self.icons:
            temp_name_dict[icon.name] = temp_icons.index(icon)
        self.icons = [temp_icons[temp_name_dict[icon_name]] for icon_name in temp_name_list]
        # Sort main device icons
        temp_name_list = [icon.name for icon in not_extra_icons]
        temp_name_dict = {}
        for icon in not_extra_icons:
            temp_name_dict[icon.name] = not_extra_icons.index(icon)
        temp_name_list.sort(key=natural_key)
        for icon_name in reversed(temp_name_list):
            self.icons.insert(0, not_extra_icons[temp_name_dict[icon_name]])
        if device_exception:
            self.icons.insert(0, device_exception)

        # Update entry with driver file path
        self.file_entry_field['state'] = NORMAL
        self.file_entry_field.delete(0, 'end')
        self.file_entry_field.insert(0, filename.replace('\\', '/'))
        self.file_entry_field['state'] = 'readonly'
        orig_file_path = filename
        orig_driver_name = ''
        for i in reversed(range(len(orig_file_path) - 1)):
            if orig_file_path[i] == '/':
                self.main.orig_file_dir = orig_file_path[:i + 1]
                break
            if orig_driver_name:
                orig_driver_name = orig_file_path[i] + orig_driver_name
                continue
            if orig_file_path[i + 1] == '.':
                orig_driver_name = orig_file_path[i]
        if orig_driver_name not in ['generic', 'multi generic']:
            self.main.export_panel.driver_name_entry.delete(0, 'end')
            self.main.export_panel.driver_name_entry.insert(0, orig_driver_name)
        if not self.main.export_panel.driver_name_entry.get():
            self.main.export_panel.driver_name_entry.insert(0, 'New Driver')
        self.main.driver_selected = True
        self.current_icon = 0
        self.update_icon()

        # Read driver.xml and update variables
        self.main.driver_xml = XMLObject(f'{self.main.instance_temp}driver/driver.xml')
        man_tag = self.main.driver_xml.get_tag('manufacturer')
        if man_tag:
            self.main.driver_manufac_var.set(man_tag[0].value)
        creator_tag = self.main.driver_xml.get_tag('creator')
        if creator_tag:
            self.main.driver_creator_var.set(creator_tag[0].value)
        self.main.driver_version_count = 1
        version_tag = self.main.driver_xml.get_tag('version')
        if version_tag:
            self.main.driver_ver_orig.set(version_tag[0].value)
            temp_str = ''
            for char in version_tag[0].value:
                if char not in numbers:
                    continue
                temp_str += char
            if temp_str:
                self.main.driver_version_var.set(temp_str)
                if self.main.export_panel.inc_driver_version.get():
                    self.main.driver_version_new_var.set(str(int(temp_str) + 1))
                else:
                    self.main.driver_version_new_var.set(temp_str)
            else:
                self.main.driver_version_var.set('0')
                self.main.driver_version_new_var.set('1')
        id_tags = self.main.driver_xml.get_tag('id')
        if id_tags:
            self.main.taken_conn_ids = []
            for id_tag in id_tags:
                with contextlib.suppress(ValueError):
                    if int(id_tag.value) not in self.main.taken_conn_ids:
                        self.main.taken_conn_ids.append(int(id_tag.value))

        # Check lua file for multi-state
        self.main.multi_state_driver = False
        self.main.edit.entryconfig(self.main.states_pos, state=DISABLED)
        if os.path.isfile(lua_path := f'{self.main.instance_temp}driver/driver.lua'):
            if on_mac:
                with open(get_path(lua_path), errors='ignore') as driver_lua_file:
                    driver_lua_lines = driver_lua_file.readlines()
            else:
                with open(lua_path, errors='ignore') as driver_lua_file:
                    driver_lua_lines = driver_lua_file.readlines()
            for line in driver_lua_lines:
                if '_OPTIONS = { {' in line:
                    self.main.get_states(driver_lua_lines)
                    self.main.multi_state_driver = True
                    break
        if self.main.multi_state_driver:
            self.main.edit.entryconfig(self.main.states_pos, state=NORMAL)
        elif self.main.states_win:
            self.main.close_states()
        self.main.state_dupes = []

        # Update driver prev/next buttons
        if len(self.icons) <= 1:
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
        else:
            self.prev_icon_button['state'] = NORMAL
            self.next_icon_button['state'] = NORMAL
        # Update replacement prev/next buttons
        if self.main.replacement_selected and self.main.driver_selected:
            self.main.replacement_panel.replace_button['state'] = NORMAL
            self.main.replacement_panel.replace_all_button['state'] = NORMAL
        else:
            self.main.replacement_panel.replace_button['state'] = DISABLED
            self.main.replacement_panel.replace_all_button['state'] = DISABLED
        # Update Export button(s)
        if self.main.driver_selected:
            if not on_mac:
                self.main.export_panel.export_button['state'] = NORMAL
            self.main.export_panel.export_as_button['state'] = NORMAL
        # Update 'Restore All' button in driver panel
        done = False
        self.restore_all_button['state'] = DISABLED
        for path in list_all_sub_directories(driver_folder):
            files = os.listdir(path)
            for file in files:
                if '.bak' in file and '.xml' not in file:
                    self.restore_all_button['state'] = NORMAL
                    done = True
                    break
            if done:
                break
        # Update restore current icon button in driver panel
        if os.path.isfile(f'{self.icons[self.current_icon].path}.bak'):
            self.restore_button['state'] = NORMAL
        else:
            self.restore_button['state'] = DISABLED

        # Remove temp backup directory
        if os.path.isdir(temp_bak):
            shutil.rmtree(temp_bak)

        # Update connections panel
        self.get_connections()
        if self.main.connections_win:
            self.main.connections_win.refresh()
        if self.main.states_win:
            self.main.states_win.refresh()

        self.main.ask_to_save = True

    if not on_mac:
        def drop_in_c4z(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            multi_file_drop = []
            running_str = ''
            for char in dropped_path:
                if char == ' ' and is_valid_image(running_str):
                    multi_file_drop.append(running_str)
                    running_str = ''
                    continue
                running_str += char
            if is_valid_image(running_str):
                multi_file_drop.append(running_str)
            if multi_file_drop:
                for file in multi_file_drop:
                    self.main.replacement_panel.process_image(file_path=file)
                return

            if dropped_path.endswith('.c4z'):
                self.load_c4z(given_path=dropped_path)
            elif is_valid_image(dropped_path):
                self.main.replacement_panel.process_image(file_path=dropped_path)
            elif '.' not in dropped_path:
                image_paths = os.listdir(dropped_path)
                for new_img_path in image_paths:
                    self.main.replacement_panel.process_image(file_path=f'{dropped_path}/{new_img_path}')

    def restore(self, do_all=False):
        self.main.update_undo_history()

        for icon in (self.icons if do_all else [self.icons[self.current_icon]]):
            for sub_icon in icon.icons:
                bak_path = f'{sub_icon.path}.bak'
                if os.path.isfile(bak_path):
                    shutil.move(bak_path, sub_icon.path)
        self.restore_button['state'] = DISABLED
        if not any(os.path.isfile(f'{group.icons[0].path}.bak') for group in self.icons):
            self.restore_all_button['state'] = DISABLED
        self.update_icon()
        self.main.ask_to_save = True

    def toggle_extra_icons(self, *_):
        if not self.main.driver_selected:
            return
        if not self.show_extra_icons.get() and self.main.c4z_panel.icons[self.main.c4z_panel.current_icon].extra:
            self.next_icon()
        self.update_icon()

    def prev_icon(self):
        if not self.main.driver_selected:
            return
        if self.current_icon < 1:
            self.current_icon = self.current_icon - 1 + len(self.icons)
        else:
            self.current_icon -= 1

        if os.path.isfile(f'{self.icons[self.current_icon].path}.bak'):
            self.restore_button['state'] = NORMAL
        else:
            self.restore_button['state'] = DISABLED

        if not self.show_extra_icons.get() and self.icons[self.current_icon].extra:
            while self.icons[self.current_icon].extra:
                if self.current_icon < 1:
                    self.current_icon = self.current_icon - 1 + len(self.icons)
                else:
                    self.current_icon -= 1

        self.update_icon()

    def next_icon(self):
        if not self.main.driver_selected:
            return
        if self.current_icon + 1 >= len(self.icons):
            self.current_icon = self.current_icon + 1 - len(self.icons)
        else:
            self.current_icon += 1

        if os.path.isfile(f'{self.icons[self.current_icon].path}.bak'):
            self.restore_button['state'] = NORMAL
        else:
            self.restore_button['state'] = DISABLED

        if not self.show_extra_icons.get() and self.icons[self.current_icon].extra:
            while self.icons[self.current_icon].extra:
                if self.current_icon + 1 >= len(self.icons):
                    self.current_icon = self.current_icon + 1 - len(self.icons)
                else:
                    self.current_icon += 1

        self.update_icon()

    def show_loading_image(self):
        loading_img_path = f'{self.main.instance_temp}loading_icon.gif'
        if on_mac:
            with open(get_path(loading_img_path), 'wb') as loading_img:
                loading_img.write(base64.b64decode(loading_icon))
        else:
            with open(loading_img_path, 'wb') as loading_img:
                loading_img.write(base64.b64decode(loading_icon))
        icon_image = Image.open(loading_img_path)
        icon = ImageTk.PhotoImage(icon_image)
        self.c4_icon_label.configure(image=icon)
        self.c4_icon_label.image = icon
        self.main.root.after(1, self.main.recall_load_gen_multi)

    def update_icon(self):
        if not self.icons:
            return
        if abs(self.current_icon) >= len(self.icons):
            self.current_icon = abs(self.current_icon) % len(self.icons)
        icon_image = Image.open(self.icons[self.current_icon].path)
        icon = icon_image.resize((128, 128))
        icon = ImageTk.PhotoImage(icon)
        self.c4_icon_label.configure(image=icon)
        self.c4_icon_label.image = icon

        if not self.show_extra_icons.get() and self.extra_icons:
            self.icon_num_label.config(text=f'icon: {self.current_icon + 1} of '
                                        f'{len(self.icons) - self.extra_icons} ({len(self.icons)})')
        else:
            self.icon_num_label.config(text=f'icon: {self.current_icon + 1} of {len(self.icons)}')
        self.icon_name_label.config(text=f'name: {self.icons[self.current_icon].name}')

    def get_connections(self):
        if not os.path.isfile(f'{self.main.instance_temp}driver/driver.xml') or not self.main.driver_selected:
            return
        for conn in self.main.connections:
            conn.__init__(self.main)

        # Get connections from xml object
        connections = []
        if classname_tags := self.main.driver_xml.get_tag('classname'):
            for classname_tag in reversed(classname_tags):
                if classname_tag.value not in valid_connections:
                    classname_tags.pop(classname_tags.index(classname_tag))
            for classname_tag in classname_tags:
                class_tag, connection_tag, connectionname_tag, id_tag, type_tag = None, None, None, None, None
                for parent in reversed(classname_tag.parents):
                    if (parent_name := parent.name) == 'class':
                        class_tag = parent
                    elif parent_name == 'connection':
                        connection_tag = parent
                        for child in connection_tag.children:
                            if (child_name := child.name) == 'type':
                                type_tag = child
                            elif child_name == 'id':
                                id_tag = child
                            elif child_name == 'connectionname':
                                connectionname_tag = child
                if all([id_tag, connection_tag, class_tag, connectionname_tag, type_tag]):
                    connections.append([connectionname_tag.value, classname_tag.value, id_tag.value,
                                        connection_tag, class_tag, connectionname_tag, id_tag, type_tag,
                                        classname_tag])

        # Check that number of connections does not exceed maximum
        if len(connections) > len(self.main.connections):
            conn_range = len(self.main.connections) - 1
        else:
            conn_range = len(connections)

        # Assign panel connections to xml tags and update UI
        id_groups = []
        for i in range(conn_range):
            not_in_group = True
            for group in id_groups:
                if group[0] is connections[i][3]:
                    group.append(self.main.connections[i])
                    not_in_group = False
            if not_in_group:
                id_groups.append([connections[i][3], self.main.connections[i]])
            self.main.connections[i].name_entry_var.set(connections[i][0])
            self.main.connections[i].type.set(connections[i][1])
            self.main.connections[i].id = connections[i][2]
            self.main.connections[i].tags = connections[i][3:]
            self.main.connections[i].original = True

        # Fill in remaining empty connections
        for conn in self.main.connections:
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
            self.main.driver_xml.get_tag('connections')[0].children.append(new_conn)
            conn.tags = [new_conn, class_tag, name_tag, id_tag, type_tag, classname_tag]

        # Form id groups
        for group in id_groups:
            first = True
            for conn in group:
                if first:
                    first = False
                    continue
                new_group = [conn0 for conn0 in group if conn0 != conn]
                conn.id_group = new_group
        for conn in self.main.connections:
            conn.update_id()


class ReplacementPanel:
    def __init__(self, main):
        # Initialize Replacement Panel
        self.main = main
        self.x, self.y = (355, 20) if on_mac else (303, 20)
        self.img_bank, self.img_bank_tk_labels = [], []

        # Labels
        self.panel_label = Label(main.root, text='Replacement Icons', font=(label_font, 15))
        self.panel_label.place(x=(165 if on_mac else 150) + self.x, y=-20 + self.y, anchor='n')

        self.replacement_img_label = Label(main.root, image=main.blank)
        self.replacement_img_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.replacement_img_label.image = main.blank
        if not on_mac:
            self.replacement_img_label.drop_target_register(DND_FILES)
            self.replacement_img_label.dnd_bind('<<Drop>>', self.drop_in_replacement)

        self.img_bank_tk_labels.append(Label(main.root, image=main.stack_blank))
        self.img_bank_tk_labels[-1].place(x=(18 if on_mac else 31) + self.x, y=176 + self.y, anchor='nw')
        self.img_bank_tk_labels[-1].image = main.stack_blank
        self.img_bank_tk_labels[-1].bind('<Button-1>', self.select_stack0)
        if not on_mac:
            self.img_bank_tk_labels[-1].drop_target_register(DND_FILES)
            self.img_bank_tk_labels[-1].dnd_bind('<<Drop>>', self.drop_stack0)

        self.img_bank_tk_labels.append(Label(main.root, image=main.stack_blank))
        self.img_bank_tk_labels[-1].place(x=(79 if on_mac else 92) + self.x, y=176 + self.y, anchor='nw')
        self.img_bank_tk_labels[-1].image = main.stack_blank
        self.img_bank_tk_labels[-1].bind('<Button-1>', self.select_stack1)
        if not on_mac:
            self.img_bank_tk_labels[-1].drop_target_register(DND_FILES)
            self.img_bank_tk_labels[-1].dnd_bind('<<Drop>>', self.drop_stack1)

        self.img_bank_tk_labels.append(Label(main.root, image=main.stack_blank))
        self.img_bank_tk_labels[-1].place(x=(140 if on_mac else 153) + self.x, y=176 + self.y, anchor='nw')
        self.img_bank_tk_labels[-1].image = main.stack_blank
        self.img_bank_tk_labels[-1].bind('<Button-1>', self.select_stack2)
        if not on_mac:
            self.img_bank_tk_labels[-1].drop_target_register(DND_FILES)
            self.img_bank_tk_labels[-1].dnd_bind('<<Drop>>', self.drop_stack2)

        self.img_bank_tk_labels.append(Label(main.root, image=main.stack_blank))
        self.img_bank_tk_labels[-1].place(x=(201 if on_mac else 214) + self.x, y=176 + self.y, anchor='nw')
        self.img_bank_tk_labels[-1].image = main.stack_blank
        self.img_bank_tk_labels[-1].bind('<Button-1>', self.select_stack3)
        if on_mac:
            self.img_bank_tk_labels.append(Label(main.root, image=main.stack_blank))
            self.img_bank_tk_labels[-1].place(x=262 + self.x, y=176 + self.y, anchor='nw')
            self.img_bank_tk_labels[-1].image = main.stack_blank
            self.img_bank_tk_labels[-1].bind('<Button-1>', self.select_stack4)
        else:
            self.img_bank_tk_labels[-1].drop_target_register(DND_FILES)
            self.img_bank_tk_labels[-1].dnd_bind('<<Drop>>', self.drop_stack3)

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.process_image, takefocus=0)
        self.open_file_button.place(x=(205 if on_mac else 187) + self.x, y=(27 if on_mac else 30) + self.y, anchor='w')

        self.replace_all_button = Button(main.root, text='Replace All', command=self.replace_all, takefocus=0)
        self.replace_all_button.place(x=(258 if on_mac else 228) + self.x, y=58 + self.y, anchor='n')
        self.replace_all_button['state'] = DISABLED

        self.replace_button = Button(main.root, text='Replace\nCurrent Icon', command=self.replace_icon, takefocus=0)
        self.replace_button.place(x=(258 if on_mac else 228) + self.x, y=91 + self.y, anchor='n')
        self.replace_button['state'] = DISABLED

        self.prev_icon_button = Button(main.root, text='Prev', command=self.dec_img_stack, width=5, takefocus=0)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = Button(main.root, text='Next', command=self.inc_img_stack, width=5, takefocus=0)
        self.next_icon_button.place(x=(260 if on_mac else 230) + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_field = Entry(main.root, width=(22 if on_mac else 25), takefocus=0)
        self.file_entry_field.place(x=(103 if on_mac else 108) + self.x, y=(15 if on_mac else 21) + self.y, anchor='n')
        if not on_mac:
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_replacement)
        self.file_entry_field.insert(0, 'Select image file...')
        self.file_entry_field['state'] = DISABLED

    def process_image(self, file_path=''):
        if not file_path:
            for path in filedialog.askopenfilenames(filetypes=[('Image', '*.png'), ('Image', '*.jpg'),
                                                               ('Image', '*.gif'), ('Image', '*.jpeg')]):
                self.process_image(file_path=path)
            return

        if not file_path or not is_valid_image(file_path):
            return

        if self.main.replacement_selected:
            self.add_to_img_bank(self.main.replacement_image_path)
        replacement_image = Image.open(file_path)
        output_img = replacement_image.resize((1024, 1024))
        replacement_image.close()
        output_img.save(self.main.replacement_image_path)
        output_img.close()

        self.file_entry_field['state'] = NORMAL
        self.file_entry_field.delete(0, 'end')
        self.file_entry_field.insert(0, file_path.replace('\\', '/'))
        self.file_entry_field['state'] = 'readonly'

        if self.main.driver_selected:
            self.replace_button['state'] = NORMAL
            self.replace_all_button['state'] = NORMAL
        else:
            self.replace_button['state'] = DISABLED
            self.replace_all_button['state'] = DISABLED

        if not os.path.isfile(self.main.replacement_image_path):
            return
        self.main.replacement_selected = True
        icon_image = Image.open(self.main.replacement_image_path)
        icon = icon_image.resize((128, 128))
        icon_image.close()
        icon = ImageTk.PhotoImage(icon)
        self.replacement_img_label.configure(image=icon)
        self.replacement_img_label.image = icon

        if self.main.driver_selected:
            self.main.ask_to_save = True

    if not on_mac:
        def drop_in_replacement(self, event):
            img_path = event.data.replace('{', '').replace('}', '')
            multi_file_drop = []
            running_str = ''
            for char in img_path:
                if char == ' ' and is_valid_image(running_str):
                    multi_file_drop.append(running_str)
                    running_str = ''
                    continue
                running_str += char
            if is_valid_image(running_str):
                multi_file_drop.append(running_str)
            if multi_file_drop:
                for file in multi_file_drop:
                    self.process_image(file_path=file)
                return
            if '.' not in img_path:
                image_paths = os.listdir(img_path)
                for new_img_path in image_paths:
                    self.process_image(file_path=f'{img_path}/{new_img_path}')
                return
            if not is_valid_image(img_path):
                return
            self.process_image(file_path=img_path)

        def drop_stack0(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_bank(dropped_path, bank_index=0)

        def drop_stack1(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_bank(dropped_path, bank_index=1)

        def drop_stack2(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_bank(dropped_path, bank_index=2)

        def drop_stack3(self, event):
            dropped_path = event.data.replace('{', '').replace('}', '')
            self.add_to_img_bank(dropped_path, bank_index=3)

    def add_to_img_bank(self, img_path: str, bank_index=None):
        if not os.path.isfile(img_path) or not is_valid_image(img_path):
            return
        for img in self.img_bank:
            if filecmp.cmp(img, img_path):
                return

        stack_length = 5 if on_mac else 4

        new_img_path = f'{self.main.instance_temp}stack{len(self.img_bank)}.png'
        if 'replacement_icon.png' in img_path:
            os.rename(img_path, new_img_path)
        else:
            stack_image = Image.open(img_path)
            output_img = stack_image.resize((1024, 1024))
            stack_image.close()
            output_img.save(new_img_path)
            output_img.close()
        if bank_index is None:
            self.img_bank.insert(0, new_img_path)
        elif not -len(self.img_bank) < bank_index < len(self.img_bank):
            self.img_bank.append(new_img_path)
        else:
            temp = self.img_bank[bank_index]
            self.img_bank.pop(bank_index)
            self.img_bank.insert(bank_index, new_img_path)
            self.img_bank.append(temp)
        self.refresh_img_bank()
        if len(self.img_bank) > stack_length:
            self.prev_icon_button['state'] = NORMAL
            self.next_icon_button['state'] = NORMAL

        self.main.ask_to_save = True

    def select_stack0(self, _):
        if not self.img_bank:
            return
        replacement_in_stack = False
        replacement_index = None
        for img in self.img_bank:
            if filecmp.cmp(img, self.main.replacement_image_path):
                replacement_in_stack = True
                replacement_index = self.img_bank.index(img)
                break
        if not replacement_in_stack:
            self.add_to_img_bank(self.main.replacement_image_path, bank_index=0)
            self.process_image(file_path=self.img_bank[-1])
            return
        stack_length = 5 if on_mac else 4
        if len(self.img_bank) > stack_length and replacement_index > 3:
            self.process_image(file_path=self.img_bank[0])
            temp = self.img_bank[0]
            temp_r = self.img_bank[replacement_index]
            self.img_bank.pop(replacement_index)
            self.img_bank.pop(0)
            self.img_bank.insert(0, temp_r)
            self.img_bank.insert(replacement_index, temp)
            self.refresh_img_bank()
            return
        self.process_image(file_path=self.img_bank[0])

    def select_stack1(self, _):
        if len(self.img_bank) <= 1:
            return
        replacement_in_stack = False
        replacement_index = None
        for img in self.img_bank:
            if filecmp.cmp(img, self.main.replacement_image_path):
                replacement_in_stack = True
                replacement_index = self.img_bank.index(img)
                break
        if not replacement_in_stack:
            self.add_to_img_bank(self.main.replacement_image_path, bank_index=1)
            self.process_image(file_path=self.img_bank[-1])
            return
        stack_length = 5 if on_mac else 4
        if len(self.img_bank) > stack_length and replacement_index > 3:
            self.process_image(file_path=self.img_bank[1])
            temp = self.img_bank[1]
            temp_r = self.img_bank[replacement_index]
            self.img_bank.pop(replacement_index)
            self.img_bank.pop(1)
            self.img_bank.insert(1, temp_r)
            self.img_bank.insert(replacement_index, temp)
            self.refresh_img_bank()
            return
        self.process_image(file_path=self.img_bank[1])

    def select_stack2(self, _):
        if len(self.img_bank) <= 2:
            return
        replacement_in_stack = False
        replacement_index = None
        for img in self.img_bank:
            if filecmp.cmp(img, self.main.replacement_image_path):
                replacement_in_stack = True
                replacement_index = self.img_bank.index(img)
                break
        if not replacement_in_stack:
            self.add_to_img_bank(self.main.replacement_image_path, bank_index=2)
            self.process_image(file_path=self.img_bank[-1])
            return
        stack_length = 5 if on_mac else 4
        if len(self.img_bank) > stack_length and replacement_index > 3:
            self.process_image(file_path=self.img_bank[2])
            temp = self.img_bank[2]
            temp_r = self.img_bank[replacement_index]
            self.img_bank.pop(replacement_index)
            self.img_bank.pop(2)
            self.img_bank.insert(2, temp_r)
            self.img_bank.insert(replacement_index, temp)
            self.refresh_img_bank()
            return
        self.process_image(file_path=self.img_bank[2])

    def select_stack3(self, _):
        if len(self.img_bank) <= 3:
            return
        replacement_in_stack = False
        replacement_index = None
        for img in self.img_bank:
            if filecmp.cmp(img, self.main.replacement_image_path):
                replacement_in_stack = True
                replacement_index = self.img_bank.index(img)
                break
        if not replacement_in_stack:
            self.add_to_img_bank(self.main.replacement_image_path, bank_index=3)
            self.process_image(file_path=self.img_bank[-1])
            return
        stack_length = 5 if on_mac else 4
        if len(self.img_bank) > stack_length and replacement_index > 3:
            self.process_image(file_path=self.img_bank[3])
            temp = self.img_bank[3]
            temp_r = self.img_bank[replacement_index]
            self.img_bank.pop(replacement_index)
            self.img_bank.pop(3)
            self.img_bank.insert(3, temp_r)
            self.img_bank.insert(replacement_index, temp)
            self.refresh_img_bank()
            return
        self.process_image(file_path=self.img_bank[3])

    if on_mac:
        def select_stack4(self, _):
            if len(self.img_bank) <= 4:
                return
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_bank:
                if filecmp.cmp(img, self.main.replacement_image_path):
                    replacement_in_stack = True
                    replacement_index = self.img_bank.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_bank(self.main.replacement_image_path, bank_index=4)
                self.process_image(file_path=self.img_bank[-1])
                return
            if len(self.img_bank) > 5 and replacement_index > 4:
                self.process_image(file_path=self.img_bank[4])
                temp = self.img_bank[4]
                temp_r = self.img_bank[replacement_index]
                self.img_bank.pop(replacement_index)
                self.img_bank.pop(4)
                self.img_bank.insert(4, temp_r)
                self.img_bank.insert(replacement_index, temp)
                self.refresh_img_bank()
                return
            self.process_image(file_path=self.img_bank[4])

    def refresh_img_bank(self):
        if not self.img_bank:
            return
        stack_length = 5 if on_mac else 4
        for i, image in enumerate(self.img_bank):
            if i == stack_length:
                break
            icon_image = Image.open(image)
            icon = icon_image.resize((60, 60))
            icon = ImageTk.PhotoImage(icon)
            self.img_bank_tk_labels[i].configure(image=icon)
            self.img_bank_tk_labels[i].image = icon

    def dec_img_stack(self):
        stack_length = 5 if on_mac else 4
        if len(self.img_bank) <= stack_length:
            return
        temp = self.img_bank[0]
        self.img_bank.pop(0)
        self.img_bank.append(temp)
        self.refresh_img_bank()

    def inc_img_stack(self):
        stack_length = 5 if on_mac else 4
        if len(self.img_bank) <= stack_length:
            return
        temp = self.img_bank[-1]
        self.img_bank.pop(-1)
        self.img_bank.insert(0, temp)
        self.refresh_img_bank()

    def replace_icon(self, update_undo_history=True, index=None, given_path=''):
        if index is None:
            index = self.main.c4z_panel.current_icon
        elif 0 > index > len(self.main.c4z_panel.icons):
            return

        if update_undo_history:
            self.main.update_undo_history()

        if given_path:
            replacement_icon = Image.open(given_path)
        else:
            replacement_icon = Image.open(self.main.replacement_image_path)
        for icon in self.main.c4z_panel.icons[index].icons:
            if not os.path.isfile(bak_path := f'{icon.path}.bak'):
                shutil.copy(icon.path, bak_path)
            if icon.size_alt:
                new_icon = replacement_icon.resize(icon.size_alt)
                new_icon.save(icon.path)
                continue
            new_icon = replacement_icon.resize((icon.size, icon.size))
            new_icon.save(icon.path)
        self.main.c4z_panel.restore_button['state'] = NORMAL
        self.main.c4z_panel.restore_all_button['state'] = NORMAL
        self.main.c4z_panel.update_icon()
        self.main.ask_to_save = True

    def replace_all(self):
        self.main.update_undo_history()
        for i, icon in enumerate(self.main.c4z_panel.icons):
            if not self.main.c4z_panel.show_extra_icons.get() and icon.extra:
                continue
            self.replace_icon(update_undo_history=False, index=i)


class ExportPanel:
    def __init__(self, main):
        # Initialize Export Panel
        self.main = main
        self.x, self.y = (730, -50) if on_mac else (615, -50)
        self.abort = False

        # Labels
        self.panel_label = Label(main.root, text='Export', font=(label_font, 15))
        self.panel_label.place(x=145 + self.x, y=50 + self.y, anchor='n')

        self.driver_name_label = Label(main.root, text='Driver Name:')
        self.driver_name_label.place(x=65 + self.x, y=180 + self.y, anchor='w')

        # Buttons
        self.export_as_button = Button(main.root, text='Export As...', width=20, command=self.do_export, takefocus=0)
        self.export_as_button.place(x=145 + self.x, y=(250 if on_mac else 220) + self.y, anchor='n')
        self.export_as_button['state'] = DISABLED

        if not on_mac:
            self.export_button = Button(main.root, text='Quick Export', width=20,
                                        command=self.quick_export, takefocus=0)
            self.export_button.place(x=145 + self.x, y=220 + self.y, anchor='n')
            self.export_button['state'] = DISABLED

        # Entry
        self.driver_name_var = StringVar(value='New Driver')
        self.driver_name_var.trace('w', self.validate_driver_name)
        self.driver_name_entry = Entry(main.root, width=25, textvariable=self.driver_name_var)
        self.driver_name_entry.place(x=145 + self.x, y=190 + self.y, anchor='n')

        # Checkboxes
        self.inc_driver_version = IntVar(value=1)
        self.inc_driver_version.trace('w', self.update_driver_version)
        self.inc_driver_check = Checkbutton(main.root, text='increment driver version',
                                            variable=self.inc_driver_version, takefocus=0)
        self.inc_driver_check.place(x=63 + self.x, y=150 + self.y, anchor='w')

        self.include_backups = IntVar(value=1)
        self.include_backups_check = Checkbutton(main.root, text='include backup files',
                                                 variable=self.include_backups, takefocus=0)
        self.include_backups_check.place(x=63 + self.x, y=130 + self.y, anchor='w')

    if not on_mac:
        def quick_export(self, first_call=True, driver_name=''):
            if first_call:
                self.do_export(quick_export=True)
                return

            def confirm_overwrite():
                # Remove old driver
                if os.path.isfile(driver_path := f'{self.main.cur_dir}{driver_name}.c4z'):
                    os.remove(driver_path)
                self.export_file(driver_name)
                export_cleanup(as_abort=False)

            def export_cleanup(as_abort=True):
                if not as_abort:
                    self.main.driver_version_var.set(self.main.driver_version_new_var.get())
                    if self.inc_driver_version.get():
                        self.main.driver_version_new_var.set(str(int(self.main.driver_version_new_var.get()) + 1))
                # Restore original xml and lua file
                self.main.driver_xml.restore()
                if os.path.isfile(lua_bak_path := f'{self.main.instance_temp}driver/driver.lua.bak'):
                    os.remove(lua_path := f'{self.main.instance_temp}driver/driver.lua')
                    os.rename(lua_bak_path, lua_path)
                os.remove(xml_path := f'{self.main.instance_temp}driver/driver.xml')
                os.rename(f'{self.main.instance_temp}driver/driver.xml.bak', xml_path)

                overwrite_pop_up.destroy()

            # Overwrite file popup
            if os.path.isfile(f'{self.main.cur_dir}{driver_name}.c4z'):
                overwrite_pop_up = Toplevel(self.main.root)
                overwrite_pop_up.title('Overwrite')
                overwrite_pop_up.geometry('239x70')
                overwrite_pop_up.geometry(f'+{self.main.root.winfo_rootx() + self.x}+{self.main.root.winfo_rooty()}')
                overwrite_pop_up.protocol('WM_DELETE_WINDOW', export_cleanup)
                overwrite_pop_up.grab_set()
                overwrite_pop_up.focus()
                overwrite_pop_up.transient(self.main.root)
                overwrite_pop_up.resizable(False, False)

                confirm_label = Label(overwrite_pop_up, text='Would you like to overwrite the existing file?')
                confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

                yes_button = Button(overwrite_pop_up, text='Yes', width='10', command=confirm_overwrite)
                yes_button.grid(row=2, column=0, sticky='e', padx=5)

                no_button = Button(overwrite_pop_up, text='No', width='10', command=export_cleanup)
                no_button.grid(row=2, column=1, sticky='w', padx=5)
                self.abort = True
                return
            self.export_file(driver_name)

        def export_file(self, driver_name: str, path=None):
            random_tags = []

            def get_random_string():
                random_string = str(random.randint(1111111, 9999999))
                if random_string not in random_tags:
                    random_tags.append(random_string)
                    return random_string
                return get_random_string()

            if path is None:
                path = f'{self.main.cur_dir}{driver_name}.c4z'
            bak_files_dict = {}
            bak_files = []
            bak_folder = f'{self.main.instance_temp}bak_files/'

            # Backup and move all .bak files if not included
            if not self.include_backups.get():
                directories = list_all_sub_directories(f'{self.main.instance_temp}driver', include_root_dir=True)
                if os.path.isdir(bak_folder):
                    shutil.rmtree(bak_folder)
                os.mkdir(bak_folder)
                for directory in directories:
                    for file in os.listdir(directory):
                        if file.endswith('.bak'):
                            random_tag = get_random_string()
                            current_path = f'{directory}/{file}'
                            new_path = f'{bak_folder}{file}{random_tag}'
                            bak_files.append(current_path)
                            bak_files_dict[current_path] = new_path
                            shutil.copy(current_path, new_path)
                            os.remove(current_path)

            # Create .c4z file
            driver_zip = f'{self.main.instance_temp}{driver_name}.zip'
            driver_c4z = f'{self.main.instance_temp}{driver_name}.c4z'
            shutil.make_archive(self.main.instance_temp + driver_name, 'zip', f'{self.main.instance_temp}driver')
            base = os.path.splitext(driver_zip)[0]
            os.rename(driver_zip, f'{base}.c4z')
            shutil.copy(driver_c4z, path)
            os.remove(driver_c4z)

            # Restore .bak files
            if not self.include_backups.get():
                for file in bak_files:
                    shutil.copy(bak_files_dict[file], file)
                shutil.rmtree(bak_folder)

    def do_export(self, quick_export=False):
        main = self.main
        driver_xml = main.driver_xml
        # Format driver name
        driver_name = self.driver_name_var.get()
        temp = []
        for letter in driver_name:
            if letter in valid_chars:
                temp.append(letter)
        driver_name = ''.join(temp)
        self.driver_name_entry.delete(0, 'end')
        self.driver_name_entry.insert(0, driver_name)
        if not driver_name:
            self.driver_name_entry['background'] = 'pink'
            main.counter = 7
            main.root.after(150, main.blink_driver_name_entry)
            return

        # Multi-state related checks
        if main.multi_state_driver:
            if main.states_win:
                main.states_win.refresh()
            # Check State Validity
            invalid_states = False
            single_invalid_state = False
            for state in main.states:
                if state.bg_color in ('pink', 'cyan'):
                    self.abort = True
                    invalid_states = True
                    if not single_invalid_state:
                        single_invalid_state = True
                        continue
                    single_invalid_state = False
                    break
            if invalid_states:
                invalid_states_pop_up = Toplevel(main.root)
                if single_invalid_state:
                    invalid_states_pop_up.title('Invalid State Found')
                    label_text = 'Cannot Export: Invalid state label'
                else:
                    invalid_states_pop_up.title('Invalid States Found')
                    label_text = 'Cannot Export: Invalid state labels'
                invalid_states_pop_up.geometry('239x70')
                invalid_states_pop_up.geometry(f'+{main.root.winfo_rootx() + self.x}+{main.root.winfo_rooty()}')
                invalid_states_pop_up.grab_set()
                invalid_states_pop_up.focus()
                invalid_states_pop_up.transient(main.root)
                invalid_states_pop_up.resizable(False, False)
                confirm_label = Label(invalid_states_pop_up, text=label_text, justify='center')
                confirm_label.pack()
                exit_button = Button(invalid_states_pop_up, text='Cancel', width='10',
                                     command=invalid_states_pop_up.destroy, justify='center')
                exit_button.pack(pady=10)
            if self.abort:
                self.abort = False
                return

            # Update state names in lua file
            # state_name_changes = [original_name, new_name, original_name_lower, new_name_lower]
            state_name_changes = []
            if os.path.isfile(lua_path := f'{main.instance_temp}driver/driver.lua'):
                # lua file backup
                if os.path.isfile(lua_bak_path := f'{main.instance_temp}driver/driver.lua.bak'):
                    os.remove(lua_bak_path)
                shutil.copy(lua_path, lua_bak_path)
                for state in main.states:
                    state_name_changes.append([state.original_name, state.name_var.get()])
                for name_change in state_name_changes:
                    formatted_name = ''
                    for character in name_change[1]:
                        if character == ' ' or (
                                character not in letters and character not in capital_letters and
                                character not in numbers):
                            continue
                        if not formatted_name and character in letters:
                            formatted_name += capital_letters[letters.index(character)]
                            continue
                        formatted_name += character
                    if not formatted_name:
                        formatted_name = name_change[0]
                    name_change[1] = formatted_name
                pop_list = []
                for name_change in state_name_changes:
                    if name_change[0] == name_change[1]:
                        pop_list.insert(0, state_name_changes.index(name_change))
                        continue
                    name_change.append(name_change[0].replace(name_change[0][0],
                                                              letters[
                                                                  capital_letters.index(name_change[0][0])]))
                    name_change.append(name_change[1].replace(name_change[1][0],
                                                              letters[
                                                                  capital_letters.index(name_change[1][0])]))
                for index in pop_list:
                    state_name_changes.pop(index)

                # Modify lua file
                modified_lua_lines = []
                if on_mac:
                    with open(get_path(lua_path), errors='ignore') as driver_lua_file:
                        driver_lua_lines = driver_lua_file.readlines()
                else:
                    with open(lua_path, errors='ignore') as driver_lua_file:
                        driver_lua_lines = driver_lua_file.readlines()
                for line in driver_lua_lines:
                    new_line = line
                    for name_change in state_name_changes:
                        if f'{name_change[0]} ' in line or f'{name_change[2]} ' in line:
                            new_line = new_line.replace(f'{name_change[0]} ', f'{name_change[1]} ')
                            new_line = new_line.replace(f'{name_change[2]} ', f'{name_change[3]} ')
                        elif f"{name_change[0]}'" in line or f"{name_change[2]}'" in line:
                            new_line = new_line.replace(f"{name_change[0]}'", f"{name_change[1]}'")
                            new_line = new_line.replace(f"{name_change[2]}'", f"{name_change[3]}'")
                        elif f'{name_change[0]}"' in line or f'{name_change[2]}"' in line:
                            new_line = new_line.replace(f'{name_change[0]}"', f'{name_change[1]}"')
                            new_line = new_line.replace(f'{name_change[2]}"', f'{name_change[3]}"')
                        elif f'{name_change[0]}=' in line or f'{name_change[2]}=' in line:
                            new_line = new_line.replace(f'{name_change[0]}=', f'{name_change[1]}=')
                            new_line = new_line.replace(f'{name_change[2]}=', f'{name_change[3]}=')
                    modified_lua_lines.append(new_line)
                if on_mac:
                    with open(get_path(lua_path), 'w', errors='ignore') as driver_lua_file:
                        driver_lua_file.writelines(modified_lua_lines)
                else:
                    with open(lua_path, 'w', errors='ignore') as driver_lua_file:
                        driver_lua_file.writelines(modified_lua_lines)

            # Do multi-state related changes in xml
            if state_name_changes:
                for item_tag in driver_xml.get_tag('item'):
                    for state_name_change in state_name_changes:
                        if state_name_change[0] == item_tag.value:
                            item_tag.value = state_name_change[1]
                            break
                        if state_name_change[2] == item_tag.value:
                            item_tag.value = state_name_change[3]
                            break
                for name_tag in driver_xml.get_tag('name'):
                    for state_name_change in state_name_changes:
                        if state_name_change[0] == name_tag.value or name_tag.value.endswith(state_name_change[0]):
                            name_tag.value = name_tag.value.replace(state_name_change[0], state_name_change[1])
                            break
                        if state_name_change[2] == name_tag.value or name_tag.value.endswith(state_name_change[2]):
                            name_tag.value = name_tag.value.replace(state_name_change[2], state_name_change[3])
                            break
                for description_tag in driver_xml.get_tag('description'):
                    for state_name_change in state_name_changes:
                        if f'{state_name_change[0]} ' in description_tag.value:
                            description_tag.value = description_tag.value.replace(state_name_change[0],
                                                                                  state_name_change[1])
                            break
                        if f'{state_name_change[2]} ' in description_tag.value:
                            description_tag.value = description_tag.value.replace(state_name_change[2],
                                                                                  state_name_change[3])
                            break
                for state_tag in driver_xml.get_tag('state'):
                    for param in state_tag.parameters:
                        if param[0] == 'id':
                            for state_name_change in state_name_changes:
                                if state_name_change[0] == param[1]:
                                    param[1] = state_name_change[1]
                                    break
                                if state_name_change[2] == param[1]:
                                    param[1] = state_name_change[3]
                                    break

        # Check driver info variables
        if not all([main.driver_version_new_var.get(), main.driver_manufac_new_var.get(),
                    main.driver_creator_new_var.get()]):
            missing_driver_info_pop_up = Toplevel(main.root)
            missing_driver_info_pop_up.title('Missing Driver Information')
            label_text = 'Cannot Export: Missing driver info'
            missing_driver_info_pop_up.geometry('239x70')
            missing_driver_info_pop_up.geometry(f'+{main.root.winfo_rootx() + self.x}+{main.root.winfo_rooty()}')
            missing_driver_info_pop_up.grab_set()
            missing_driver_info_pop_up.focus()
            missing_driver_info_pop_up.transient(main.root)
            missing_driver_info_pop_up.resizable(False, False)
            confirm_label = Label(missing_driver_info_pop_up, text=label_text, justify='center')
            confirm_label.pack()
            exit_button = Button(missing_driver_info_pop_up, text='Cancel', width='10',
                                 command=missing_driver_info_pop_up.destroy, justify='center')
            exit_button.pack(pady=10)
            return

        # Confirm all connections have non-conflicting ids
        for conn in main.connections:
            conn.update_id(refresh=True)

        # Set restore point for xml object
        driver_xml.set_restore_point()

        # Update connection names
        for conn in main.connections:
            conn.tags[2].value = conn.name_entry_var.get()
            conn.tags[5].value = conn.type.get()

        # Update xml with new driver name
        driver_xml.get_tag('name')[0].value = driver_name
        modified_datestamp = str(datetime.now().strftime('%m/%d/%Y %H:%M'))
        if self.inc_driver_version.get() and \
                int(main.driver_version_var.get()) >= int(main.driver_version_new_var.get()):
            main.driver_version_new_var.set(str(int(main.driver_version_var.get()) + 1))
        driver_xml.get_tag('version')[0].value = main.driver_version_new_var.get()
        driver_xml.get_tag('modified')[0].value = modified_datestamp
        driver_xml.get_tag('creator')[0].value = main.driver_creator_new_var.get()
        driver_xml.get_tag('manufacturer')[0].value = main.driver_manufac_new_var.get()
        for param in driver_xml.get_tag('proxy')[0].parameters:
            if param[0] == 'name':
                param[1] = driver_name
        for icon_tag in driver_xml.get_tag('Icon'):
            result = re.search('driver/(.*)/icons', icon_tag.value)
            if result:
                result = result[1]
                icon_tag.value = icon_tag.value.replace(result, driver_name)

        # Backup xml file and write new xml
        if os.path.isfile(xml_bak_path := f'{main.instance_temp}driver/driver.xml.bak'):
            os.remove(xml_bak_path)
        os.rename(xml_path := f'{main.instance_temp}driver/driver.xml', xml_bak_path)
        if on_mac:
            with open(get_path(xml_path), 'w', errors='ignore') as out_file:
                out_file.writelines(driver_xml.get_lines())
        else:
            with open(xml_path, 'w', errors='ignore') as out_file:
                out_file.writelines(driver_xml.get_lines())
        if on_mac:
            random_tags = []

            def get_random_string():
                random_string = str(random.randint(1111111, 9999999))
                if random_string not in random_tags:
                    random_tags.append(random_string)
                    return random_string
                return get_random_string()

            # Save As Dialog
            out_file = filedialog.asksaveasfile(initialfile=f'{driver_name}.c4z',
                                                filetypes=[('Control4 Drivers', '*.c4z')])
            with contextlib.suppress(AttributeError):
                out_file_path = out_file.name
                out_file.close()
                flag_remove_empty_file = False
                if '.c4z' not in out_file_path:
                    flag_remove_empty_file = True
                    out_file_path += '.c4z'

                # Export file
                if os.path.isfile(out_file_path):
                    os.remove(out_file_path)
                bak_files_dict = {}
                bak_files = []
                bak_folder = f'{main.instance_temp}bak_files/'

                # Backup and move all .bak files if not included
                if not self.include_backups.get():
                    directories = list_all_sub_directories(f'{main.instance_temp}/driver', include_root_dir=True)
                    if os.path.isdir(bak_folder):
                        shutil.rmtree(bak_folder)
                    os.mkdir(bak_folder)
                    for directory in directories:
                        for file in os.listdir(directory):
                            if file.endswith('.bak'):
                                random_tag = get_random_string()
                                current_path = f'{directory}/{file}'
                                new_path = f'{bak_folder}{file}{random_tag}'
                                bak_files.append(current_path)
                                bak_files_dict[current_path] = new_path
                                shutil.copy(current_path, new_path)
                                os.remove(current_path)

                # Create .c4z file
                driver_zip = f'{main.instance_temp}{driver_name}.zip'
                driver_c4z = f'{main.instance_temp}{driver_name}.c4z'
                shutil.make_archive(main.instance_temp + driver_name, 'zip', f'{main.instance_temp}driver')
                base = os.path.splitext(driver_zip)[0]
                os.rename(driver_zip, f'{base}.c4z')
                shutil.copy(driver_c4z, out_file_path)
                os.remove(driver_c4z)

                # Restore .bak files
                if not self.include_backups.get():
                    for file in bak_files:
                        shutil.copy(bak_files_dict[file], file)
                    shutil.rmtree(bak_folder)

                if flag_remove_empty_file:
                    os.remove(out_file_path.replace('.c4z', ''))
        else:
            # Call export functions
            if quick_export:
                self.quick_export(first_call=False, driver_name=driver_name)
                if self.abort:
                    self.abort = False
                    return
            else:
                # Save As Dialog
                out_file = filedialog.asksaveasfile(initialfile=f'{driver_name}.c4z',
                                                    filetypes=[('Control4 Drivers', '*.c4z')])
                with contextlib.suppress(AttributeError):
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
        main.driver_version_var.set(main.driver_version_new_var.get())
        if self.inc_driver_version.get():
            main.driver_version_new_var.set(str(int(main.driver_version_new_var.get()) + 1))
        driver_xml.restore()
        if os.path.isfile(lua_bak_path := f'{main.instance_temp}driver/driver.lua.bak'):
            os.remove(lua_path := f'{main.instance_temp}driver/driver.lua')
            os.rename(lua_bak_path, lua_path)
        os.remove(xml_path := f'{main.instance_temp}driver/driver.xml')
        os.rename(f'{main.instance_temp}driver/driver.xml.bak', xml_path)

    def validate_driver_name(self, *_):
        if on_mac:
            if no_dark_mode or not is_dark_mode():
                self.driver_name_entry['background'] = light_entry_bg
            else:
                self.driver_name_entry['background'] = dark_entry_bg

        self.driver_name_var.set(''.join([char for char in self.driver_name_var.get() if char in valid_chars]))

        self.main.ask_to_save = True

    def update_driver_version(self, *_):
        self.main.ask_to_save = True
        # Update driver version if 'increment driver' is selected and new version value is <= last version value
        if not self.inc_driver_version.get():
            return
        if not self.main.driver_version_new_var.get() or not self.main.driver_version_var.get():
            return

        if int(self.main.driver_version_var.get()) >= int(self.main.driver_version_new_var.get()):
            self.main.driver_version_new_var.set(str(int(self.main.driver_version_var.get()) + 1))


class C4IS:
    def __init__(self, main: C4IconSwapper):
        if type(main) is not C4IconSwapper:
            raise TypeError
        # Root class
        self.driver_xml = main.driver_xml
        self.driver_manufac_var = main.driver_manufac_var.get()
        self.driver_manufac_new_var = main.driver_manufac_new_var.get()
        self.driver_creator_var = main.driver_creator_var.get()
        self.driver_creator_new_var = main.driver_creator_new_var.get()
        self.driver_ver_orig = main.driver_ver_orig.get()
        self.driver_version_var = main.driver_version_var.get()
        self.driver_version_new_var = main.driver_version_new_var.get()
        self.multi_state_driver = main.multi_state_driver
        self.states_orig_names = main.states_orig_names
        self.driver_selected = main.driver_selected
        self.replacement_selected = main.replacement_selected

        # State Panel
        self.states = [{'original_name': state.original_name, 'name_var': state.name_var.get()}
                       for state in main.states]

        # Connection Panel
        self.ids = main.taken_conn_ids
        self.connections = [{'id': conn.id, 'original': conn.original, 'in_id_group': conn.in_id_group,
                             'delete': conn.delete, 'prior_txt': conn.prior_txt, 'prior_type': conn.prior_type,
                             'tags': conn.tags, 'id_group': conn.id_group, 'type': conn.type.get(),
                             'name': conn.name_entry_var.get(), 'state': conn.enabled}
                            for conn in main.connections]

        # Export Panel
        self.driver_name_var = main.export_panel.driver_name_var.get()
        self.inc_driver_version = main.export_panel.inc_driver_version.get()
        self.include_backups = main.export_panel.include_backups.get()

        # C4z Panel
        self.extra_icons = main.c4z_panel.extra_icons
        self.show_extra_icons = main.c4z_panel.show_extra_icons.get()
        if main.driver_selected:
            shutil.make_archive(f'{main.instance_temp}driver', 'zip', f'{main.instance_temp}driver')
            with open(f'{main.instance_temp}driver.zip', 'rb') as driver_zip:
                self.driver_zip = driver_zip.read()
            os.remove(f'{main.instance_temp}driver.zip')
        else:
            self.driver_zip = None
        self.c4z_panel = {'restore': main.c4z_panel.restore_button['state'],
                          'restore_all': main.c4z_panel.restore_all_button['state'],
                          'prev': main.c4z_panel.prev_icon_button['state'],
                          'next': main.c4z_panel.next_icon_button['state']}

        # Replacement Panel
        if self.replacement_selected:
            self.replacement = Image.open(f'{main.instance_temp}replacement_icon.png')
        else:
            self.replacement = None
        self.img_bank = [Image.open(img) for img in main.replacement_panel.img_bank]

        self.replacement_panel = {'replace': main.replacement_panel.replace_button['state'],
                                  'replace_all': main.replacement_panel.replace_all_button['state'],
                                  'prev': main.replacement_panel.prev_icon_button['state'],
                                  'next': main.replacement_panel.next_icon_button['state']}


def list_all_sub_directories(directory: str, include_root_dir=False):
    subs = [path for dir_name in os.listdir(directory) if os.path.isdir(path := f'{directory}/{dir_name}')]
    for sub_sub in [list_all_sub_directories(sub_dir) for sub_dir in [*subs]]:
        subs.extend(sub_sub)
    return [directory, *sorted(subs)] if include_root_dir else sorted(subs)  # I don't remember why I used sort here


def find_valid_id(id_seed: int, list_of_ids: list, inc_count=0):
    return [id_seed, inc_count] if id_seed not in list_of_ids \
        else find_valid_id(id_seed + 1, list_of_ids, inc_count=inc_count + 1)


def is_valid_image(file_path: str):
    return any(file_path.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.jpeg'])


def natural_key(string: str):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]


if on_mac:
    def is_dark_mode():
        global no_dark_mode

        if no_dark_mode:
            return False

        if no_dark_mode is None:
            mac_ver_temp = platform.mac_ver()
            mac_ver = mac_ver_temp[0]
            ver_check = ''
            one_point = False
            for char in mac_ver:
                if char == '.':
                    if one_point:
                        break
                    one_point = True
                ver_check += char
            if float(ver_check) < 10.14:
                no_dark_mode = True
                return False
            no_dark_mode = False
        cmd = 'defaults read -g AppleInterfaceStyle'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        return bool(p.communicate()[0])


    def get_path(filename: str):
        name = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1]
        file = NSBundle.mainBundle().pathForResource_ofType_(name, ext)
        return file or os.path.realpath(filename)


if __name__ == '__main__':
    C4IconSwapper()
