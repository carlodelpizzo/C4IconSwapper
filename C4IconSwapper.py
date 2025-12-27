import filecmp
import os
import shutil
import copy
import base64
import contextlib
import itertools
import time
import random
import re
import pickle
import PIL.Image
import tkinter as tk
import Base64Assets
from tkinter import NORMAL, DISABLED, END, INSERT
from tkinter import ttk, filedialog, Toplevel, StringVar, IntVar, Checkbutton, Label, OptionMenu, Menu
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import ImageTk, Image
from datetime import datetime
from collections import deque
from XMLObject import XMLObject, XMLTag

version = '1.3'
label_font, light_entry_bg, dark_entry_bg = 'Arial', '#FFFFFF', '#282830'

letters = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
           'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z')
capital_letters = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                   'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z')
numbers = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')
valid_chars = ('_', '-', ' ', *letters, *capital_letters, *numbers)
conn_template = """
<connection>
    <id>0</id>
    <type>0</type>
    <connectionname>REPLACE</connectionname>
    <consumer>False</consumer>
    <linelevel>True</linelevel>
    <classes>
        <class>
            <classname>REPLACE</classname>
        </class>
    </classes>
</connection>
"""
selectable_connections = ['HDMI IN', 'HDMI OUT', 'COMPOSITE IN', 'COMPOSITE OUT', 'VGA IN', 'VGA OUT', 'COMPONENT IN',
                          'COMPONENT OUT', 'DVI IN', 'DVI OUT', 'STEREO IN', 'STEREO OUT', 'DIGITAL_OPTICAL IN',
                          'DIGITAL_OPTICAL OUT', 'IR_OUT']


class C4IS:
    def __init__(self, main: object):
        if type(main) is not C4IconSwapper:
            raise TypeError
        if not main:
            main = C4IconSwapper()  # For IDE UnresolvedReferences errors
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
        self.ids = main.conn_ids
        self.connections = [{'id': conn.id, 'original': conn.original, 'in_id_group': conn.in_id_group,
                             'delete': conn.delete, 'prior_txt': conn.prior_txt, 'prior_type': conn.prior_type,
                             'tag': conn.tag, 'id_group': conn.id_group, 'type': conn.type.get(),
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
            shutil.make_archive(driver_path_noext := os.path.join(main.temp_dir, 'driver'), 'zip', driver_path_noext)
            with open(driver_path := f'{driver_path_noext}.zip', 'rb') as driver_zip:
                self.driver_zip = driver_zip.read()
            os.remove(driver_path)
        else:
            self.driver_zip = None
        self.c4z_panel = {'restore': main.c4z_panel.restore_button['state'],
                          'restore_all': main.c4z_panel.restore_all_button['state'],
                          'prev': main.c4z_panel.prev_icon_button['state'],
                          'next': main.c4z_panel.next_icon_button['state']}

        # Replacement Panel
        if self.replacement_selected:
            self.replacement = Image.open(os.path.join(main.temp_dir, 'replacement_icon.png'))
        else:
            self.replacement = None
        self.img_stack = [Image.open(img) for img in main.replacement_panel.img_stack]

        self.replacement_panel = {'replace': main.replacement_panel.replace_button['state'],
                                  'replace_all': main.replacement_panel.replace_all_button['state'],
                                  'prev': main.replacement_panel.prev_icon_button['state'],
                                  'next': main.replacement_panel.next_icon_button['state']}


class C4IconSwapper:
    class Connection:
        def __init__(self, main):
            self.main = main
            self.id = 0
            self.original, self.in_id_group, self.delete, self.enabled = False, False, False, False
            self.prior_txt, self.prior_type = '', ''
            self.tag = None
            self.id_group = []
            self.name_entry_var = StringVar(value='Connection Name...')
            self.type = StringVar(value='HDMI IN')

        def update_id(self, *_, refresh=False):
            if not self.tag:
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
            # TODO: Replace with dict
            if ' IN' in conn_type:
                conn_type = conn_type.replace(' IN', '')
                if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                    valid_id = find_valid_id(2000, self.main.conn_ids)
                    self.tag.get_tag('type').set_value('5')
                elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                    valid_id = find_valid_id(4000, self.main.conn_ids)
                    self.tag.get_tag('type').set_value('6')
            elif ' OUT' in conn_type:
                conn_type = conn_type.replace(' OUT', '')
                if conn_type in ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI']:
                    valid_id = find_valid_id(1900, self.main.conn_ids)
                    self.tag.get_tag('type').set_value('5')
                elif conn_type in ['STEREO', 'DIGITAL_OPTICAL']:
                    valid_id = find_valid_id(3900, self.main.conn_ids)
                    self.tag.get_tag('type').set_value('6')
            if conn_type == 'IR_OUT':
                valid_id = find_valid_id(1, self.main.conn_ids)
                self.tag.get_tag('type').set_value('1')

            if self.id in self.main.conn_ids:
                self.main.conn_ids.pop(self.main.conn_ids.index(self.id))
            self.id = valid_id[0]
            self.tag.get_tag('id').set_value(str(self.id))
            self.main.conn_ids.append(self.id)

    class State:
        def __init__(self, name: str):
            self.original_name = name
            self.name_var = StringVar(value=name)
            background = light_entry_bg
            self.bg_color = background

    class ConnectionsWin:
        class ConnectionEntry:
            def __init__(self, main, conn_obj, x_pos: int, y_pos: int):
                # Initialize Connection UI Object
                self.window = main.window
                self.main = main.main
                self.conn_object = conn_obj
                self.x, self.y = x_pos, y_pos

                # Entry
                self.name_entry_var = conn_obj.name_entry_var
                self.name_entry_var.trace('w', self.name_update)
                self.name_entry = tk.Entry(self.window, width=20, textvariable=self.name_entry_var)
                self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
                if not self.conn_object.enabled:
                    self.name_entry['state'] = DISABLED

                # Dropdown
                self.type = conn_obj.type
                self.type_menu = OptionMenu(self.window, self.type, *selectable_connections)
                self.type_menu.place(x=self.x + 160, y=self.y, anchor='w')
                self.type.trace('w', self.conn_object.update_id)
                if not self.conn_object.enabled:
                    self.type_menu['state'] = DISABLED

                # Buttons
                self.add_button = tk.Button(self.window, text='Add', width=3, command=self.enable, takefocus=0)
                if self.conn_object.enabled or self.conn_object.original:
                    self.add_button.place(x=-420, y=-420, anchor='w')
                else:
                    self.add_button.place(x=self.x, y=self.y, anchor='w')
                if not self.main.driver_selected:
                    self.add_button['state'] = DISABLED

                self.x_button = tk.Button(self.window, text='x', width=1, command=self.disable, takefocus=0)
                if self.conn_object.enabled and not self.conn_object.original:
                    self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
                else:
                    self.x_button.place(x=-420, y=-420, anchor='w')

                self.del_button = tk.Button(self.window, text='Del', width=3, command=self.flag_delete, takefocus=0)
                if self.conn_object.original:
                    self.del_button.place(x=self.x, y=self.y, anchor='w')
                else:
                    self.del_button.place(x=-420, y=-420, anchor='w')
                if self.conn_object.delete:
                    self.del_button['text'] = 'Keep'
                    self.del_button['width'] = 4
                    self.del_button.place(x=self.x + self.del_button.winfo_x() - 6, y=self.y)

            def enable(self):
                self.conn_object.enabled = True
                self.name_entry['state'] = NORMAL
                self.type_menu['state'] = NORMAL
                self.add_button.place(x=-420, y=-420, anchor='w')
                self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
                if self.conn_object.tag:
                    self.conn_object.tag.delete = False
                self.name_entry['takefocus'] = 1

            def disable(self):
                self.conn_object.enabled = False
                self.name_entry['state'] = DISABLED
                self.type_menu['state'] = DISABLED
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.x_button.place(x=-420, y=-420, anchor='w')
                if self.conn_object.tag:
                    self.conn_object.tag.delete = True
                self.name_entry['takefocus'] = 0

            def flag_delete(self):
                if not self.conn_object.original:
                    return
                if not self.conn_object.delete:
                    self.conn_object.delete = True
                    if self.conn_object.tag:
                        self.conn_object.tag.delete = True
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
                            self.conn_object.tag.delete = True
                        self.conn_object.tag.delete = True
                    return
                self.conn_object.delete = False
                if self.conn_object.tag:
                    self.conn_object.tag.delete = False
                self.name_entry['state'] = NORMAL
                self.name_entry_var.set(self.conn_object.prior_txt)
                self.conn_object.prior_txt = ''
                self.name_entry['state'] = DISABLED
                self.type.set(self.conn_object.prior_type)
                self.conn_object.prior_type = ''
                if self.conn_object.tag:
                    self.conn_object.tag.delete = False
                self.del_button['text'] = 'Del'
                self.del_button['width'] = 3
                self.del_button.place(x=self.del_button.winfo_x() + 6, y=self.y)

            def name_update(self, *_):
                self.main.ask_to_save = True

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
                    self.add_button.place(x=-420, y=-420, anchor='w')
                self.add_button.place(x=self.x, y=self.y, anchor='w')
                self.add_button['state'] = NORMAL if self.main.driver_selected else DISABLED
                if self.conn_object.enabled and not self.conn_object.original:
                    self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
                else:
                    self.x_button.place(x=-420, y=-420, anchor='w')

                if self.conn_object.original:
                    self.del_button.place(x=self.x, y=self.y, anchor='w')
                else:
                    self.del_button.place(x=-420, y=-420, anchor='w')
                if self.conn_object.delete:
                    self.del_button['text'] = 'Keep'
                    self.del_button['width'] = 4
                    self.del_button.place(x=self.x + self.del_button.winfo_x() - 6, y=self.y)

        def __init__(self, main):
            self.main = main

            # Initialize window
            self.window = Toplevel(self.main.root)
            self.window.focus()
            self.window.protocol('WM_DELETE_WINDOW', self.main.close_connections)
            self.window.title('Edit Driver Connections')
            self.window.geometry('975x250')
            x_spacing, y_spacing = 330, 40
            self.window.geometry(f'+{self.main.root.winfo_rootx()}+{self.main.root.winfo_rooty()}')
            self.window.resizable(False, False)

            self.connections = [self.ConnectionEntry(self, self.main.connections[(x * 6) + y],
                                                     x * x_spacing + 15, y * y_spacing + 25)
                                for x, y in itertools.product(range(3), range(6))]

        def refresh(self):
            for conn_entry in self.connections:
                conn_entry.refresh()

    class DriverInfoWin:
        def __init__(self, main):
            self.main = main

            # Initialize window
            self.window = Toplevel(self.main.root)
            self.window.focus()
            self.window.protocol('WM_DELETE_WINDOW', self.main.close_driver_info)
            self.window.title('Edit Driver Info')
            self.window.geometry('255x240')
            self.window.geometry(f'+{self.main.root.winfo_rootx() + self.main.export_panel.x}+'
                                 f'{self.main.root.winfo_rooty()}')
            self.window.resizable(False, False)

            # Validate driver version
            if (self.main.export_panel.inc_driver_version.get() and self.main.driver_version_var.get() and
                    self.main.driver_version_new_var.get() and
                    int(self.main.driver_version_new_var.get()) <= int(self.main.driver_version_var.get())):
                self.main.driver_version_new_var.set(str(int(self.main.driver_version_var.get()) + 1))

            # Labels
            instance_id_label = tk.Label(self.window, text=f'program instance id: {self.main.instance_id}')

            man_y = 20
            man_arrow = tk.Label(self.window, text='\u2192', font=('', 15))

            creator_y = man_y + 55
            creator_arrow = tk.Label(self.window, text='\u2192', font=('', 15))

            version_y = creator_y + 55
            version_arrow = tk.Label(self.window, text='\u2192', font=('', 15))

            font_size = 10
            driver_ver_orig_label = tk.Label(self.window, text='Original Version:',
                                             font=(label_font, 8))

            driver_man_label = tk.Label(self.window, text='Driver Manufacturer',
                                        font=(label_font, font_size))

            driver_creator_label = tk.Label(self.window, text='Driver Creator',
                                            font=(label_font, font_size))

            driver_ver_label = tk.Label(self.window, text='Driver Version',
                                        font=(label_font, font_size))

            # Entry
            entry_width = 17
            driver_man_entry = tk.Entry(self.window, width=entry_width,
                                        textvariable=self.main.driver_manufac_var)
            driver_man_entry['state'] = DISABLED
            self.driver_man_new_entry = tk.Entry(self.window, width=entry_width,
                                                 textvariable=self.main.driver_manufac_new_var)
            self.main.driver_manufac_new_var.trace('w', lambda name, index, mode: self.main.validate_man_and_creator(
                string_var=self.main.driver_manufac_new_var, entry=self.driver_man_new_entry))

            driver_creator_entry = tk.Entry(self.window, width=entry_width,
                                            textvariable=self.main.driver_creator_var)
            driver_creator_entry['state'] = DISABLED
            self.driver_creator_new_entry = tk.Entry(self.window, width=entry_width,
                                                     textvariable=self.main.driver_creator_new_var)
            self.main.driver_creator_new_var.trace('w', lambda name, index, mode: self.main.validate_man_and_creator(
                string_var=self.main.driver_creator_new_var, entry=self.driver_creator_new_entry))

            driver_ver_entry = tk.Entry(self.window, width=entry_width,
                                        textvariable=self.main.driver_version_var)
            driver_ver_entry['state'] = DISABLED
            self.driver_ver_new_entry = tk.Entry(self.window, width=entry_width,
                                                 textvariable=self.main.driver_version_new_var)
            self.driver_ver_new_entry.bind('<FocusOut>', self.main.export_panel.update_driver_version)
            self.main.driver_version_new_var.trace('w', self.main.validate_driver_ver)
            driver_ver_orig_entry = tk.Entry(self.window, width=6, textvariable=self.main.driver_ver_orig)
            driver_ver_orig_entry['state'] = DISABLED
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

    class StatesWin:
        class StateEntry:
            def __init__(self, main, state_obj, x_pos: int, y_pos: int, label='State#:'):
                # Initialize Driver State UI Object
                self.main = main.main
                self.window = main.window
                self.state_object = state_obj
                self.original_name = state_obj.original_name
                self.x, self.y = x_pos, y_pos

                # Label
                self.name_label = tk.Label(self.window, text=label)
                self.name_label.place(x=self.x + 35, y=self.y, anchor='e')

                # Entry
                self.name_var = StringVar(value=state_obj.name_var.get())
                self.name_var.trace('w', self.validate_state)
                self.name_entry = tk.Entry(self.window, width=20, textvariable=self.name_var)
                self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
                self.name_entry['background'] = state_obj.bg_color
                if not self.main.multi_state_driver:
                    self.name_entry['state'] = DISABLED

            # TODO: Improve this
            def validate_state(self, *_):
                def state_object(obj_index):
                    return self.main.states_win.states[obj_index]

                def original_name_check(obj_index):
                    orig_name_check = [*self.main.states_orig_names]
                    orig_name_check.pop(obj_index)
                    if (state_object(obj_index).state_object.bg_color != 'pink' and
                            state_object(obj_index).name_var.get() in orig_name_check):
                        state_object(obj_index).state_object.bg_color = 'cyan'

                self.main.ask_to_save = True
                if not self.main.states_win:
                    return
                self.format_state_name()
                self_index = self.main.states_win.states.index(self)
                background_color = light_entry_bg
                in_dupe_list = False
                if not (self_name := self.name_var.get()):
                    self.state_object.bg_color = 'pink'
                    in_dupe_list = True
                for dupe_list in self.main.state_dupes:
                    if (self_index in dupe_list and
                            ((dupe_list[0] is not self_index and state_object(dupe_list[0]).name_var.get() != self_name)
                             or state_object(dupe_list[-1]).name_var.get() != self_name)):
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
                    state_names = [state.name_var.get() for state in self.main.states_win.states if state is not self]
                    if self_name in state_names:
                        dupe_list = [self.main.states_win.states.index(state)
                                     for state in self.main.states_win.states if state.name_var.get() == self_name]
                        for state_index in dupe_list:
                            state_object(state_index).state_object.bg_color = 'pink'
                        self.main.state_dupes.append(dupe_list)
                    else:
                        self.state_object.bg_color = background_color

                original_name_check(self_index)

                for state in self.main.states_win.states:
                    state.refresh(bg_only=True)
                self.state_object.name_var.set(self_name)

            # TODO: Improve this
            def format_state_name(self):
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

            def refresh(self, bg_only=False):
                self.name_entry['background'] = self.state_object.bg_color
                if bg_only:
                    return
                self.name_var.set(self.state_object.name_var.get())

        def __init__(self, main):
            self.main = main

            # Initialize window
            self.window = Toplevel(self.main.root)
            self.window.focus()
            self.window.protocol('WM_DELETE_WINDOW', self.main.close_states)
            self.window.title('Edit Driver States')
            x_spacing, y_spacing = 200, 34
            self.window.geometry('385x287')
            self.window.geometry(f'+{self.main.root.winfo_rootx()}+{self.main.root.winfo_rooty()}')
            self.window.resizable(False, False)

            self.states = []
            x_offset, y_offset = (10, 30)
            self.states.extend(
                self.StateEntry(self, self.main.states[i], int(i / 7) * x_spacing + x_offset,
                                (i % 7) * y_spacing + y_offset, label=f'state{str(i + 1)}:')
                for i in range(13))

        def refresh(self):
            for state in self.states:
                state.refresh()

    class C4zPanel:
        class SubIcon:
            def __init__(self, root_path: str, path: str, name: str, size: int):
                # Initialize Icon
                self.root = root_path  # Path to directory containing image
                self.path = path  # Full path to image file
                self.name, self.size = name, size
                self.size_alt, self.name_alt, self.alt_format = None, '', False
                # TODO: Improve using RegEx
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

        # TODO: Update to use tk images; add .bak flag
        class Icon:
            def __init__(self, icons: list, extra=False):
                # Initialize Icon Group
                self.name, self.name_orig = icons[0].name, icons[0].name
                self.name_alt, self.path, self.root = icons[0].name_alt, icons[0].path, icons[0].root
                self.icons, self.extra, self.dupe_number = icons, extra, 0

        def __init__(self, main):
            # Initialize C4z Panel
            self.main = main
            self.x, self.y = 5, 20
            self.current_icon, self.extra_icons = 0, 0
            self.icons = []
            self.valid_connections = ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI', 'STEREO', 'DIGITAL_OPTICAL',
                                      *selectable_connections]

            # Buttons
            self.open_file_button = tk.Button(self.main.root, text='Open', width=10, command=self.load_c4z, takefocus=0)
            self.restore_button = tk.Button(self.main.root, text='Restore\nOriginal Icon', command=self.restore_icon,
                                            takefocus=0)
            self.restore_button['state'] = DISABLED

            self.restore_all_button = tk.Button(self.main.root, text='Restore All',
                                                command=self.restore_all, takefocus=0)
            self.restore_all_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.main.root, text='Prev', command=self.prev_icon, width=5, takefocus=0)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.main.root, text='Next', command=self.next_icon, width=5, takefocus=0)
            self.next_icon_button['state'] = DISABLED

            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')
            self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)

            # Entry
            self.file_entry_field = tk.Entry(self.main.root, width=25, takefocus=0)
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_c4z)
            self.file_entry_field.insert(0, 'Select .c4z file...')
            self.file_entry_field['state'] = DISABLED

            # Checkbox
            # TODO: Disable show extra icons checkbox when it is inapplicable
            self.show_extra_icons = IntVar(value=0)
            self.show_extra_icons.trace('w', self.toggle_extra_icons)
            self.show_sub_icons_check = Checkbutton(self.main.root, text='show extra icons',
                                                    variable=self.show_extra_icons, takefocus=0)
            self.show_sub_icons_check.place(x=self.x + 177, y=self.y + 176, anchor='nw')

            # Labels
            self.panel_label = tk.Label(self.main.root, text='Driver Selection', font=(label_font, 15))

            self.blank_image_label = tk.Label(self.main.root, image=self.main.blank)
            self.blank_image_label.image = self.main.blank
            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')

            self.icon_label = tk.Label(self.main.root, text='0 of 0')
            self.icon_label.place(x=108 + self.x, y=176 + self.y, anchor='n')

            self.icon_name_label = tk.Label(self.main.root, text='icon name')
            self.icon_name_label.place(x=108 + self.x, y=193 + self.y, anchor='n')

            self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')
            self.blank_image_label.drop_target_register(DND_FILES)
            self.blank_image_label.dnd_bind('<<Drop>>', self.drop_in_c4z)

        def toggle_extra_icons(self, *_):
            if not self.main.driver_selected:
                return
            if not self.show_extra_icons.get() and self.main.c4z_panel.icons[self.main.c4z_panel.current_icon].extra:
                self.next_icon()
            self.update_icon()

        # TODO: Combine loading generic drivers
        def load_gen_driver(self):
            if self.main.ask_to_save:
                self.main.root.wait_window(self.main.ask_to_save_dialog(on_exit=False))
            # Load generic two-state driver from Base64Assets
            gen_driver_path = os.path.join(self.main.temp_dir, 'generic.c4z')
            if self.file_entry_field.get() == gen_driver_path:
                return
            with open(gen_driver_path, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(Base64Assets.generic_driver))

            if os.path.isdir(temp_driver_path := os.path.join(self.main.temp_dir, 'driver')):
                shutil.rmtree(temp_driver_path)

            shutil.unpack_archive(gen_driver_path, temp_driver_path, 'zip')
            os.remove(gen_driver_path)

            sizes = [(70, 70), (90, 90), (300, 300), (512, 512)]
            pictures = os.listdir(self.main.device_icon_dir)
            for picture in pictures:
                resized_icon = Image.open(img_path := os.path.join(self.main.device_icon_dir, picture))
                for size in sizes:
                    new_icon = resized_icon.resize(size)
                    new_icon.save(img_path.replace('1024', str(size[0])))

            shutil.make_archive(gen_driver_path.replace('.c4z', ''), 'zip',
                                os.path.join(self.main.temp_dir, 'driver'))

            os.rename(gen_driver_path.replace('.c4z', '.zip'), gen_driver_path)

            self.load_c4z(gen_driver_path)
            self.main.export_panel.driver_name_entry.delete(0, 'end')
            self.main.export_panel.driver_name_entry.insert(0, 'New Driver')
            self.main.ask_to_save = False
            os.remove(gen_driver_path)

        # TODO: Combine loading generic drivers
        def load_gen_multi(self, show_loading_image=True):
            if self.main.ask_to_save:
                self.main.root.wait_window(self.main.ask_to_save_dialog(on_exit=False))
            # Shows loading image then recalls function with show_loading_image=False
            if show_loading_image:
                self.show_loading_image()
                return
            # Load generic multi-state driver from Base64Assets
            multi_driver_path = os.path.join(self.main.temp_dir, 'multi generic.c4z')
            if self.file_entry_field.get() == multi_driver_path:
                return
            with open(multi_driver_path, 'wb') as gen_driver:
                gen_driver.write(base64.b64decode(Base64Assets.generic_multi))

            if os.path.isdir(temp_driver_path := os.path.join(self.main.temp_dir, 'driver')):
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

            shutil.make_archive(multi_driver_path.replace('.c4z', ''), 'zip',
                                os.path.join(self.main.temp_dir, 'driver'))

            os.rename(multi_driver_path.replace('.c4z', '.zip'), multi_driver_path)

            self.load_c4z(multi_driver_path)
            self.main.export_panel.driver_name_entry.delete(0, 'end')
            self.main.export_panel.driver_name_entry.insert(0, 'New Driver')
            self.main.ask_to_save = False
            os.remove(multi_driver_path)
            os.remove(os.path.join(self.main.temp_dir, 'loading_icon.gif'))
            return

        # TODO: Store loading image as tk object in b64
        def show_loading_image(self):
            with open(loading_img_path := os.path.join(self.main.temp_dir, 'loading_icon.gif'), 'wb') as loading_img:
                loading_img.write(base64.b64decode(Base64Assets.loading_icon))
            icon_image = Image.open(loading_img_path)
            icon = ImageTk.PhotoImage(icon_image)
            self.blank_image_label.configure(image=icon)
            self.blank_image_label.image = icon
            self.main.root.after(1, self.main.recall_load_gen_multi)

        # TODO: Update to use tk images
        def update_icon(self):
            if not self.icons:
                return
            if abs(self.current_icon) >= len(self.icons):
                self.current_icon = abs(self.current_icon) % len(self.icons)
            icon_image = Image.open(self.icons[self.current_icon].path)
            icon = icon_image.resize((128, 128))
            icon = ImageTk.PhotoImage(icon)
            self.blank_image_label.configure(image=icon)
            self.blank_image_label.image = icon

            if not self.show_extra_icons.get() and self.extra_icons:
                self.icon_label.config(text=f'icon: {str(self.current_icon + 1)} of '
                                            f'{str(len(self.icons) - self.extra_icons)} ({str(len(self.icons))})')
            else:
                self.icon_label.config(text=f'icon: {str(self.current_icon + 1)} of {str(len(self.icons))}')
            self.icon_name_label.config(text=f'name: {self.icons[self.current_icon].name}')

        def load_c4z(self, given_path=None, recovery=False):
            # TODO: Improve code
            def get_icons(directory):
                if not os.path.isdir(directory):
                    return None
                icons_out = []
                sub_list = []
                path_list = os.listdir(directory)
                path_list.sort()
                for string in path_list:
                    if '.bak' in string or string[0] == '.':
                        continue
                    if os.path.isdir(sub_path := os.path.join(directory, string)):
                        sub_list.append(sub_path)
                        continue
                    if 'device_lg' in string or 'icon_large' in string:
                        icon_objects.append(self.SubIcon(directory, sub_path, 'device', 32))
                        continue
                    elif 'device_sm' in string or 'icon_small' in string:
                        icon_objects.append(self.SubIcon(directory, sub_path, 'device', 16))
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
                    temp_img = PIL.Image.open(sub_path)
                    temp_size = str(temp_img.size[0])
                    if temp_img.size[0] != temp_img.size[1]:
                        alt_sized = True
                    icons_out.append(self.SubIcon(directory, sub_path, temp_name, int(temp_size)))
                    if alt_sized:
                        icons_out[-1].size_alt = temp_img.size
                    temp_img.close()

                if not sub_list:
                    return icons_out
                for sub_dir in sorted(sub_list):
                    icons_out.extend(get_icons(sub_dir))
                return icons_out

            # TODO: Improve code; Code runs when loading some drivers, need to re-evaluate
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
                                print('debug testing: recalled check_dupe_names...')
                                print('this code should never run')
                                icon_cmp1.name = f'{icon_cmp1.name} ({str(icon_cmp1.dupe_number)})'
                                continue
                            icon_cmp0.name = icon_cmp0.name_alt
                            icon_cmp1.name = icon_cmp1.name_alt
                            break
                if recall:
                    check_dupe_names(recalled=True)

            if self.main.ask_to_save:
                self.main.root.wait_window(self.main.ask_to_save_dialog(on_exit=False))

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
            temp_bak = os.path.join(self.main.temp_dir, 'temp_driver_backup')
            icons_bak = None
            if self.icons:
                icons_bak = self.icons
                if os.path.isdir(temp_driver_path := os.path.join(self.main.temp_dir, 'driver')):
                    shutil.copytree(temp_driver_path, temp_bak)

            # File select dialog
            if given_path is None and not recovery:
                filename = filedialog.askopenfilename(filetypes=[('Control4 Drivers', '*.c4z *.zip')])
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
            if os.path.isdir(driver_folder := os.path.join(self.main.temp_dir, 'driver')) and not recovery:
                shutil.rmtree(driver_folder)

            # Unpack selected driver
            if not recovery:
                shutil.unpack_archive(filename, driver_folder, 'zip')

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
                        self.icons.append(self.Icon(icon_group, extra=True))
                    else:
                        self.icons.append(self.Icon(icon_group))
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
                                self.icons.append(self.Icon(icon_group, extra=True))
                                added = True
                                break
                        if not added:
                            self.icons.append(self.Icon(icon_group))
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

            # TODO: Examine this code for efficiency
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

            # TODO: Update using os functions
            # Update entry with driver file path
            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, filename)
            self.file_entry_field['state'] = 'readonly'
            orig_file_path = filename
            orig_driver_name = ''
            for i in reversed(range(len(orig_file_path) - 1)):
                if orig_file_path[i] == '/' or orig_file_path[i] == '\\':
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
            self.main.driver_xml = XMLObject(os.path.join(self.main.temp_dir, 'driver', 'driver.xml'))
            if man_tag := self.main.driver_xml.get_tag('manufacturer'):
                self.main.driver_manufac_var.set(man_tag.value())
            if creator_tag := self.main.driver_xml.get_tag('creator'):
                self.main.driver_creator_var.set(creator_tag.value())
            if version_tag := self.main.driver_xml.get_tag('version'):
                # TODO: Redo using RegEx
                self.main.driver_ver_orig.set(version_tag.value())
                temp_str = ''
                for char in version_tag.value():
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
            if id_tags := self.main.driver_xml.get_tags('id'):
                self.main.conn_ids = []
                for id_tag in id_tags:
                    with contextlib.suppress(ValueError):
                        if int(id_tag.value()) not in self.main.conn_ids:
                            self.main.conn_ids.append(int(id_tag.value()))

            # TODO: Rewrite using RegEx or maybe a Lua parser?
            # Check Lua file for multi-state
            self.main.multi_state_driver = False
            self.main.edit.entryconfig(self.main.states_pos, state=DISABLED)
            if os.path.isfile(lua_path := os.path.join(self.main.temp_dir, 'driver', 'driver.lua')):
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
                self.main.export_panel.export_button['state'] = NORMAL
                self.main.export_panel.export_as_button['state'] = NORMAL
            # Update 'Restore All' button in driver panel
            done = False
            self.restore_all_button['state'] = DISABLED
            for path in list_all_sub_directories(driver_folder):
                for file in os.listdir(path):
                    # TODO: Double check this RegEx works properly
                    if re.search(r'(?<!\.xml)\.bak[^.]*$', file):
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

        # TODO: Update to use tk images
        def restore_icon(self, update_undo_history=True, index=None):
            if index is None:
                index = self.current_icon
            elif 0 > index > len(self.icons):
                return

            if update_undo_history:
                self.main.update_undo_history()

            for icon in self.icons[index].icons:
                if os.path.isfile(f'{icon.path}.bak'):
                    shutil.copy(f'{icon.path}.bak', icon.path)
                    os.remove(f'{icon.path}.bak')
            self.restore_button['state'] = DISABLED
            if not any(os.path.isfile(f'{group.icons[0].path}.bak') for group in self.icons):
                self.restore_all_button['state'] = DISABLED
            self.update_icon()
            self.main.ask_to_save = True

        def restore_all(self):
            self.main.update_undo_history()
            for i in range(len(self.icons)):
                self.restore_icon(update_undo_history=False, index=i)
            self.restore_button['state'] = DISABLED
            self.restore_all_button['state'] = DISABLED
            self.update_icon()

        # TODO: Update to use Icon.bak flag
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

        # TODO: Update to use Icon.bak flag
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

        def get_connections(self):
            if (not os.path.isfile(os.path.join(self.main.temp_dir, 'driver', 'driver.xml')) or
                    not self.main.driver_selected):
                return
            # TODO: Maybe write new function for reinitialization?
            for conn in self.main.connections:
                conn.__init__(self.main)

            # Get connections from XML object
            connections = []
            if classname_tags := self.main.driver_xml.get_tags('classname'):
                for classname_tag in reversed(classname_tags):
                    if classname_tag.value() not in self.valid_connections:
                        classname_tags.pop(classname_tags.index(classname_tag))
                for classname_tag in classname_tags:
                    class_tag, connection_tag, connectionname_tag, id_tag, type_tag = None, None, None, None, None
                    for parent in reversed(classname_tag.get_parents()):
                        if not parent:
                            continue
                        if (parent_name := parent.name) == 'class':
                            class_tag = parent
                        elif parent_name == 'connection':
                            connection_tag = parent
                            for child in connection_tag.elements:
                                if type(child) is not XMLTag:
                                    continue
                                if (child_name := child.name) == 'type':
                                    type_tag = child
                                elif child_name == 'id':
                                    id_tag = child
                                elif child_name == 'connectionname':
                                    connectionname_tag = child
                    if all([id_tag, connection_tag, class_tag, connectionname_tag, type_tag]):
                        connections.append([connectionname_tag.value(), classname_tag.value(), id_tag.value(),
                                            connection_tag, class_tag, connectionname_tag, id_tag, type_tag,
                                            classname_tag])

            # Check that number of connections does not exceed maximum
            if len(connections) > len(self.main.connections):
                conn_range = len(self.main.connections) - 1
            else:
                conn_range = len(connections)

            # Assign panel connections to XML tags and update UI
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
                self.main.connections[i].tag = connections[i][3]
                self.main.connections[i].original = True

            # Fill in remaining empty connections
            for conn in self.main.connections:
                if conn.original:
                    continue
                new_conn = XMLTag(xml_string=conn_template)
                name_tag = new_conn.get_tag('connectionname')
                name_tag.value = 'Connection Name...'
                new_conn.get_tag('classname').set_value('HDMI IN')
                new_conn.delete = True
                self.main.driver_xml.get_tag('connections').add_element(new_conn)
                conn.tag = new_conn

            # Form id groups
            for group in id_groups:
                for conn in group[1:]:
                    new_group = [conn0 for conn0 in group if conn0 != conn]
                    conn.id_group = new_group
            for conn in self.main.connections:
                conn.update_id()

        # TODO: Rewrite using Regex
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
                    self.main.replacement_panel.load_replacement(given_path=file)
                return

            if dropped_path.endswith('.c4z'):
                self.load_c4z(given_path=dropped_path)
            elif is_valid_image(dropped_path):
                self.main.replacement_panel.load_replacement(given_path=dropped_path)
            elif '.' not in dropped_path:
                image_paths = os.listdir(dropped_path)
                for new_img_path in image_paths:
                    self.main.replacement_panel.load_replacement(given_path=os.path.join(dropped_path, new_img_path))

    class ReplacementPanel:
        def __init__(self, main):
            # Initialize Replacement Panel
            self.main = main
            self.x, self.y = (303, 20)
            self.img_stack, self.stack_labels = [], []
            self.stack_select_lockout = {}

            # Labels
            self.panel_label = tk.Label(self.main.root, text='Replacement Icons', font=(label_font, 15))

            self.blank_image_label = tk.Label(self.main.root, image=self.main.blank)
            self.blank_image_label.image = self.main.blank

            self.stack_labels.append(tk.Label(self.main.root, image=self.main.stack_blank))
            self.stack_labels[-1].image = self.main.stack_blank
            self.stack_labels[-1].bind('<Button-1>', self.select_stack0)
            self.stack_labels[-1].place(x=31 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack0)

            self.stack_labels.append(tk.Label(self.main.root, image=self.main.stack_blank))
            self.stack_labels[-1].image = self.main.stack_blank
            self.stack_labels[-1].bind('<Button-1>', self.select_stack1)
            self.stack_labels[-1].place(x=92 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack1)

            self.stack_labels.append(tk.Label(self.main.root, image=self.main.stack_blank))
            self.stack_labels[-1].image = self.main.stack_blank
            self.stack_labels[-1].bind('<Button-1>', self.select_stack2)
            self.stack_labels[-1].place(x=153 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack2)

            self.stack_labels.append(tk.Label(self.main.root, image=self.main.stack_blank))
            self.stack_labels[-1].image = self.main.stack_blank
            self.stack_labels[-1].bind('<Button-1>', self.select_stack3)
            self.stack_labels[-1].place(x=214 + self.x, y=176 + self.y, anchor='nw')
            self.stack_labels[-1].drop_target_register(DND_FILES)
            self.stack_labels[-1].dnd_bind('<<Drop>>', self.drop_stack3)

            self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')

            self.blank_image_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
            self.blank_image_label.drop_target_register(DND_FILES)
            self.blank_image_label.dnd_bind('<<Drop>>', self.drop_in_replacement)

            # Buttons
            self.open_file_button = tk.Button(self.main.root, text='Open', width=10, command=self.load_replacement,
                                              takefocus=0)

            self.replace_all_button = tk.Button(self.main.root, text='Replace All',
                                                command=self.replace_all, takefocus=0)
            self.replace_all_button['state'] = DISABLED

            self.replace_button = tk.Button(self.main.root, text='Replace\nCurrent Icon', command=self.replace_icon,
                                            takefocus=0)
            self.replace_button['state'] = DISABLED

            self.prev_icon_button = tk.Button(self.main.root, text='Prev', command=self.dec_img_stack, width=5,
                                              takefocus=0)
            self.prev_icon_button['state'] = DISABLED

            self.next_icon_button = tk.Button(self.main.root, text='Next', command=self.inc_img_stack, width=5,
                                              takefocus=0)
            self.next_icon_button['state'] = DISABLED

            self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')
            self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
            self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
            self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
            self.next_icon_button.place(x=230 + self.x, y=146 + self.y)

            # Entry
            self.file_entry_field = tk.Entry(self.main.root, width=25, takefocus=0)
            self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
            self.file_entry_field.drop_target_register(DND_FILES)
            self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_replacement)
            self.file_entry_field.insert(0, 'Select image file...')
            self.file_entry_field['state'] = DISABLED

        # TODO: Update to us tk images
        def load_replacement(self, given_path=''):
            if not given_path:
                filename = filedialog.askopenfilenames(filetypes=[('Image', '*.png *.jpg *.jpeg *.gif')])
                # TODO: Rewrite to handle multiple files simultaneously
                if len(filename) == 1:
                    filename = filename[0]
                else:
                    for file in filename:
                        self.load_replacement(given_path=file)
                    return
            else:
                filename = given_path

            if not filename or not is_valid_image(filename):
                return

            if self.main.replacement_selected:
                self.add_to_img_stack(self.main.replacement_image_path)
            replacement_image = Image.open(filename)
            output_img = replacement_image.resize((1024, 1024))
            replacement_image.close()
            output_img.save(self.main.replacement_image_path)
            output_img.close()

            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, filename)
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
            self.blank_image_label.configure(image=icon)
            self.blank_image_label.image = icon

            if self.main.driver_selected:
                self.main.ask_to_save = True

        # TODO: Update to use tk images
        def add_to_img_stack(self, img_path: str, index=None):
            if not os.path.isfile(img_path) or not is_valid_image(img_path):
                return
            for img in self.img_stack:
                if filecmp.cmp(img, img_path):
                    return

            stack_length = 4

            new_img_path = os.path.join(self.main.temp_dir, 'stack', str(len(self.img_stack)), '.png')
            if 'replacement_icon.png' in img_path:
                os.rename(img_path, new_img_path)
            else:
                stack_image = Image.open(img_path)
                output_img = stack_image.resize((1024, 1024))
                stack_image.close()
                output_img.save(new_img_path)
                output_img.close()
            if index is None:
                self.img_stack.insert(0, new_img_path)
            elif not -len(self.img_stack) < index < len(self.img_stack):
                self.img_stack.append(new_img_path)
            else:
                temp = self.img_stack[index]
                self.img_stack.pop(index)
                self.img_stack.insert(index, new_img_path)
                self.img_stack.append(temp)
            self.refresh_img_stack()
            if len(self.img_stack) > stack_length:
                self.prev_icon_button['state'] = NORMAL
                self.next_icon_button['state'] = NORMAL

            self.main.ask_to_save = True

        # TODO: Update to use tk images
        def refresh_img_stack(self):
            if not self.img_stack:
                return
            # Create class variable for stack_length
            stack_length = 4
            for i, image in enumerate(self.img_stack):
                if i == stack_length:
                    break
                icon_image = Image.open(image)
                icon = icon_image.resize((60, 60))
                icon = ImageTk.PhotoImage(icon)
                self.stack_labels[i].configure(image=icon)
                self.stack_labels[i].image = icon

        def dec_img_stack(self):
            # Create class variable for stack_length
            stack_length = 4
            if len(self.img_stack) <= stack_length:
                return
            temp = self.img_stack[0]
            self.img_stack.pop(0)
            self.img_stack.append(temp)
            self.refresh_img_stack()

        def inc_img_stack(self):
            # Create class variable for stack_length
            stack_length = 4
            if len(self.img_stack) <= stack_length:
                return
            temp = self.img_stack[-1]
            self.img_stack.pop(-1)
            self.img_stack.insert(0, temp)
            self.refresh_img_stack()

        # TODO: Update to use tk images
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
            for i, icon in enumerate(self.main.c4z_panel.icons):
                if not self.main.c4z_panel.show_extra_icons.get() and icon.extra:
                    continue
                self.replace_icon(update_undo_history=False, index=i)
            self.main.update_undo_history()

        # TODO: Update to use tk images
        # TODO: Consolidate all select_stack functions
        def select_stack0(self, event):
            if not self.img_stack:
                return event
            # Debounce stack selection
            if 'stack0' in self.stack_select_lockout and time.time() - self.stack_select_lockout['stack0'] < 0.5:
                return event
            self.stack_select_lockout['stack0'] = time.time()
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.main.replacement_image_path):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.main.replacement_image_path, index=0)
                self.load_replacement(given_path=self.img_stack[-1])
                return None
            # TODO: Create class variable for stack_length
            stack_length = 4
            if len(self.img_stack) > stack_length and replacement_index > 3:
                self.load_replacement(given_path=self.img_stack[0])
                temp = self.img_stack[0]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(0)
                self.img_stack.insert(0, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return None
            self.load_replacement(given_path=self.img_stack[0])
            return None

        def select_stack1(self, event):
            if len(self.img_stack) <= 1:
                return event
            # Debounce stack selection
            if 'stack1' in self.stack_select_lockout and time.time() - self.stack_select_lockout['stack1'] < 0.5:
                return event
            self.stack_select_lockout['stack1'] = time.time()
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.main.replacement_image_path):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.main.replacement_image_path, index=1)
                self.load_replacement(given_path=self.img_stack[-1])
                return None
            stack_length = 4
            if len(self.img_stack) > stack_length and replacement_index > 3:
                self.load_replacement(given_path=self.img_stack[1])
                temp = self.img_stack[1]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(1)
                self.img_stack.insert(1, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return None
            self.load_replacement(given_path=self.img_stack[1])
            return None

        def select_stack2(self, event):
            if len(self.img_stack) <= 2:
                return event
            # Debounce stack selection
            if 'stack2' in self.stack_select_lockout and time.time() - self.stack_select_lockout['stack2'] < 0.5:
                return event
            self.stack_select_lockout['stack2'] = time.time()
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.main.replacement_image_path):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.main.replacement_image_path, index=2)
                self.load_replacement(given_path=self.img_stack[-1])
                return None
            stack_length = 4
            if len(self.img_stack) > stack_length and replacement_index > 3:
                self.load_replacement(given_path=self.img_stack[2])
                temp = self.img_stack[2]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(2)
                self.img_stack.insert(2, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return None
            self.load_replacement(given_path=self.img_stack[2])
            return None

        def select_stack3(self, event):
            if len(self.img_stack) <= 3:
                return event
            # Debounce stack selection
            if 'stack3' in self.stack_select_lockout and time.time() - self.stack_select_lockout['stack3'] < 0.5:
                return event
            self.stack_select_lockout['stack3'] = time.time()
            replacement_in_stack = False
            replacement_index = None
            for img in self.img_stack:
                if filecmp.cmp(img, self.main.replacement_image_path):
                    replacement_in_stack = True
                    replacement_index = self.img_stack.index(img)
                    break
            if not replacement_in_stack:
                self.add_to_img_stack(self.main.replacement_image_path, index=3)
                self.load_replacement(given_path=self.img_stack[-1])
                return None
            stack_length = 4
            if len(self.img_stack) > stack_length and replacement_index > 3:
                self.load_replacement(given_path=self.img_stack[3])
                temp = self.img_stack[3]
                temp_r = self.img_stack[replacement_index]
                self.img_stack.pop(replacement_index)
                self.img_stack.pop(3)
                self.img_stack.insert(3, temp_r)
                self.img_stack.insert(replacement_index, temp)
                self.refresh_img_stack()
                return None
            self.load_replacement(given_path=self.img_stack[3])
            return None

        def drop_in_replacement(self, event):
            paths = [path[0] if path[0] else path[1] for path in re.findall(r'\{(.*?)}|(\S+)', event.data)]
            for path in paths:
                if is_valid_image(path):
                    self.load_replacement(given_path=path)
                    continue
                if os.path.isdir(path):
                    for directory in list_all_sub_directories(path, include_root_dir=True):
                        for file in os.listdir(directory):
                            if is_valid_image(img_path := os.path.join(directory, file)):
                                self.load_replacement(given_path=img_path)

        # TODO: Consolidate all drop_stack functions and update to use RegEx
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
        def __init__(self, main):
            # Initialize Export Panel
            self.main = main
            self.x, self.y = (615, -50)
            self.abort = False

            # Labels
            self.panel_label = tk.Label(self.main.root, text='Export', font=(label_font, 15))
            self.panel_label.place(x=145 + self.x, y=50 + self.y, anchor='n')

            self.driver_name_label = tk.Label(self.main.root, text='Driver Name:')
            self.driver_name_label.place(x=65 + self.x, y=180 + self.y, anchor='w')

            # Buttons
            self.export_as_button = tk.Button(self.main.root, text='Export As...', width=20,
                                              command=self.do_export, takefocus=0)
            self.export_as_button['state'] = DISABLED

            self.export_as_button.place(x=145 + self.x, y=250 + self.y, anchor='n')
            self.export_button = tk.Button(self.main.root, text='Quick Export', width=20,
                                           command=self.quick_export, takefocus=0)
            self.export_button.place(x=145 + self.x, y=220 + self.y, anchor='n')
            self.export_button['state'] = DISABLED

            # Entry
            self.driver_name_var = StringVar(value='New Driver')
            self.driver_name_var.trace('w', self.validate_driver_name)
            self.driver_name_entry = tk.Entry(self.main.root, width=25, textvariable=self.driver_name_var)
            self.driver_name_entry.place(x=145 + self.x, y=190 + self.y, anchor='n')

            # Checkboxes
            self.inc_driver_version = IntVar(value=1)
            self.inc_driver_version.trace('w', self.update_driver_version)
            self.inc_driver_check = Checkbutton(self.main.root, text='increment driver version',
                                                variable=self.inc_driver_version, takefocus=0)
            self.inc_driver_check.place(x=63 + self.x, y=150 + self.y, anchor='w')

            self.include_backups = IntVar(value=1)
            self.include_backups_check = Checkbutton(self.main.root, text='include backup files',
                                                     variable=self.include_backups, takefocus=0)
            self.include_backups_check.place(x=63 + self.x, y=130 + self.y, anchor='w')

        def quick_export(self):
            driver_name = self.driver_name_var.get()

            def confirm_overwrite():
                self.abort = False
                overwrite_pop_up.destroy()

            def abort():
                self.abort = True
                overwrite_pop_up.destroy()

            # Overwrite file popup
            if os.path.isfile(os.path.join(self.main.cur_dir, f'{driver_name}.c4z')):
                overwrite_pop_up = Toplevel(self.main.root)
                overwrite_pop_up.title('Overwrite')
                overwrite_pop_up.geometry('239x70')
                overwrite_pop_up.geometry(f'+{self.main.root.winfo_rootx() + self.x}+'
                                          f'{self.main.root.winfo_rooty()}')
                overwrite_pop_up.protocol('WM_DELETE_WINDOW', abort)
                overwrite_pop_up.grab_set()
                overwrite_pop_up.focus()
                overwrite_pop_up.transient(self.main.root)
                overwrite_pop_up.resizable(False, False)

                confirm_label = Label(overwrite_pop_up, text='Would you like to overwrite the existing file?')
                confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

                yes_button = tk.Button(overwrite_pop_up, text='Yes', width='10', command=confirm_overwrite)
                yes_button.grid(row=2, column=0, sticky='e', padx=5)

                no_button = tk.Button(overwrite_pop_up, text='No', width='10', command=abort)
                no_button.grid(row=2, column=1, sticky='w', padx=5)
                self.do_export(quick_export=overwrite_pop_up)
                return
            self.do_export(quick_export=True)

        def export_file(self, driver_name: str, path=None):
            def get_next_num(start=0):
                while True:
                    start += 1
                    yield str(start)

            if path is None:
                path = os.path.join(self.main.cur_dir, f'{driver_name}.c4z')
            bak_files_dict = {}
            bak_files = []
            bak_folder = os.path.join(self.main.temp_dir, 'bak_files')

            # Backup and move all .bak files if not included
            if not self.include_backups.get():
                directories = list_all_sub_directories(os.path.join(self.main.temp_dir, 'driver'),
                                                       include_root_dir=True)
                if os.path.isdir(bak_folder):
                    shutil.rmtree(bak_folder)
                os.mkdir(bak_folder)
                suffix_num = get_next_num()
                for directory in directories:
                    for file in os.listdir(directory):
                        if file.endswith('.bak'):
                            current_path = os.path.join(directory, file)
                            # I think this is to avoid same name collisions
                            new_path = os.path.join(bak_folder, f'{file}{next(suffix_num)}')
                            bak_files.append(current_path)
                            bak_files_dict[current_path] = new_path
                            shutil.copy(current_path, new_path)
                            os.remove(current_path)

            # Create .c4z file
            shutil.make_archive(path, 'zip', os.path.join(self.main.temp_dir, 'driver'))
            os.rename(f'{path}.zip', path)

            # Restore .bak files
            if not self.include_backups.get():
                for file in bak_files:
                    shutil.copy(bak_files_dict[file], file)
                shutil.rmtree(bak_folder)

        def do_export(self, quick_export=None):
            # Wait for confirm overwrite dialog
            if quick_export and isinstance(quick_export, Toplevel):
                self.main.root.wait_window(quick_export)
            if self.abort:
                return
            # Format driver name
            driver_name = self.driver_name_var.get()
            # TODO: Probably a better way to do this
            temp = []
            for letter in driver_name:
                if letter in valid_chars:
                    temp.append(letter)
            driver_name = ''.join(temp)
            self.driver_name_entry.delete(0, 'end')
            self.driver_name_entry.insert(0, driver_name)
            if not driver_name:
                self.driver_name_entry['background'] = 'pink'
                self.main.counter = 7
                self.main.root.after(150, self.main.blink_driver_name_entry)
                return

            # Multi-state related checks
            if self.main.multi_state_driver:
                if self.main.states_win:
                    self.main.states_win.refresh()
                # Check State Validity
                invalid_states = False
                single_invalid_state = False
                for state in self.main.states:
                    if state.bg_color in ['pink', 'cyan']:
                        self.abort = True
                        invalid_states = True
                        if not single_invalid_state:
                            single_invalid_state = True
                            continue
                        single_invalid_state = False
                        break
                if invalid_states:
                    invalid_states_pop_up = Toplevel(self.main.root)
                    if single_invalid_state:
                        invalid_states_pop_up.title('Invalid State Found')
                        label_text = 'Cannot Export: Invalid state label'
                    else:
                        invalid_states_pop_up.title('Invalid States Found')
                        label_text = 'Cannot Export: Invalid state labels'
                    invalid_states_pop_up.geometry('239x70')
                    invalid_states_pop_up.geometry(f'+{self.main.root.winfo_rootx() + self.x}+'
                                                   f'{self.main.root.winfo_rooty()}')
                    invalid_states_pop_up.grab_set()
                    invalid_states_pop_up.focus()
                    invalid_states_pop_up.transient(self.main.root)
                    invalid_states_pop_up.resizable(False, False)
                    confirm_label = Label(invalid_states_pop_up, text=label_text, justify='center')
                    confirm_label.pack()
                    exit_button = tk.Button(invalid_states_pop_up, text='Cancel', width='10',
                                            command=invalid_states_pop_up.destroy, justify='center')
                    exit_button.pack(pady=10)
                if self.abort:
                    self.abort = False
                    return

                # Update state names in Lua file
                # state_name_changes = [original_name, new_name, original_name_lower, new_name_lower]
                state_name_changes = []
                if os.path.isfile(lua_path := os.path.join(self.main.temp_dir, 'driver', 'driver.lua')):
                    # Lua file backup
                    if os.path.isfile(lua_bak_path := f'{lua_path}.bak'):
                        os.remove(lua_bak_path)
                    shutil.copy(lua_path, lua_bak_path)
                    for state in self.main.states:
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

                    # Modify Lua file
                    modified_lua_lines = []
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
                    with open(lua_path, 'w', errors='ignore') as driver_lua_file:
                        driver_lua_file.writelines(modified_lua_lines)

                # Do multi-state related changes in XML
                if state_name_changes:
                    for item_tag in self.main.driver_xml.get_tags('item'):
                        for state_name_change in state_name_changes:
                            if state_name_change[0] == item_tag.value():
                                item_tag.set_value(state_name_change[1])
                                break
                            if state_name_change[2] == item_tag.value():
                                item_tag.set_value(state_name_change[3])
                                break
                    for name_tag in self.main.driver_xml.get_tags('name'):
                        for state_name_change in state_name_changes:
                            if state_name_change[0] == name_tag.value() or name_tag.value().endswith(
                                    state_name_change[0]):
                                name_tag.set_value(name_tag.value.replace(state_name_change[0],
                                                                          state_name_change[1]))
                                break
                            if state_name_change[2] == name_tag.value() or name_tag.value().endswith(
                                    state_name_change[2]):
                                name_tag.set_value(name_tag.value().replace(state_name_change[2],
                                                                            state_name_change[3]))
                                break
                    for description_tag in self.main.driver_xml.get_tags('description'):
                        for state_name_change in state_name_changes:
                            if f'{state_name_change[0]} ' in description_tag.value():
                                description_tag.set_value(description_tag.value().replace(state_name_change[0],
                                                                                          state_name_change[1]))
                                break
                            if f'{state_name_change[2]} ' in description_tag.value():
                                description_tag.set_value(description_tag.value.replace(state_name_change[2],
                                                                                        state_name_change[3]))
                                break
                    for state_tag in self.main.driver_xml.get_tags('state'):
                        for attribute in state_tag.attributes:
                            if attribute[0] == 'id':
                                for state_name_change in state_name_changes:
                                    if state_name_change[0] == attribute[1]:
                                        attribute[1] = state_name_change[1]
                                        break
                                    if state_name_change[2] == attribute[1]:
                                        attribute[1] = state_name_change[3]
                                        break

            # Check driver info variables
            if not all([self.main.driver_version_new_var.get(), self.main.driver_manufac_new_var.get(),
                        self.main.driver_creator_new_var.get()]):
                missing_driver_info_pop_up = Toplevel(self.main.root)
                missing_driver_info_pop_up.title('Missing Driver Information')
                label_text = 'Cannot Export: Missing driver info'
                missing_driver_info_pop_up.geometry('239x70')
                missing_driver_info_pop_up.geometry(f'+{self.main.root.winfo_rootx() + self.x}+'
                                                    f'{self.main.root.winfo_rooty()}')
                missing_driver_info_pop_up.grab_set()
                missing_driver_info_pop_up.focus()
                missing_driver_info_pop_up.transient(self.main.root)
                missing_driver_info_pop_up.resizable(False, False)
                confirm_label = Label(missing_driver_info_pop_up, text=label_text, justify='center')
                confirm_label.pack()
                exit_button = tk.Button(missing_driver_info_pop_up, text='Cancel', width='10',
                                        command=missing_driver_info_pop_up.destroy, justify='center')
                exit_button.pack(pady=10)
                return

            # Confirm all connections have non-conflicting ids
            for conn in self.main.connections:
                conn.update_id(refresh=True)

            # Set restore point for XML object
            self.main.driver_xml.set_restore_point()

            # Update connection names
            for conn in self.main.connections:
                conn.tag.get_tag('connectionname').set_value(conn.name_entry_var.get())
                conn.tag.get_tag('classname').set_value(conn_type := conn.type.get())
                if 'IN' in conn_type:
                    conn.tag.get_tag('consumer').set_value('True')
                else:
                    conn.tag.get_tag('consumer').set_value('False')
                if conn_type == 'IR_OUT':
                    conn.tag.add_element(XMLTag(xml_string='<facing>6</facing>'), index=2)
                    conn.tag.add_element(XMLTag(xml_string='<audiosource>False</audiosource>'), index=-3)
                    conn.tag.add_element(XMLTag(xml_string='<videosource>False</videosource>'), index=-3)

            # Update XML with new driver name
            self.main.driver_xml.get_tag('name').set_value(driver_name)
            modified_datestamp = str(datetime.now().strftime('%m/%d/%Y %H:%M'))
            if (self.inc_driver_version.get() and
                    int(self.main.driver_version_var.get()) >= int(self.main.driver_version_new_var.get())):
                self.main.driver_version_new_var.set(str(int(self.main.driver_version_var.get()) + 1))
            self.main.driver_xml.get_tag('version').set_value(self.main.driver_version_new_var.get())
            self.main.driver_xml.get_tag('modified').set_value(modified_datestamp)
            self.main.driver_xml.get_tag('creator').set_value(self.main.driver_creator_new_var.get())
            self.main.driver_xml.get_tag('manufacturer').set_value(self.main.driver_manufac_new_var.get())
            for attribute in self.main.driver_xml.get_tag('proxy').attributes:
                if attribute[0] == 'name':
                    attribute[1] = driver_name
            for icon_tag in self.main.driver_xml.get_tags('Icon'):
                if result := re.search('driver/(.*)/icons', icon_tag.value()):
                    result = result[1]
                    icon_tag.set_value(icon_tag.value().replace(result, driver_name))

            # Backup XML file and write new XML
            if os.path.isfile(xml_bak_path := os.path.join(self.main.temp_dir, 'driver', 'driver.xml.bak')):
                os.remove(xml_bak_path)
            os.rename(xml_path := os.path.join(self.main.temp_dir, 'driver', 'driver.xml'), xml_bak_path)
            with open(xml_path, 'w', errors='ignore') as out_file:
                out_file.writelines(self.main.driver_xml.get_lines())
            # TODO: Remove before commit
            with open('driver.xml', 'w', errors='ignore') as out_file:
                out_file.writelines(self.main.driver_xml.get_lines())

            # Save As Dialog
            if not quick_export:
                out_file = filedialog.asksaveasfile(initialfile=f'{driver_name}.c4z',
                                                    filetypes=[('Control4 Drivers', '*.c4z')])
                with contextlib.suppress(AttributeError):
                    out_file_path = out_file.name
                    out_file.close()
                    if '.c4z' not in out_file_path:
                        # Remove file created by save dialog
                        os.remove(out_file_path)
                        out_file_path += '.c4z'
                    # Export file
                    if os.path.isfile(out_file_path):
                        os.remove(out_file_path)
                    self.export_file(driver_name, path=out_file_path)
            else:
                if os.path.isfile(existing_file := os.path.join(self.main.cur_dir, f'{driver_name}.c4z')):
                    os.remove(existing_file)
                self.export_file(driver_name)

            # Restore original XML and Lua
            self.main.driver_version_var.set(self.main.driver_version_new_var.get())
            if self.inc_driver_version.get():
                self.main.driver_version_new_var.set(str(int(self.main.driver_version_new_var.get()) + 1))
            self.main.driver_xml.restore()
            if os.path.isfile(lua_bak_path := os.path.join(self.main.temp_dir, 'driver', 'driver.lua.bak')):
                os.remove(lua_path := os.path.join(self.main.temp_dir, 'driver', 'driver.lua'))
                os.rename(lua_bak_path, lua_path)
            os.remove(xml_path := os.path.join(self.main.temp_dir, 'driver', 'driver.xml'))
            os.rename(f'{xml_path}.bak', xml_path)

        def validate_driver_name(self, *_):
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

    def __init__(self):
        def valid_instance_id(instance_ids: list):
            valid_id = str(random.randint(111111, 999999))
            if f'{valid_id}\n' in instance_ids:
                valid_id = valid_instance_id(instance_ids)
            return valid_id

        # Create temporary directory
        self.instance_id = str(random.randint(111111, 999999))
        self.cur_dir = os.getcwd()
        self.temp_root_dir = os.path.join(self.cur_dir, 'C4IconSwapperTemp')
        self.temp_dir = os.path.join(self.temp_root_dir, self.instance_id)
        self.checked_in, self.recover_instance, checked_in_instances = False, '', []
        if os.path.isdir(self.temp_root_dir):
            if os.path.isfile(instance_path := os.path.join(self.temp_root_dir, 'instance')):
                with open(instance_path, 'r', errors='ignore') as instance_file:
                    current_instances = instance_file.readlines()
                if current_instances:
                    if not os.path.isdir(check_in_path := os.path.join(self.temp_root_dir, 'check_in')):
                        os.mkdir(check_in_path)
                    waiting_for_response = True
                    self.main_app_wait = False
                    # I'm sure there is a better way to format this timestamp lol
                    begin_time = float(time.mktime(datetime.now().timetuple()))
                    while waiting_for_response:
                        checked_in_instances = os.listdir(check_in_path)
                        if len(checked_in_instances) == len(current_instances):
                            waiting_for_response = False
                        if float(time.mktime(datetime.now().timetuple())) - begin_time >= 2:
                            waiting_for_response = False
                    failed_to_check_in = []
                    for instance_id in current_instances:
                        if instance_id.replace('\n', '') not in checked_in_instances:
                            failed_to_check_in.append(instance_id.replace('\n', ''))

                    # Offer project recovery if applicable
                    if not os.path.isdir(os.path.join(self.temp_root_dir, failed_to_check_in[0])):
                        # Hack to deal with bug cause by crash during recovery
                        failed_to_check_in = []
                    if failed_to_check_in and os.listdir(os.path.join(self.temp_root_dir, failed_to_check_in[0])):
                        def win_close():
                            self.main_app_wait = False
                            recovery_win.destroy()

                        def flag_recovery():
                            self.recover_instance = failed_to_check_in[0]
                            win_close()

                        self.main_app_wait = True
                        recovery_win = tk.Tk()
                        recovery_win.focus()
                        recovery_win.protocol('WM_DELETE_WINDOW', win_close)
                        recovery_win.title('Driver Recovery')
                        recovery_win.geometry('300x100')
                        recovery_win.resizable(False, False)
                        label_text = 'Existing driver found.'
                        recovery_label = tk.Label(recovery_win, text=label_text)
                        recovery_label.pack()
                        label_text = 'Would you like to recover previous driver?'
                        recovery_label2 = tk.Label(recovery_win, text=label_text)
                        recovery_label2.pack()
                        recovery_button = tk.Button(recovery_win, text='Recover Driver', command=flag_recovery)
                        recovery_button.pack()
                        recovery_win.mainloop()

                    while self.main_app_wait:
                        pass
                    del self.main_app_wait

                    for failed_id in failed_to_check_in:
                        if failed_id == self.recover_instance:
                            continue
                        if os.path.isdir(os.path.join(self.temp_root_dir, failed_id)):
                            shutil.rmtree(os.path.join(self.temp_root_dir, failed_id))
                    current_instances = []
                    for instance_id in os.listdir(check_in_path):
                        current_instances.append(f'{instance_id}\n')
                    shutil.rmtree(check_in_path)
                if f'{self.instance_id}\n' in current_instances:
                    self.instance_id = valid_instance_id(current_instances)
                current_instances.append(f'{self.instance_id}\n')
                with open(instance_path, 'w', errors='ignore') as out_file:
                    out_file.writelines(current_instances)
                if self.recover_instance and os.path.isdir(os.path.join(self.temp_root_dir, self.recover_instance)):
                    os.rename(os.path.join(self.temp_root_dir, self.recover_instance), self.temp_dir)
            else:
                shutil.rmtree(self.temp_root_dir)
                os.mkdir(self.temp_root_dir)
                with open(instance_path, 'w', errors='ignore') as out_file:
                    out_file.writelines(f'{self.instance_id}\n')
        else:
            os.mkdir(self.temp_root_dir)
            with open(os.path.join(self.temp_root_dir, 'instance'), 'w', errors='ignore') as out_file:
                out_file.writelines(f'{self.instance_id}\n')
        if not self.recover_instance:
            os.mkdir(self.temp_dir)
        # Initialize main program
        self.root = TkinterDnD.Tk()
        self.root.geometry('915x287')
        self.root.bind('<KeyRelease>', self.key_release)

        # Root window properties
        if checked_in_instances:
            self.root.title(f'C4 Icon Swapper ({self.instance_id})')
        else:
            self.root.title('C4 Icon Swapper')
        self.root.resizable(False, False)

        # Version Label
        self.version_label = Label(self.root, text=version)
        self.version_label.place(relx=1, rely=1.01, anchor='se')
        self.version_label.bind('<Button-1>', self.easter)

        # Class variables
        self.driver_xml = None
        self.driver_manufac_var = StringVar()
        self.driver_manufac_new_var = StringVar(value='C4IconSwapper')
        self.driver_creator_var = StringVar()
        self.driver_creator_new_var = StringVar(value='C4IconSwapper')
        self.driver_ver_orig = StringVar()
        self.driver_version_var = StringVar()
        self.driver_version_new_var = StringVar()
        self.driver_version_new_var.set('1')
        self.multi_state_driver, self.states_shown, self.ask_to_save = False, False, False
        self.counter, self.easter_counter = 0, 0
        self.connections = [self.Connection(self) for _ in range(18)]
        self.conn_ids = []
        self.states = [self.State('') for _ in range(13)]
        self.state_dupes = []
        self.states_orig_names = []
        self.device_icon_dir = os.path.join(www_path := os.path.join(self.temp_dir, 'driver', 'www'), 'icons', 'device')
        self.icon_dir = os.path.join(www_path, 'icons')
        self.images_dir = os.path.join(www_path, 'images')
        self.replacement_image_path = os.path.join(self.temp_dir, 'replacement_icon.png')
        self.orig_file_dir, self.orig_file_path, self.restore_entry_string = '', '', ''
        self.driver_selected, self.replacement_selected, self.schedule_entry_restore = False, False, False
        self.undo_history = deque(maxlen=10)

        # TODO: Update to use tk images
        # Panels; Creating blank image for panels
        temp_image_file = os.path.join(self.temp_root_dir, 'blank.gif')
        with open(temp_image_file, 'wb') as blank_img_file:
            blank_img_file.write(base64.b64decode(Base64Assets.blank_img_b64))
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
        self.driver_info_win = None
        self.states_win = None
        self.connections_win = None
        self.root.bind('<Control-s>', self.save_project)
        self.root.bind('<Control-o>', self.load_project)
        self.root.bind('<Control-z>', self.undo)
        self.root.bind('<Control-w>', self.on_program_exit)

        # Menu
        self.menu = Menu(self.root)
        self.file = Menu(self.menu, tearoff=0)
        self.file.add_command(label='Open Project', command=self.load_project)
        self.file.add_command(label='Save Project', command=self.save_project)
        self.file.add_separator()
        self.file.add_command(label='Open C4z', command=self.c4z_panel.load_c4z)
        self.file.add_command(label='Open Replacement Image', command=self.replacement_panel.load_replacement)
        self.file.add_separator()
        self.file.add_command(label='Load Generic Driver', command=self.c4z_panel.load_gen_driver)
        self.file.add_command(label='Load Multi Driver', command=self.c4z_panel.load_gen_multi)
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

        # Separators
        self.separator0 = ttk.Separator(self.root, orient='vertical')
        self.separator1 = ttk.Separator(self.root, orient='vertical')
        self.separator0.place(x=305, y=0, height=270)
        self.separator1.place(x=610, y=0, height=270)

        # TODO: Update to use wm_iconbitmap object stored in b64
        # Creating window icon
        temp_icon_file = os.path.join(self.temp_root_dir, 'icon.ico')
        with open(temp_icon_file, 'wb') as icon_file:
            icon_file.write(base64.b64decode(Base64Assets.win_icon))
        self.root.wm_iconbitmap(temp_icon_file)
        os.remove(temp_icon_file)

        # Do recovery if necessary
        if self.recover_instance:
            # Recover Driver
            self.c4z_panel.load_c4z(recovery=True)
            # Recover replacement images; Need to make this more efficient
            first_time = True
            recovery_path = os.path.join(self.temp_dir, 'img_recovery')
            for file in os.listdir(self.temp_dir):
                if is_valid_image(file):
                    if first_time:
                        os.mkdir(recovery_path)
                        first_time = False
                    shutil.copy(temp_path := os.path.join(self.temp_dir, file), os.path.join(recovery_path, file))
                    os.remove(temp_path)
            if not first_time:
                multi_images = False
                multi_check = 0
                # TODO: Create class variable for stack_length
                stack_size = 4
                for file in os.listdir(recovery_path):
                    self.replacement_panel.load_replacement(given_path=os.path.join(recovery_path, file))
                    if multi_check > stack_size + 1:
                        multi_images = True
                        continue
                    multi_check += 1
                shutil.rmtree(os.path.join(self.temp_dir, 'img_recovery'))
                self.replacement_panel.file_entry_field['state'] = NORMAL
                self.replacement_panel.file_entry_field.delete(0, END)
                self.replacement_panel.file_entry_field.insert(0, 'Recovered Image')
                self.replacement_panel.file_entry_field['state'] = 'readonly'
                if multi_images:
                    self.replacement_panel.next_icon_button['state'] = NORMAL
                    self.replacement_panel.prev_icon_button['state'] = NORMAL

        # Main Loop
        self.root.config(menu=self.menu)
        self.root.after(150, self.instance_check)
        self.root.protocol('WM_DELETE_WINDOW', self.on_program_exit)
        self.root.mainloop()

    def restore_entry_text(self):
        if self.schedule_entry_restore:
            self.schedule_entry_restore = False
            if self.restore_entry_string:
                self.c4z_panel.file_entry_field['state'] = NORMAL
                self.c4z_panel.file_entry_field.delete(0, 'end')
                self.c4z_panel.file_entry_field.insert(0, self.restore_entry_string)
                self.c4z_panel.file_entry_field['state'] = 'readonly'
                self.restore_entry_string = ''

    def key_release(self, event):
        if event.keysym == 'Right':
            self.c4z_panel.next_icon()
        elif event.keysym == 'Left':
            self.c4z_panel.prev_icon()
        elif event.keysym == 'Up':
            self.replacement_panel.inc_img_stack()
        elif event.keysym == 'Down':
            self.replacement_panel.dec_img_stack()
        elif event.keysym == 'c' and self.easter_counter >= 10:
            self.version_label.config(text='\u262D', font=('Arial', 25))
            self.version_label.place(relx=1.005, rely=1.02, anchor='se')
            self.easter_counter = -1

    # TODO: Rewrite using RegEx
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
                self.states_win.states[i].name_entry['state'] = NORMAL
            self.states[i].name_var.set(state_name)
            self.states[i].original_name = state_name

    def recall_load_gen_multi(self):
        self.c4z_panel.load_gen_multi(show_loading_image=False)

    def blink_driver_name_entry(self):
        if not self.counter:
            return
        self.counter -= 1
        if self.export_panel.driver_name_entry['background'] != light_entry_bg:
            self.export_panel.driver_name_entry['background'] = light_entry_bg
        else:
            self.export_panel.driver_name_entry['background'] = 'pink'
        self.root.after(150, self.blink_driver_name_entry)

    def on_program_exit(self, *_):
        if self.ask_to_save:
            self.ask_to_save_dialog(root_destroy=True)
            return
        self.end_program()

    def end_program(self):
        with open(instance_path := os.path.join(self.temp_root_dir, 'instance'), 'r', errors='ignore') as instance_file:
            current_instances = instance_file.readlines()
        if len(current_instances) > 1:
            if os.path.isdir(check_in_path := os.path.join(self.temp_root_dir, 'check_in')) and not self.checked_in:
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
                if os.path.isdir(os.path.join(self.temp_root_dir, failed_id)):
                    shutil.rmtree(self.temp_root_dir + failed_id)
            current_instances = [f'{instance_id}\n' for instance_id in os.listdir(check_in_path)]
            shutil.rmtree(check_in_path)
            if current_instances:
                with open(instance_path, 'w', errors='ignore') as out_file:
                    out_file.writelines(current_instances)
                shutil.rmtree(self.temp_dir)
            else:
                shutil.rmtree(self.temp_root_dir)
        else:
            shutil.rmtree(self.temp_root_dir)

        self.root.destroy()

    def ask_to_save_dialog(self, on_exit=True, root_destroy=False):
        def cancel_dialog():
            self.ask_to_save = True
            save_dialog.destroy()

        def exit_save_dialog():
            save_dialog.destroy()
            if root_destroy:
                self.end_program()

        def do_project_save():
            self.save_project()
            exit_save_dialog()

        save_dialog = Toplevel(self.root)
        save_dialog.title('Save current project?')
        save_dialog.geometry('239x70')
        if on_exit:
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

        yes_button = tk.Button(save_dialog, text='Yes', width='10', command=do_project_save)
        yes_button.grid(row=2, column=0, sticky='e', padx=5)

        no_button = tk.Button(save_dialog, text='No', width='10', command=exit_save_dialog)
        no_button.grid(row=2, column=1, sticky='w', padx=5)

        self.ask_to_save = False
        return save_dialog

    def close_connections(self):
        if self.connections_win is None:
            return
        self.connections_win.window.destroy()
        del self.connections_win
        self.connections_win = None

    def close_driver_info(self):
        if self.driver_info_win is None:
            return
        if not self.driver_version_new_var.get():
            self.driver_version_new_var.set('0')
        if not self.driver_creator_new_var.get():
            self.driver_creator_new_var.set('C4IconSwapper')
        if not self.driver_manufac_new_var.get():
            self.driver_manufac_new_var.set('C4IconSwapper')
        if not self.driver_version_new_var.get():
            if self.driver_version_var.get():
                self.driver_version_new_var.set(str(int(self.driver_version_var.get()) + 1))
            else:
                self.driver_version_new_var.set('1')
        if (self.export_panel.inc_driver_version.get() and self.driver_version_var.get() and
                int(self.driver_version_new_var.get()) <= int(self.driver_version_var.get())):
            self.driver_version_new_var.set(str(int(self.driver_version_var.get()) + 1))
        self.driver_info_win.window.destroy()
        del self.driver_info_win
        self.driver_info_win = None

    def close_states(self):
        if self.states_win is None:
            return
        self.states_win.refresh()
        self.states_win.window.destroy()
        del self.states_win
        self.states_win = None

    def validate_driver_ver(self, *_):
        version_str = self.driver_version_new_var.get()
        version_compare = [char for char in version_str.lstrip('0') if char in numbers]

        if self.driver_info_win and (str_diff := len(version_str) - len(version_compare)):
            cursor_pos = self.driver_info_win.driver_ver_new_entry.index(INSERT)
            self.driver_info_win.driver_ver_new_entry.icursor(cursor_pos - str_diff)
            self.driver_version_new_var.set(''.join(version_compare))

        self.ask_to_save = True

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

    def save_project(self, *_):
        out_file = filedialog.asksaveasfile(initialfile=f'{self.export_panel.driver_name_var.get()}.c4is',
                                            filetypes=[('C4IconSwapper Project', '*.c4is')])
        if not out_file:
            return
        if not (out_file_path := out_file.name).endswith('.c4is'):
            out_file.close()
            os.rename(out_file_path, (out_file_path := f'{out_file_path}.c4is'))
        with open(out_file_path, 'wb') as output:
            pickle.dump(C4IS(self), output)
        self.ask_to_save = False

    def load_project(self, *_):
        if filename := filedialog.askopenfilename(filetypes=[('C4IconSwapper Project', '*.c4is')]):
            self.load_c4is(filename)

    def load_c4is(self, file):
        save_state = file
        if type(file) is str:
            with open(file, 'rb') as file:
                save_state = pickle.load(file)
        if type(save_state) is not C4IS:
            raise TypeError

        # C4z Panel (and export button)
        self.c4z_panel.icons = []
        self.c4z_panel.current_icon = 0
        self.c4z_panel.blank_image_label.configure(image=self.blank)
        if os.path.isdir(driver_folder := os.path.join(self.temp_dir, 'driver')):
            shutil.rmtree(driver_folder)
        self.c4z_panel.restore_button['state'] = DISABLED
        if save_state.driver_selected:
            with open(saved_driver_path := os.path.join(self.temp_dir, 'saved_driver.c4z'), 'wb') as driver_zip:
                driver_zip.write(save_state.driver_zip)
            self.c4z_panel.load_c4z(saved_driver_path)
            os.remove(saved_driver_path)
            self.export_panel.export_button['state'] = NORMAL
            self.export_panel.export_as_button['state'] = NORMAL
            if os.path.isfile(f'{self.c4z_panel.icons[self.c4z_panel.current_icon].path}.bak'):
                self.c4z_panel.restore_button['state'] = NORMAL
        else:
            self.export_panel.export_button['state'] = DISABLED
            self.export_panel.export_as_button['state'] = DISABLED
            self.c4z_panel.icon_name_label.config(text='icon name')
            self.c4z_panel.icon_label.config(text='0 of 0')
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
        self.conn_ids = save_state.ids
        for i, conn in enumerate(save_state.connections):
            self.connections[i].id = conn['id']
            self.connections[i].original = conn['original']
            self.connections[i].in_id_group = conn['in_id_group']
            self.connections[i].delete = conn['delete']
            self.connections[i].prior_txt = conn['prior_txt']
            self.connections[i].prior_type = conn['prior_type']
            self.connections[i].tag = conn['tag']
            self.connections[i].id_group = conn['id_group']
            self.connections[i].type.set(conn['type'])
            self.connections[i].name_entry_var.set(conn['name'])
            self.connections[i].enabled = conn['state']

        # Export Panel
        self.export_panel.driver_name_var.set(save_state.driver_name_var)
        self.export_panel.inc_driver_version.set(save_state.inc_driver_version)
        self.export_panel.include_backups.set(save_state.include_backups)

        # TODO: Update to use tk images
        # Replacement Panel
        if save_state.replacement:
            if os.path.isfile(self.replacement_image_path):
                os.remove(self.replacement_image_path)
            save_state.replacement.save(self.replacement_image_path)
            save_state.replacement.close()
            icon_image = Image.open(self.replacement_image_path)
            icon = icon_image.resize((128, 128))
            icon = ImageTk.PhotoImage(icon)
            self.replacement_panel.blank_image_label.configure(image=icon)
            self.replacement_panel.blank_image_label.image = icon
        for img in self.replacement_panel.img_stack:
            os.remove(img)
        self.replacement_panel.img_stack = []
        for stack_label in self.replacement_panel.stack_labels:
            stack_label.configure(image=self.stack_blank)
        for img in save_state.img_stack:
            img_path = f'{self.temp_dir}stack{str(len(self.replacement_panel.img_stack))}.png'
            img.save(img_path)
            img.close()
            self.replacement_panel.img_stack.append(img_path)
        self.replacement_panel.refresh_img_stack()
        self.replacement_panel.replace_button['state'] = save_state.replacement_panel['replace']
        self.replacement_panel.replace_all_button['state'] = save_state.replacement_panel['replace_all']
        self.replacement_panel.prev_icon_button['state'] = save_state.replacement_panel['prev']
        self.replacement_panel.next_icon_button['state'] = save_state.replacement_panel['next']

        self.ask_to_save = False

    def open_edit_win(self, window, win_type: str):
        if window:
            window.window.deiconify()
            window.window.focus()
            return
        if win_type == 'conn':
            self.connections_win = self.ConnectionsWin(self)
        elif win_type == 'driver':
            self.driver_info_win = self.DriverInfoWin(self)
        elif win_type == 'states':
            self.states_win = self.StatesWin(self)

    # TODO: Make the undo feature actually decent
    def undo(self, *_):
        # I'm doing this bootleg af... too lazy to make this efficient
        if not self.undo_history:
            self.edit.entryconfig(self.undo_pos, state=DISABLED)
            return
        current_icon = self.c4z_panel.current_icon
        ask_to_save = self.ask_to_save
        self.ask_to_save = False
        self.load_c4is(self.undo_history.pop())
        self.c4z_panel.current_icon = current_icon
        self.c4z_panel.update_icon()
        if os.path.isfile(f'{self.c4z_panel.icons[current_icon].path}.bak'):
            self.c4z_panel.restore_button['state'] = NORMAL
        else:
            self.c4z_panel.restore_button['state'] = DISABLED

        if not self.undo_history:
            self.edit.entryconfig(self.undo_pos, state=DISABLED)
        self.ask_to_save = ask_to_save

    def update_undo_history(self):
        # EXTREMELY memory inefficient! 😎
        self.undo_history.append(copy.deepcopy(C4IS(self)))
        self.edit.entryconfig(self.undo_pos, state=NORMAL)

    def instance_check(self):
        if self.checked_in and not os.path.isdir(os.path.join(self.temp_root_dir, 'check_in')):
            self.checked_in = False
        elif not self.checked_in and os.path.isdir(check_in_path := os.path.join(self.temp_root_dir, 'check_in')):
            with open(os.path.join(check_in_path, self.instance_id), 'w', errors='ignore') as check_in_file:
                check_in_file.writelines('')
            self.checked_in = True
            self.root.title(f'C4 Icon Swapper ({self.instance_id})')

        self.root.after(150, self.instance_check)

    def easter(self, *_, decay=False):
        if self.easter_counter < 0:
            return
        if not decay:
            if not self.easter_counter:
                self.root.after(2000, lambda: self.easter(decay=True))
            self.easter_counter += 1
            return
        self.easter_counter -= 1
        if not self.easter_counter:
            return
        self.root.after(2000, lambda: self.easter(decay=True))


def list_all_sub_directories(directory: str, include_root_dir=False):
    subs = []
    for root, dirs, _ in os.walk(directory):
        for sub in dirs:
            subs.append(os.path.join(root, sub))
    subs.sort()
    return [directory, *subs] if include_root_dir else subs


def find_valid_id(id_seed: int, list_of_ids: list, inc_count=0):
    if id_seed not in list_of_ids:
        return [id_seed, inc_count]
    return find_valid_id(id_seed + 1, list_of_ids, inc_count=inc_count + 1)


def is_valid_image(file_path: str):
    return any(file_path.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.jpeg'])


def natural_key(string: str):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]


if __name__ == '__main__':
    C4IconSwapper()
