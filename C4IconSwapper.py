import contextlib
import copy
import filecmp
import itertools
import os
import pickle
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import warnings
from collections import Counter, deque, defaultdict
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageTk, UnidentifiedImageError
from PIL.Image import Resampling
from tkinter import Tk, filedialog, ttk, Toplevel, Checkbutton, IntVar, StringVar, Label, Menu, OptionMenu
from tkinter import DISABLED, NORMAL, END, INSERT, Scrollbar, Text, Button, Entry, Frame
from tkinterdnd2 import DND_FILES, TkinterDnD

from XMLObject import XMLObject, XMLTag

version = '1.3'

label_font, light_entry_bg, dark_entry_bg = 'Arial', '#FFFFFF', '#282830'
mono_font = label_font

re_valid_chars = re.compile(r'[^\-_ a-zA-Z0-9]')
valid_img_types = ('.png', '.jpg', '.gif', '.jpeg')
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
selectable_connections = ('HDMI IN', 'HDMI OUT', 'COMPOSITE IN', 'COMPOSITE OUT', 'VGA IN', 'VGA OUT', 'COMPONENT IN',
                          'COMPONENT OUT', 'DVI IN', 'DVI OUT', 'STEREO IN', 'STEREO OUT', 'DIGITAL_OPTICAL IN',
                          'DIGITAL_OPTICAL OUT', 'IR_OUT')
conn_id_type = {'HDMI IN': (2000, '5'), 'COMPOSITE IN': (2000, '5'), 'VGA IN': (2000, '5'),
                 'COMPONENT IN': (2000, '5'), 'DVI IN': (2000, '5'),
                 'HDMI OUT': (1900, '5'), 'COMPOSITE OUT': (1900, '5'), 'VGA OUT': (1900, '5'),
                 'COMPONENT OUT': (1900, '5'), 'DVI OUT': (1900, '5'),
                 'STEREO IN': (4000, '6'), 'DIGITAL_OPTICAL IN': (4000, '6'),
                 'STEREO OUT': (3900, '6'), 'DIGITAL_OPTICAL OUT': (3900, '6'),
                 'IR_OUT': (1, '1')}
global_instance_id = None


# TODO: Completely overhaul everything related to multistate
class C4IconSwapper:
    def __init__(self):
        def valid_instance_id(instance_ids: list):
            valid_id = str(random.randint(111111, 999999))
            if f'{valid_id}\n' in instance_ids:
                valid_id = valid_instance_id(instance_ids)
            return valid_id

        def exception_window(*args, message_txt=None):
            root = Toplevel(self.root)
            root.title('Exception')
            root.attributes('-toolwindow', True)
            frame = Frame(root)
            frame.pack(expand=True, fill='both', padx=10, pady=10)

            h_scroll = Scrollbar(frame, orient='horizontal')
            h_scroll.pack(side='bottom', fill='x')
            v_scroll = Scrollbar(frame, orient='vertical')
            v_scroll.pack(side='right', fill='y')

            text_widget = Text(frame, font=('Consolas', 11), wrap='none')
            text_widget.pack(side='left', expand=True, fill='both')
            text_widget.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
            v_scroll.config(command=text_widget.yview)
            h_scroll.config(command=text_widget.xview)

            # Set window size
            if message_txt:
                msg_lines = message_txt.splitlines()
            elif len(args) > 1 and args[1] is RuntimeWarning:
                message_txt = f'{args[1].__name__}\nMessage: {args[0]}\n{args[2]}, Line: {args[3]}'
                msg_lines = message_txt.splitlines()
            else:
                msg_lines = (message_txt := '\n'.join(traceback.format_exception(*args))).splitlines()

            text_widget.insert(END, message_txt)
            width = max(len(line.strip()) for line in msg_lines) + 3
            height = len(msg_lines) + 2
            text_widget.config(width=width, height=height)

            # Update window for size check
            root.update_idletasks()

            # Cap window size
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            max_rel_h_size = 0.75
            max_rel_v_size = 0.75
            if root.winfo_width() > screen_width * max_rel_h_size:
                if root.winfo_height() > screen_height * max_rel_v_size:
                    root.geometry(f'{int(screen_width * max_rel_h_size)}x{int(screen_height * max_rel_v_size)}')
                else:
                    root.geometry(f'{int(screen_width * max_rel_h_size)}x{root.winfo_height()}')
            elif root.winfo_height() > screen_height * max_rel_v_size:
                root.geometry(f'{root.winfo_width()}x{int(screen_height * max_rel_v_size)}')

            text_widget.config(state='disabled')
            root.resizable(False, False)
            root.grab_set()
            return

        def exception_handler(*args):
            if args:
                if len(args) > 1 and args[1] is RuntimeWarning:
                    self.warnings.append(f'{args[1].__name__}\nMessage: {args[0]}\n{args[2]}, Line: {args[3]}')
                else:
                    self.exceptions.append('\n'.join(traceback.format_exception(*args)))
                if self.handler_recall_id:
                    self.root.after_cancel(self.handler_recall_id)
                # noinspection PyTypeChecker
                self.handler_recall_id = self.root.after(50, exception_handler)
                return
            if not self.warnings and not self.exceptions:
                return
            if len(self.warnings) == 1 and not self.exceptions:
                exception_window(message_txt=self.warnings.pop())
                return
            elif len(self.exceptions) == 1 and not self.warnings:
                exception_window(message_txt=self.exceptions.pop())
                return

            def get_label(count: int, text: str):
                if count == 0:
                    return ''
                return f'{count} {text}' if count != 1 else f'{count} {text[:-1]}'

            labels = (get_label(len(self.exceptions), 'EXCEPTIONS'),
                      get_label(len(self.warnings), 'WARNINGS'))
            header = f'{" & ".join(filter(None, labels))}\n'
            header += '=' * len(header.strip())
            msg_body = []
            if self.exceptions:
                msg_body.append('\n\n========================\n\n'.join(self.exceptions))
            if self.warnings:
                msg_body.append('\n\n========================\n\n'.join(self.warnings))
            msg_txt = '\n\n==================\n     WARNINGS\n==================\n\n'.join(msg_body)

            self.exceptions.clear()
            self.warnings.clear()
            exception_window(message_txt=f'{header}\n\n{msg_txt}')

        self.warnings = deque()
        self.exceptions = deque()
        self.handler_recall_id = None

        # Create temporary directory
        self.instance_id = str(random.randint(111111, 999999))
        self.cur_dir = os.getcwd()
        if sys.platform == 'win32':
            self.appdata_temp = os.path.join(os.environ.get('APPDATA'), 'C4IconSwapper')
        elif sys.platform == 'darwin':
            self.appdata_temp = os.path.expanduser('~/Library/Application Support/C4IconSwapper')
        else:  # Linux
            self.appdata_temp = os.path.expanduser('~/.config/C4IconSwapper')
        self.temp_root_dir = os.path.join(self.appdata_temp, 'C4IconSwapperTemp')
        self.temp_dir = os.path.join(self.temp_root_dir, self.instance_id)
        self.checked_in, self.recover_instance, checked_in_instances = False, '', []
        if not os.path.isdir(self.appdata_temp):
            os.mkdir(self.appdata_temp)
        if os.path.isdir(self.temp_root_dir):
            # TODO: Rewrite instance checks using sockets
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
                        if instance_id not in [inst_id.strip() for inst_id in checked_in_instances]:
                            failed_to_check_in.append(instance_id.replace('\n', ''))

                    # Offer project recovery if applicable
                    if not os.path.isdir(failed_inst_path := os.path.join(self.temp_root_dir, failed_to_check_in[0])):
                        # Hack to deal with bug cause by crash during recovery
                        failed_to_check_in = []
                    if failed_to_check_in and 'driver' in os.listdir(failed_inst_path):
                        def win_close():
                            self.main_app_wait = False
                            recovery_win.destroy()

                        def flag_recovery():
                            self.recover_instance = failed_to_check_in[0]
                            win_close()

                        self.main_app_wait = True
                        recovery_win = Tk()
                        recovery_win.focus()
                        recovery_win.protocol('WM_DELETE_WINDOW', win_close)
                        recovery_win.title('Driver Recovery')
                        recovery_win.geometry('300x100')
                        if sys.platform == 'win32':
                            recovery_win.attributes('-toolwindow', True)
                        elif sys.platform == 'darwin':
                            recovery_win.attributes('-type', 'utility')
                        recovery_win.attributes('-topmost', True)
                        recovery_win.resizable(False, False)
                        label_text = 'Existing driver found.'
                        recovery_label = Label(recovery_win, text=label_text)
                        recovery_label.pack()
                        label_text = 'Would you like to recover previous driver?'
                        recovery_label2 = Label(recovery_win, text=label_text)
                        recovery_label2.pack()
                        recovery_button = Button(recovery_win, text='Recover Driver', command=flag_recovery)
                        recovery_button.pack()
                        recovery_win.wait_window()

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
            else:
                shutil.rmtree(self.temp_root_dir)
                os.mkdir(self.temp_root_dir)
                with open(instance_path, 'w', errors='ignore') as out_file:
                    out_file.writelines(f'{self.instance_id}\n')
        else:
            os.mkdir(self.temp_root_dir)
            with open(os.path.join(self.temp_root_dir, 'instance'), 'w', errors='ignore') as out_file:
                out_file.writelines(f'{self.instance_id}\n')
        os.mkdir(self.temp_dir)
        # Initialize main program
        self.root = TkinterDnD.Tk()
        self.root.report_callback_exception = exception_handler
        warnings.showwarning = exception_handler
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
        self.version_label.place(relx=0.997, rely=1.005, anchor='se')
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
        self.easter_recall_id = None
        self.img_bank_size = 4
        self.connections = [Connection(self) for _ in range(18)]
        self.conn_ids = []
        self.states = [State('') for _ in range(13)]
        self.state_dupes = []
        self.states_orig_names = []
        self.device_icon_dir = os.path.join(www_path := os.path.join(self.temp_dir, 'driver', 'www'), 'icons', 'device')
        self.icon_dir = os.path.join(www_path, 'icons')
        self.images_dir = os.path.join(www_path, 'images')
        self.orig_file_dir, self.orig_file_path, self.restore_entry_string = '', '', ''
        self.driver_selected, self.schedule_entry_restore = False, False
        self.undo_history = deque(maxlen=10)

        # Panel Separators
        self.separator0 = ttk.Separator(self.root, orient='vertical')
        self.separator1 = ttk.Separator(self.root, orient='vertical')
        self.separator0.place(x=305, y=0, height=270)
        self.separator1.place(x=610, y=0, height=270)

        # Panels; Creating blank image for panels
        with Image.open(asset_path('assets/blank_img.png')) as img:
            self.blank = ImageTk.PhotoImage(img.resize((128, 128)))
            self.img_bank_blank = ImageTk.PhotoImage(img.resize((60, 60)))

        # Initialize Panels
        self.c4z_panel = C4zPanel(self)
        self.replacement_panel = ReplacementPanel(self)
        self.export_panel = ExportPanel(self)
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
        self.file.add_command(label='Load Multi Driver', command=lambda: self.c4z_panel.load_gen_driver(multi=True))

        self.edit = Menu(self.menu, tearoff=0)
        self.edit.add_command(label='Driver Info', command=lambda: self.open_edit_win(self.driver_info_win, 'driver'))
        self.edit.add_command(label='Connections', command=lambda: self.open_edit_win(self.connections_win, 'conn'))
        self.edit.add_command(label='States', command=lambda: self.open_edit_win(self.states_win, 'states'))
        self.edit.add_separator()
        self.edit.add_command(label='UnRestore All', command=lambda: self.c4z_panel.unrestore(do_all=True))
        self.edit.add_command(label='UnRestore Icon', command=self.c4z_panel.unrestore)
        self.edit.add_separator()
        self.edit.add_command(label='Undo', command=self.undo)
        self.states_pos = 2
        self.edit.entryconfig(self.states_pos, state=DISABLED)
        self.unrestore_all_pos = 4
        self.edit.entryconfig(self.unrestore_all_pos, state=DISABLED)
        self.unrestore_pos = 5
        self.edit.entryconfig(self.unrestore_pos, state=DISABLED)
        self.undo_pos = 7
        self.edit.entryconfig(self.undo_pos, state=DISABLED)

        self.menu.add_cascade(label='File', menu=self.file)
        self.menu.add_cascade(label='Edit', menu=self.edit)

        # Create window icon
        self.root.iconbitmap(default=asset_path('assets/icon.ico'))

        global global_instance_id
        global_instance_id = self.instance_id

        # Do recovery if necessary
        if self.recover_instance:
            self.c4z_panel.load_c4z(recovery=True)
            recovery_path = os.path.join(self.temp_root_dir, self.recover_instance, 'Replacement Icons')
            for file in os.listdir(recovery_path):
                if file.endswith(valid_img_types):
                    img_path = os.path.join(recovery_path, file)
                    self.replacement_panel.load_replacement(file_path=img_path)
                    os.remove(img_path)
            self.replacement_panel.file_entry_field['state'] = NORMAL
            self.replacement_panel.file_entry_field.delete(0, END)
            self.replacement_panel.file_entry_field.insert(0, 'Recovered Image')
            self.replacement_panel.file_entry_field['state'] = 'readonly'
            shutil.rmtree(os.path.join(self.temp_root_dir, self.recover_instance))
            self.ask_to_save = True
            self.recover_instance = ''

        # Main Loop
        self.root.config(menu=self.menu)
        # noinspection PyTypeChecker
        self.root.after(150, self.instance_check)
        self.root.protocol('WM_DELETE_WINDOW', self.on_program_exit)
        self.root.focus_force()
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
            self.c4z_panel.inc_icon()
        elif event.keysym == 'Left':
            self.c4z_panel.inc_icon(inc=-1)
        elif event.keysym == 'Up':
            self.replacement_panel.inc_img_bank()
        elif event.keysym == 'Down':
            self.replacement_panel.dec_img_bank()

    def get_states(self, lua_file):
        self.states_orig_names = []
        # Match 'state_OPTIONS' + 0 or more white spaces + '=' + white space + '{'
        if not (states_index := re.search(r'state_OPTIONS\s*=\s*\{', lua_file)):
            return False
        states_index = states_index.start()
        if states_index < 0:
            return False
        states_str = ''
        bracket_count = 0
        for i, char in enumerate(lua_file[states_index:]):
            if char == '{':
                bracket_count += 1
                continue
            if char == '}':
                bracket_count -= 1
                if not bracket_count:
                    states_str = lua_file[states_index:states_index + i]
                    break
        if not states_str:
            return False
        # Find '{' + 0 or more white spaces + 1 or more alphanumeric char including '_' + white space + '='
        self.states_orig_names = re.findall(r'\{\s*(\w+)\s*=', states_str)[1:]
        for i, state_name in enumerate(self.states_orig_names):
            if self.states_win:
                self.states_win.states[i].name_entry['state'] = NORMAL
            self.states[i].name_var.set(state_name)
            self.states[i].original_name = state_name
        return True

    def blink_driver_name_entry(self):
        if not self.counter:
            return
        self.counter -= 1
        if self.export_panel.driver_name_entry['background'] != light_entry_bg:
            self.export_panel.driver_name_entry['background'] = light_entry_bg
        else:
            self.export_panel.driver_name_entry['background'] = 'pink'
        # noinspection PyTypeChecker
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
                if os.path.isdir(failed_id_path := os.path.join(self.temp_root_dir, failed_id)):
                    shutil.rmtree(failed_id_path)
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

        yes_button = Button(save_dialog, text='Yes', width='10', command=do_project_save)
        yes_button.grid(row=2, column=0, sticky='e', padx=5)

        no_button = Button(save_dialog, text='No', width='10', command=exit_save_dialog)
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
        version_compare = re.sub(r'\D', '', version_str := self.driver_version_new_var.get()).lstrip('0')

        if self.driver_info_win and (str_diff := len(version_str) - len(version_compare)):
            cursor_pos = self.driver_info_win.driver_ver_new_entry.index(INSERT)
            self.driver_info_win.driver_ver_new_entry.icursor(cursor_pos - str_diff)
            self.driver_version_new_var.set(version_compare)

        self.ask_to_save = True

    def validate_man_and_creator(self, string_var=None, entry=None):
        if not string_var or not entry:
            return
        name_compare = re_valid_chars.sub('', name := string_var.get())
        if self.driver_info_win and (str_diff := len(name) - len(name_compare)):
            cursor_pos = entry.index(INSERT)
            entry.icursor(cursor_pos - str_diff)
            string_var.set(name_compare)

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
            # noinspection PyTypeChecker
            pickle.dump(C4IS(self), output)
        self.ask_to_save = False

    def load_project(self, *_):
        if filename := filedialog.askopenfilename(filetypes=[('C4IconSwapper Project', '*.c4is')]):
            self.load_c4is(filename)

    def load_c4is(self, file):
        while self.replacement_panel.multi_threading:
            pass
        save_state = file
        if isinstance(file, str):
            with open(file, 'rb') as file:
                save_state = pickle.load(file)
        if not isinstance(save_state, C4IS):
            raise TypeError(f'Expected type: {C4IS.__name__}')

        # C4z Panel (and export button)
        self.c4z_panel.icons = []
        self.c4z_panel.current_icon = 0
        self.c4z_panel.c4_icon_label.configure(image=self.blank)
        if os.path.isdir(driver_folder := os.path.join(self.temp_dir, 'driver')):
            shutil.rmtree(driver_folder)
        self.c4z_panel.restore_button['state'] = DISABLED
        if save_state.driver_selected:
            with open(saved_driver_path := os.path.join(self.temp_dir, 'saved_driver.c4z'), 'wb') as driver_zip:
                driver_zip.write(save_state.driver_zip)
            self.c4z_panel.load_c4z(saved_driver_path)
            os.remove(saved_driver_path)
        else:
            self.export_panel.export_button['state'] = DISABLED
            self.export_panel.export_as_button['state'] = DISABLED
            self.c4z_panel.icon_name_label.config(text='icon name')
            self.c4z_panel.icon_num_label.config(text='0 of 0')
        self.driver_selected = save_state.driver_selected

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
            self.connections[i].id_group = conn['id_group']
            self.connections[i].in_id_group = conn['in_id_group']
            self.connections[i].delete = conn['delete']
            self.connections[i].prior_txt = conn['prior_txt']
            self.connections[i].prior_type = conn['prior_type']
            self.connections[i].tag = conn['tag']
            self.connections[i].type.set(conn['type'])
            self.connections[i].name_entry_var.set(conn['name'])
            self.connections[i].enabled = conn['state']

        # Export Panel
        self.export_panel.driver_name_var.set(save_state.driver_name_var)
        self.export_panel.inc_driver_version.set(save_state.inc_driver_version)
        self.export_panel.include_backups.set(save_state.include_backups)

        # Replacement Panel
        self.replacement_panel.img_bank_select_lockout = {}
        replacement_dir = self.replacement_panel.replacement_icons_dir
        if os.path.isdir(replacement_dir):
            shutil.rmtree(replacement_dir)
        os.mkdir(replacement_dir)
        if save_state.replacement:
            save_state.replacement.save(os.path.join(replacement_dir, 'replacement.png'))
            save_state.replacement.close()
            self.replacement_panel.replacement_icon = (
                Icon(os.path.join(replacement_dir, 'replacement.png')))
            self.replacement_panel.replacement_img_label.configure(
                image=self.replacement_panel.replacement_icon.tk_icon_lg)
            self.replacement_panel.replacement_img_label.image = self.replacement_panel.replacement_icon.tk_icon_lg
        self.replacement_panel.img_bank = []
        for img_bank_label in self.replacement_panel.img_bank_tk_labels:
            img_bank_label.configure(image=self.img_bank_blank)
        next_num = get_next_num()
        for img in save_state.img_bank:
            img_path = os.path.join(replacement_dir, f'img_bank{next(next_num)}.png')
            img.save(img_path)
            img.close()
            self.replacement_panel.img_bank.append(Icon(img_path))
        self.replacement_panel.refresh_img_bank()
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
            self.connections_win = ConnectionsWin(self)
        elif win_type == 'driver':
            self.driver_info_win = DriverInfoWin(self)
        elif win_type == 'states':
            self.states_win = StatesWin(self)

    # TODO: Make the undo feature in an actually decent way
    def undo(self, *_):
        if not self.undo_history:
            self.edit.entryconfig(self.undo_pos, state=DISABLED)
            return
        current_icon = self.c4z_panel.current_icon
        ask_to_save = self.ask_to_save
        self.ask_to_save = False
        self.load_c4is(self.undo_history.pop())
        self.c4z_panel.current_icon = current_icon
        self.c4z_panel.update_icon()

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

        # noinspection PyTypeChecker
        self.root.after(150, self.instance_check)

    def easter(self, *_, increment=True):
        if self.easter_counter < 0:
            self.easter_counter = 0
            return
        if self.easter_recall_id:
            self.root.after_cancel(self.easter_recall_id)
        if self.easter_counter > 10:
            self.easter_counter = 0
            text, rely = ('\u262D', 1.027) if self.version_label.cget('text') == '\U0001F339' else ('\U0001F339', 1.02)
            self.version_label.config(text=text, font=(label_font, 30))
            self.version_label.place(relx=1.003, rely=rely)
        else:
            self.easter_counter += 1 if increment else -1
            # noinspection PyTypeChecker
            self.easter_recall_id = self.root.after(500, lambda: self.easter(increment=False))


class Icon:
    def __init__(self, path: str, img=None):
        if not os.path.isfile(path):
            raise FileNotFoundError('Failed to find path to image file')
        if not path.endswith(valid_img_types):
            raise TypeError('Invalid image type')
        self.path = path
        self.tk_icon_lg = None
        self.tk_icon_sm = None

        def create_tk_icons(pil_img):
            self.tk_icon_lg = ImageTk.PhotoImage(pil_img.resize((128, 128), Resampling.LANCZOS))
            self.tk_icon_sm = ImageTk.PhotoImage(pil_img.resize((60, 60), Resampling.LANCZOS))
        if img:
            create_tk_icons(img)
        else:
            with Image.open(self.path) as img:
                create_tk_icons(img)


class C4SubIcon:
    def __init__(self, root_path: str, img_path: str, name: str, size: int | tuple[int, int], bak_path=None):
        self.root = root_path  # Path to directory containing image
        self.path = img_path  # Full path to image file
        path_parts = Path(img_path).parts
        split_i = next(path_parts.index(part) for part in path_parts if part == global_instance_id)
        split_i = next(path_parts.index(part) for part in path_parts[split_i+1:] if part in ('icons', 'images'))
        self.rel_path = os.path.join(*list(path_parts[split_i:]))
        self.full_name = os.path.split(img_path)[-1]
        self.name = name
        self.bak_path = bak_path
        if isinstance(size, int) and not isinstance(size, bool):
            self.size = (size, size)
        elif (isinstance(size, (tuple, list)) and len(size) == 2 and
              all(isinstance(n, int) and not isinstance(n, bool) for n in size)):
            self.size = tuple(size)
        else:
            raise ValueError(f'Expected int or (int, int). Received: {type(size).__name__}: {size}')


class C4Icon(Icon):
    def __init__(self, icons: list[C4SubIcon], name=None, replacement_icon=None, extra=False):
        icons.sort(key=lambda sub_icon: sub_icon.size[0], reverse=True)
        icon = icons[0]
        super().__init__(path=icon.path)
        self.tk_icon_sm = None
        self.name = icon.name if not name else name
        self.root = icon.root  # Path to directory containing 'icon'
        self.icons = icons
        self.extra = extra
        self.bak = any(icn.bak_path for icn in icons)
        self.replacement_icon = replacement_icon
        self.restore_bak = False
        self.bak_tk_icon = None
        if self.bak:
            icon = max(icons, key=lambda sub_icon: sub_icon.size[0] if sub_icon.bak_path else None)
            with Image.open(icon.bak_path) as img:
                self.bak_tk_icon = ImageTk.PhotoImage(img.resize((128, 128), Resampling.LANCZOS))

    def get_tk_img(self):
        if self.replacement_icon:
            return self.replacement_icon.tk_icon_lg
        if self.restore_bak:
            return self.bak_tk_icon
        return self.tk_icon_lg

    def set_restore(self):
        if self.replacement_icon:
            self.replacement_icon = None
            return
        self.restore_bak = True if self.bak else False

    def replace(self, icon: Icon):
        self.replacement_icon = icon

    def refresh_tk_img(self):
        with Image.open(self.path) as img:
            self.tk_icon_lg = ImageTk.PhotoImage(img.resize((128, 128), Resampling.LANCZOS))


class ConnectionsWin:
    def __init__(self, main: C4IconSwapper):
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

        self.connections = [ConnectionEntry(self, self.main.connections[
            (x * 6) + y], x * x_spacing + 15, y * y_spacing + 25) for x, y in itertools.product(range(3), range(6))]

    def refresh(self):
        for conn_entry in self.connections:
            conn_entry.refresh()


class Connection:
    def __init__(self, main: C4IconSwapper):
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
            self.in_id_group = any(conn is not self and conn.original and conn.id == self.id
                                   for conn in self.main.connections)
            return
        if not refresh:
            return
        conn_type = self.type.get()
        valid_id = conn_id_type[conn_type][0]
        while valid_id in self.main.conn_ids:
            valid_id += 1
        self.tag.get_tag('type').set_value(conn_id_type[conn_type][1])
        if self.id in self.main.conn_ids:
            self.main.conn_ids.pop(self.main.conn_ids.index(self.id))
        self.id = valid_id
        self.tag.get_tag('id').set_value(str(self.id))
        self.main.conn_ids.append(self.id)


class ConnectionEntry:
    def __init__(self, parent: ConnectionsWin, conn_obj: Connection, x_pos: int, y_pos: int):
        # Initialize Connection UI Object
        self.window = parent.window
        self.main = parent.main
        self.conn_object = conn_obj
        self.x, self.y = x_pos, y_pos

        # Entry
        self.name_entry_var = conn_obj.name_entry_var
        self.name_entry_var.trace_add('write', self.name_update)
        self.name_entry = Entry(self.window, width=20, textvariable=self.name_entry_var)
        self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
        if not self.conn_object.enabled:
            self.name_entry['state'] = DISABLED

        # Dropdown
        self.type = conn_obj.type
        self.type_menu = OptionMenu(self.window, self.type, *selectable_connections)
        self.type_menu.place(x=self.x + 160, y=self.y, anchor='w')
        self.type.trace_add('write', self.conn_object.update_id)
        if not self.conn_object.enabled:
            self.type_menu['state'] = DISABLED

        # Buttons
        self.add_button = Button(self.window, text='Add', width=3, command=self.enable, takefocus=0)
        if self.conn_object.enabled or self.conn_object.original:
            self.add_button.place(x=-420, y=-420, anchor='w')
        else:
            self.add_button.place(x=self.x, y=self.y, anchor='w')
        if not self.main.driver_selected:
            self.add_button['state'] = DISABLED

        self.x_button = Button(self.window, text='x', width=1, command=self.disable, takefocus=0)
        if self.conn_object.enabled and not self.conn_object.original:
            self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
        else:
            self.x_button.place(x=-420, y=-420, anchor='w')

        self.del_button = Button(self.window, text='Del', width=3, command=self.flag_delete, takefocus=0)
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
                if all(self.main.connections[i].delete for i in self.conn_object.id_group if i):
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


class DriverInfoWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', main.close_driver_info)
        self.window.title('Edit Driver Info')
        self.window.geometry('255x240')
        self.window.geometry(f'+{main.root.winfo_rootx() + main.export_panel.x}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        # Validate driver version
        if (main.export_panel.inc_driver_version.get() and
                main.driver_version_var.get() and main.driver_version_new_var.get() and
                int(main.driver_version_new_var.get()) <= int(main.driver_version_var.get())):
            main.driver_version_new_var.set(str(int(main.driver_version_var.get()) + 1))

        # Labels
        instance_id_label = Label(self.window, text=f'program instance id: {main.instance_id}')

        man_y = 20
        man_arrow = Label(self.window, text='\u2192', font=('', 15))

        creator_y = man_y + 55
        creator_arrow = Label(self.window, text='\u2192', font=('', 15))

        version_y = creator_y + 55
        version_arrow = Label(self.window, text='\u2192', font=('', 15))

        font_size = 10
        driver_ver_orig_label = Label(self.window, text='Original Version:', font=(label_font, 8))
        driver_man_label = Label(self.window, text='Driver Manufacturer', font=(label_font, font_size))
        driver_creator_label = Label(self.window, text='Driver Creator', font=(label_font, font_size))
        driver_ver_label = Label(self.window, text='Driver Version', font=(label_font, font_size))

        # Entry
        entry_width = 17
        driver_man_entry = Entry(self.window, width=entry_width, textvariable=main.driver_manufac_var)
        driver_man_entry['state'] = DISABLED
        self.driver_man_new_entry = Entry(self.window, width=entry_width,
                                          textvariable=main.driver_manufac_new_var)
        main.driver_manufac_new_var.trace_add('write',
                                              lambda name, index, mode: main.validate_man_and_creator(
                                                  entry=self.driver_man_new_entry))

        driver_creator_entry = Entry(self.window, width=entry_width, textvariable=main.driver_creator_var)
        driver_creator_entry['state'] = DISABLED
        self.driver_creator_new_entry = Entry(self.window, width=entry_width,
                                              textvariable=main.driver_creator_new_var)
        main.driver_creator_new_var.trace_add('write',
                                              lambda name, index, mode: main.validate_man_and_creator(
                                                  string_var=main.driver_creator_new_var,
                                                  entry=self.driver_creator_new_entry))

        driver_ver_entry = Entry(self.window, width=entry_width, textvariable=main.driver_version_var)
        driver_ver_entry['state'] = DISABLED
        self.driver_ver_new_entry = Entry(self.window, width=entry_width,
                                          textvariable=main.driver_version_new_var)
        self.driver_ver_new_entry.bind('<FocusOut>', main.export_panel.update_driver_version)
        main.driver_version_new_var.trace_add('write', main.validate_driver_ver)
        driver_ver_orig_entry = Entry(self.window, width=6, textvariable=main.driver_ver_orig)
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
    def __init__(self, main: C4IconSwapper):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', main.close_states)
        self.window.title('Edit Driver States')
        self.window.geometry('385x287')
        self.window.geometry(f'+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)
        self.trace_lockout = False

        self.state_entries = []
        x_spacing, y_spacing = 200, 34
        x_offset, y_offset = 10, 30
        self.state_entries.extend(StateEntry(self, main.states[i], int(i / 7) * x_spacing + x_offset,
                                             (i % 7) * y_spacing + y_offset, label=f'state{str(i + 1)}:')
                                  for i in range(13))

    def refresh(self, bg_only=False):
        trace_lockout = self.trace_lockout
        self.trace_lockout = True
        for state_entry in self.state_entries:
            state_entry.refresh(bg_only)
        self.trace_lockout = trace_lockout

    def validate_states(self, *_):
        self.main.ask_to_save = True
        self.trace_lockout = True
        # Update/format names and reset entry bg colors
        for state_entry in self.state_entries:
            state_entry.update_state_name()
            state_entry.state_object.bg_color = light_entry_bg
        # Count occurrences of each name
        name_counts = Counter(state_entry.get() for state_entry in self.state_entries)
        for name in name_counts:
            # If name occurs more than once, change bg color to pink
            if name_counts[name] > 1:
                for state_entry in self.state_entries:
                    if state_entry.get() == name:
                        state_entry.state_object.bg_color = 'pink'
                continue
            # Else if name is in original names and does not match own original name, set bg color to cyan
            if name in self.main.states_orig_names:
                break_out = False
                for state_entry in self.state_entries:
                    if state_entry.get() == name and state_entry.original_name != name:
                        if break_out:
                            break
                        for compare_entry in self.state_entries:
                            if state_entry is compare_entry:
                                continue
                            if compare_entry.original_name == name:
                                state_entry.state_object.bg_color = 'cyan'
                                break_out = True
                                break
        self.refresh(bg_only=True)
        self.trace_lockout = False


class State:
    def __init__(self, name: str):
        self.original_name = name
        self.name_var = StringVar(value=name)
        background = light_entry_bg
        self.bg_color = background


class StateEntry:
    def __init__(self, parent: StatesWin, state_obj: State, x_pos: int, y_pos: int, label='State#:'):
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
        self.name_var.trace_add('write', self.on_name_update)
        self.name_entry = Entry(self.window, width=20, textvariable=self.name_var)
        self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
        self.name_entry['background'] = state_obj.bg_color
        if not self.main.multi_state_driver:
            self.name_entry['state'] = DISABLED

    def on_name_update(self, *_):
        if self.main.states_win:
            if self.main.states_win.trace_lockout:
                return
            self.main.states_win.validate_states()

    def get(self):
        return self.name_var.get()

    def update_state_name(self):
        name = self.name_var.get()
        # Substitute non-alphanumeric chars with ''
        formatted_name = re.sub(r'[^a-zA-Z0-9]', '', name).capitalize()
        if not formatted_name:
            self.name_var.set('')
            return
        if str_diff := len(name) - len(formatted_name):
            cursor_pos = self.name_entry.index(INSERT)
            self.name_entry.icursor(cursor_pos - str_diff)
        self.name_var.set(formatted_name)
        self.state_object.name_var.set(formatted_name)

    def refresh(self, bg_only=False):
        self.name_entry['background'] = self.state_object.bg_color
        if bg_only:
            return
        self.name_var.set(self.state_object.name_var.get())


class SubIconWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main
        self.icons = main.c4z_panel.icons[main.c4z_panel.current_icon].icons
        self.current_icon = 0
        self.num_of_icons = len(self.icons)

        # Initialize window
        self.window = window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', lambda: main.c4z_panel.toggle_sub_icon_win(close=True))
        self.window.title('Sub Icons')
        self.window.geometry('225x255')
        self.window.geometry(f'+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        # Labels
        self.sub_icon_label = Label(window, image=main.blank)
        self.sub_icon_label.image = main.blank
        self.sub_icon_label.place(relx=0.5, y=10, anchor='n')
        self.sub_icon_label.bind('<Button-3>', self.right_click_menu)

        self.name_label = Label(window, text='icon name', font=(mono_font, 10, 'bold'))
        self.name_label.place(relx=0.5, y=180, anchor='n')

        self.size_label = Label(window, text='0x0', font=(mono_font, 10))
        self.size_label.place(relx=0.5, y=164, anchor='n')

        self.num_label = Label(window, text='0 of 0', font=(mono_font, 10))
        self.num_label.place(relx=0.5, y=146, anchor='n')

        # Buttons
        self.prev_button = Button(window, text='Prev', command=lambda: self.inc_icon(inc=-1), width=5, takefocus=0)
        self.prev_button.place(relx=0.5, x=-4, y=222, anchor='e')
        self.next_button = Button(window, text='Next', command=self.inc_icon, width=5, takefocus=0)
        self.next_button.place(relx=0.5, x=4, y=222, anchor='w')

        self.update_icon()

    def update_icon(self):
        curr_icon = self.icons[self.current_icon]
        with Image.open(curr_icon.path) as img:
            icon_image = ImageTk.PhotoImage(img.resize((128, 128), Resampling.LANCZOS))
            self.sub_icon_label.configure(image=icon_image)
            self.sub_icon_label.image = icon_image
        self.num_label.config(text=f'{self.current_icon + 1} of {self.num_of_icons}')
        self.size_label.config(text=f'{curr_icon.size[0]}x{curr_icon.size[1]}')
        self.name_label.config(text=curr_icon.full_name)

    def inc_icon(self, inc=1):
        self.current_icon = (self.current_icon + inc) % self.num_of_icons
        self.update_icon()

    def right_click_menu(self, event):
        context_menu = Menu(self.main.root, tearoff=0)
        context_menu.add_command(label='Show icon in folder', command=self.open_icon_folder)
        context_menu.tk_popup(event.x_root, event.y_root)
        context_menu.grab_release()

    def open_icon_folder(self, *_):
        path = os.path.normpath(self.icons[self.current_icon].path)  # normalize just to be safe
        subprocess.Popen(f'explorer /select,"{path}"')


class C4zPanel:
    def __init__(self, main: C4IconSwapper):
        # Initialize C4z Panel
        self.main = main
        self.x, self.y = 5, 20
        self.current_icon, self.extra_icons = 0, 0
        self.icons = []
        self.valid_connections = ['HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI', 'STEREO', 'DIGITAL_OPTICAL',
                                  *selectable_connections]

        self.sub_icon_win = None

        # Labels
        self.panel_label = Label(main.root, text='Driver Selection', font=(label_font, 15))

        self.c4_icon_label = Label(main.root, image=main.blank)
        self.c4_icon_label.image = main.blank
        self.c4_icon_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.c4_icon_label.bind('<Button-3>', self.right_click_menu)

        self.icon_num_label = Label(main.root, text='0 of 0', font=(mono_font, 10))
        self.icon_num_label.place(x=108 + self.x, y=180 + self.y, anchor='n')

        self.icon_name_label = Label(main.root, text='icon name', font=(mono_font, 10, 'bold'))
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

        self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')
        self.c4_icon_label.drop_target_register(DND_FILES)
        self.c4_icon_label.dnd_bind('<<Drop>>', self.drop_in_c4z)

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.load_c4z, takefocus=0)
        self.restore_button = Button(main.root, text='Restore\nOriginal Icon', command=self.restore_icon, takefocus=0)
        self.restore_button['state'] = DISABLED

        self.restore_all_button = Button(main.root, text='Restore All', command=self.restore_all, takefocus=0)
        self.restore_all_button['state'] = DISABLED

        self.prev_icon_button = Button(
            main.root, text='Prev', command=lambda: self.inc_icon(inc=-1), width=5, takefocus=0)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = Button(main.root, text='Next', command=self.inc_icon, width=5, takefocus=0)
        self.next_icon_button['state'] = DISABLED

        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')
        self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)

        # Entry
        self.file_entry_field = Entry(main.root, width=25, takefocus=0)
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field.drop_target_register(DND_FILES)
        self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_c4z)
        self.file_entry_field.insert(0, 'Select .c4z file...')
        self.file_entry_field['state'] = DISABLED

        # Checkboxes
        self.show_extra_icons = IntVar(value=0)
        self.show_extra_icons.trace_add('write', self.toggle_extra_icons)
        self.show_extra_icons_check = Checkbutton(main.root, text='show extra icons',
                                                  variable=self.show_extra_icons, takefocus=0)
        self.show_extra_icons_check.place(x=self.x + 177, y=self.y + 176, anchor='nw')
        self.show_extra_icons_check.config(state='disabled')

    def toggle_extra_icons(self, *_):
        if not self.main.driver_selected:
            return
        if not (show_extra := self.show_extra_icons.get()):
            if self.extra_icons:
                self.show_extra_icons_check.config(text=f'show extra ({self.extra_icons})')
            current_icon = self.icons[self.current_icon]
            if current_icon.extra:
                self.inc_icon()
        else:
            self.show_extra_icons_check.config(text='show extra icons')

        self.prev_icon_button['state'] = NORMAL
        self.next_icon_button['state'] = NORMAL
        if len(self.icons) - (self.extra_icons if not show_extra else 0) == 1:
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
        self.update_icon()

    def load_gen_driver(self, multi=False):
        main = self.main
        if main.ask_to_save:
            main.root.wait_window(main.ask_to_save_dialog(on_exit=False))

        with Image.open(asset_path('assets/loading_img.png')) as img:
            icon = ImageTk.PhotoImage(img)
            self.c4_icon_label.configure(image=icon)
            self.c4_icon_label.image = icon
        main.root.update()

        rel_path = 'assets/multi_generic.c4z' if multi else 'assets/generic.c4z'
        gen_driver_path = asset_path(rel_path)

        if os.path.isdir(temp_driver_path := os.path.join(main.temp_dir, 'driver')):
            shutil.rmtree(temp_driver_path)

        shutil.unpack_archive(gen_driver_path, temp_driver_path, 'zip')

        sizes = [70, 90, 300, 512]
        root_size = '1024'
        temp_dir = os.path.join(main.temp_dir, 'temp_unpacking')
        os.mkdir(temp_dir)
        for img_name in os.listdir(main.device_icon_dir):
            img = Image.open(os.path.join(main.device_icon_dir, img_name))
            for size in sizes:
                resized_img = img.resize((size, size), Resampling.LANCZOS)
                resized_img.save(os.path.join(temp_dir, img_name.replace(root_size, str(size))))
        for img in os.listdir(temp_dir):
            shutil.copy(os.path.join(temp_dir, img), os.path.join(main.device_icon_dir, img))

        shutil.make_archive(os.path.join(temp_dir, 'driver'), 'zip', temp_driver_path)
        self.load_c4z(f'{os.path.join(temp_dir, "driver")}.zip')
        shutil.rmtree(temp_dir)

        main.export_panel.driver_name_entry.delete(0, 'end')
        main.export_panel.driver_name_entry.insert(0, 'New Driver')
        main.ask_to_save = False

    def update_icon(self):
        if not (icons := self.icons):
            return
        if self.current_icon < 0:
            raise ValueError('Expected positive icon index')
        if self.current_icon >= len(icons):
            self.current_icon = self.current_icon % len(icons)

        icon_image = icons[self.current_icon].get_tk_img()
        self.c4_icon_label.configure(image=icon_image)
        self.c4_icon_label.image = icon_image

        curr_icon = icons[self.current_icon]
        self.icon_name_label.config(text=f'{curr_icon.name}')
        show_extra = self.show_extra_icons.get()
        visible_icons = len(icons) - (self.extra_icons if not show_extra else 0)
        current_icon_num = self.current_icon + 1
        self.icon_num_label.config(text=f'{current_icon_num} of {visible_icons}')

        bak_check = not curr_icon.restore_bak and curr_icon.bak
        restore_state = NORMAL if (bak_check or curr_icon.replacement_icon) else DISABLED
        self.restore_button['state'] = restore_state

        def skp(icn):
            return icn.extra and not self.show_extra_icons.get()

        if restore_state is NORMAL:
            self.restore_all_button['state'] = NORMAL
        elif any((icon.replacement_icon or (not icon.restore_bak and icon.bak)) for icon in icons if not skp(icon)):
            self.restore_all_button['state'] = NORMAL
        else:
            self.restore_all_button['state'] = DISABLED

        unrestore_state = DISABLED
        if restore_state is NORMAL:
            self.main.edit.entryconfig(self.main.unrestore_pos, state=DISABLED)
        elif not curr_icon.replacement_icon and (curr_icon.restore_bak and curr_icon.bak):
            self.main.edit.entryconfig(self.main.unrestore_pos, state=(unrestore_state := NORMAL))
        else:
            self.main.edit.entryconfig(self.main.unrestore_pos, state=DISABLED)

        if unrestore_state is NORMAL:
            self.main.edit.entryconfig(self.main.unrestore_all_pos, state=NORMAL)
        elif any(not icon.replacement_icon and (icon.restore_bak and icon.bak) for icon in icons if not skp(icon)):
            self.main.edit.entryconfig(self.main.unrestore_all_pos, state=NORMAL)
        else:
            self.main.edit.entryconfig(self.main.unrestore_all_pos, state=DISABLED)

    def load_c4z(self, given_path=None, recovery=False):
        def get_icons(root_directory):
            if not root_directory:
                return []
            directories = set()
            if isinstance(root_directory, (list, tuple)):
                for i in root_directory:
                    if not os.path.isdir(i):
                        continue
                    directories.update(list_all_sub_directories(i, include_root_dir=True))
                if not directories:
                    return []
            elif isinstance(root_directory, str):
                if not os.path.isdir(root_directory):
                    return []
                directories.update(list_all_sub_directories(root_directory, include_root_dir=True))
            else:
                return []
            self.extra_icons = 0
            output = []
            icon_groups = defaultdict(list)
            both_scheme = deque()
            all_sub_icons = []
            bak_files = {}
            for directory in directories:
                for item in os.scandir(directory):
                    if not item.is_file():
                        continue
                    if re.search(r'\.bak[^.]*$', item.name):
                        root_name = re.sub(r'\.bak[^.]*$', '', item.name)
                        bak_files[os.path.join(directory, root_name)] = os.path.join(directory, item.name)
                        continue
                    try:
                        with Image.open(item.path) as img:
                            actual_size = img.size[0]
                    except UnidentifiedImageError:
                        continue
                    file_stem, file_ext = os.path.splitext(item.name)
                    img_info = re.search(r'^(?:(\d+)_)?(.+?)(?:_(\d+))?$', file_stem).groups()
                    img_name = img_info[1]
                    if not img_name or file_stem in ('device_sm', 'device_lg'):
                        img_name = file_stem
                    # If XOR left/right size labels exist
                    if ((l_label := img_info[0]) is None) != ((r_label := img_info[2]) is None):
                        if (l_label and int(l_label) == actual_size) or int(r_label) == actual_size:
                            icon_groups[img_name].append(C4SubIcon(directory, item.path, img_name, actual_size))
                            all_sub_icons.append(icon_groups[img_name][-1])
                            continue
                    elif l_label and r_label:
                        r_size = int(r_label)
                        if l_label == r_label and r_size == actual_size:
                            both_scheme.append(C4SubIcon(directory, item.path, img_name, actual_size))
                            all_sub_icons.append(both_scheme[-1])
                            continue
                        elif r_size == actual_size:
                            img_name = f'{l_label}_{img_name}'
                        elif int(l_label) == actual_size:
                            img_name = f'{img_name}_{r_label}'
                        icon_groups[img_name].append(C4SubIcon(directory, item.path, img_name, actual_size))
                        all_sub_icons.append(icon_groups[img_name][-1])
                        continue
                    icon_groups[img_name].append(C4SubIcon(directory, item.path, img_name, actual_size))
                    all_sub_icons.append(icon_groups[img_name][-1])

            # Handle icons which have numbers on both sides that match their size
            for sub_icon in both_scheme:
                found = None
                if f'{sub_icon.size[0]}_{sub_icon.name}' in icon_groups:
                    found = 'r'
                if f'{sub_icon.name}_{sub_icon.size[0]}' in icon_groups:
                    found = 'l' if not found else 'b'
                if not found:
                    icon_name = f'{sub_icon.size[0]}_{sub_icon.name}_{sub_icon.size[0]}'
                    sub_icon.name = icon_name
                    icon_groups[icon_name].append(sub_icon)
                elif found == 'r':
                    icon_name = f'{sub_icon.size[0]}_{sub_icon.name}'
                    sub_icon.name = icon_name
                    icon_groups[icon_name].append(sub_icon)
                elif found == 'l':
                    icon_name = f'{sub_icon.name}_{sub_icon.size[0]}'
                    sub_icon.name = icon_name
                    icon_groups[icon_name].append(sub_icon)
                else:
                    warnings.warn(f'Failed to parse icon data: {sub_icon.path}', RuntimeWarning)

            # Update .bak status of all sub_icons
            for sub_icon in all_sub_icons:
                if bak_path := bak_files.get(sub_icon.path):
                    sub_icon.bak_path = bak_path

            # Use XML data to form icon groups
            extras = []
            standard_icons = []
            group_dict = get_icon_groups()
            for group in group_dict:
                group_list = []
                # range(start, stop, step)
                for i in range(len(all_sub_icons) - 1, -1, -1):
                    sub_icon = all_sub_icons[i]
                    if sub_icon.rel_path in group_dict[group]:
                        group_list.append(all_sub_icons.pop(i))
                if not group_list:
                    continue
                standard_icons.append(C4Icon(group_list, name=group[0]))

            # Separate 'device' icons from list
            device_group = []
            for i in range(len(all_sub_icons) - 1, -1, -1):
                sub_icon = all_sub_icons[i]
                if sub_icon.root == main.icon_dir:
                    if sub_icon.name == 'device_sm':
                        device_group.append(all_sub_icons.pop(i))
                    elif sub_icon.name == 'device_lg':
                        device_group.append(all_sub_icons.pop(i))
                        continue

            # Flag 'extra' icons
            for key in icon_groups:
                extra_flag = True
                if not (group_list := [subicon for subicon in icon_groups[key] if subicon in all_sub_icons]):
                    continue
                for sub_icon in group_list:
                    if extra_flag and os.path.basename(os.path.dirname(sub_icon.path)) == 'device':
                        extra_flag = False
                if extra_flag:
                    extras.append(C4Icon(group_list))
                    extras[-1].extra = True
                    continue
                standard_icons.append(C4Icon(group_list))

            # Mark extra icons as standard icons if no standard icons found
            if not standard_icons and not device_group and extras:
                self.extra_icons = 0
                for icon in extras:
                    icon.extra = False

            if device_group:
                output.append(C4Icon(device_group))
            standard_icons.sort(key=lambda c4icon: natural_key(c4icon.name))
            output.extend(standard_icons)
            extras.sort(key=lambda c4icon: natural_key(c4icon.name))
            output.extend(extras)
            self.extra_icons = sum(icon.extra for icon in output)
            return output

        def get_icon_groups():
            icon_groups = defaultdict(set)
            for tag in main.driver_xml.get_tags('proxy'):
                if value := tag.attributes.get('small_image'):
                    group_name = tag.attributes.get('name')
                    rel_path = os.path.join(*Path(value).parts)
                    icon_groups[(group_name if group_name else 'Device Icon', tag.parent)].add(rel_path)
                if value := tag.attributes.get('large_image'):
                    group_name = tag.attributes.get('name')
                    rel_path = os.path.join(*Path(value).parts)
                    icon_groups[(group_name if group_name else 'Device Icon', tag.parent)].add(rel_path)
            for tag in main.driver_xml.get_tags('Icon'):
                path_parts = Path(tag.value()).parts
                split_i = next(path_parts.index(part) for part in path_parts if part in ('icons', 'images'))
                group_name = tag.parent.attributes.get('id')
                rel_path = os.path.join(*list(path_parts[split_i:]))
                icon_groups[(group_name if group_name else tag.parent.name, tag.parent)].add(rel_path)

            seen_groups = {}
            duplicates = set()
            for key, group in icon_groups.items():
                f_group = frozenset(group)
                if f_group in seen_groups:
                    first_key = seen_groups[f_group]
                    if not first_key[1].attributes.get('id') and key[1].attributes.get('id'):
                        duplicates.add(first_key)
                        seen_groups[f_group] = key
                    else:
                        duplicates.add(key)
                else:
                    seen_groups[f_group] = key
            for dupe in duplicates:
                del icon_groups[dupe]

            return icon_groups

        if recovery and not self.main.recover_instance:
            return

        if (main := self.main).ask_to_save:
            main.root.wait_window(main.ask_to_save_dialog(on_exit=False))

        if self.file_entry_field.get() == 'Invalid driver selected...':
            self.file_entry_field['state'] = NORMAL
            self.file_entry_field.delete(0, 'end')
            if main.restore_entry_string:
                self.file_entry_field.insert(0, main.restore_entry_string)
            else:
                self.file_entry_field.insert(0, 'Select .c4z file...')
            self.file_entry_field['state'] = 'readonly'
            main.restore_entry_string = ''
            main.time_var = 0
            main.schedule_entry_restore = False

        # Backup existing driver data
        temp_bak = os.path.join(main.temp_dir, 'temp_driver_backup')
        icons_bak = None
        if self.icons:
            icons_bak = self.icons
            if os.path.isdir(temp_driver_path := os.path.join(main.temp_dir, 'driver')):
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
        main.driver_selected = False
        if os.path.isdir(driver_folder := os.path.join(main.temp_dir, 'driver')) and not recovery:
            shutil.rmtree(driver_folder)

        # Unpack selected driver
        if not recovery:
            shutil.unpack_archive(filename, driver_folder, 'zip')
        else:
            shutil.copytree(os.path.join(self.main.temp_root_dir, self.main.recover_instance, 'driver'), driver_folder)

        # Read XML
        curr_xml = main.driver_xml  # store current XML in case of abort
        main.driver_xml = XMLObject(os.path.join(main.temp_dir, 'driver', 'driver.xml'))

        # Get icons
        self.icons = get_icons((main.icon_dir, main.images_dir))

        # Update entry fields and restore driver if necessary
        if not self.icons:
            main.driver_xml = curr_xml
            self.file_entry_field['state'] = NORMAL
            if self.file_entry_field.get() not in ('Select .c4z file...', 'Invalid driver selected...'):
                # Restore existing driver data if invalid driver selected
                self.icons = icons_bak
                if os.path.isdir(temp_bak):
                    if os.path.isdir(driver_folder):
                        shutil.rmtree(driver_folder)
                    shutil.copytree(temp_bak, driver_folder)
                    shutil.rmtree(temp_bak)
                # noinspection PyTypeChecker
                main.root.after(3000, main.restore_entry_text)
                main.schedule_entry_restore = True
                main.restore_entry_string = self.file_entry_field.get()
                main.driver_selected = True
            self.file_entry_field.delete(0, 'end')
            self.file_entry_field.insert(0, 'Invalid driver selected...')
            self.file_entry_field['state'] = DISABLED
            return

        # Update entry with driver file path
        self.file_entry_field['state'] = NORMAL
        self.file_entry_field.delete(0, 'end')
        self.file_entry_field.insert(0, filename)
        self.file_entry_field['state'] = 'readonly'

        orig_file_path = Path(filename)
        main.orig_file_dir = orig_file_path.parent
        if (orig_driver_name := orig_file_path.stem) not in ('generic', 'multi generic'):
            main.export_panel.driver_name_entry.delete(0, 'end')
            main.export_panel.driver_name_entry.insert(0, orig_driver_name)
        if not main.export_panel.driver_name_entry.get():
            main.export_panel.driver_name_entry.insert(0, 'New Driver')

        main.driver_selected = True
        self.current_icon = 0
        self.update_icon()

        self.show_extra_icons.set(0)
        extra_icon_text = 'show extra icons' if not self.extra_icons else f'show extra ({self.extra_icons})'
        self.show_extra_icons_check.config(text=extra_icon_text)
        self.show_extra_icons_check.config(state='disabled' if not self.extra_icons else 'normal')

        # Update XML variables
        if man_tag := main.driver_xml.get_tag('manufacturer'):
            main.driver_manufac_var.set(man_tag.value())
        if creator_tag := main.driver_xml.get_tag('creator'):
            main.driver_creator_var.set(creator_tag.value())
        if version_tag := main.driver_xml.get_tag('version'):
            main.driver_ver_orig.set(version_tag.value())
            ver_num = re.search(r'\d*', version_tag.value())[0]
            if ver_num:
                main.driver_version_var.set(ver_num)
                ver_num = str(int(ver_num) + 1) if main.export_panel.inc_driver_version.get() else ver_num
                main.driver_version_new_var.set(ver_num)
            else:
                main.driver_version_var.set('0')
                main.driver_version_new_var.set('1')
        if id_tags := main.driver_xml.get_tags('id'):
            main.conn_ids = []
            for id_tag in id_tags:
                with contextlib.suppress(ValueError):
                    if int(id_tag.value()) not in main.conn_ids:
                        main.conn_ids.append(int(id_tag.value()))

        # Check Lua file for multi-state
        main.multi_state_driver = False
        main.edit.entryconfig(main.states_pos, state=DISABLED)
        if os.path.isfile(lua_path := os.path.join(main.temp_dir, 'driver', 'driver.lua')):
            with open(lua_path, errors='ignore') as driver_lua_file:
                driver_lua = driver_lua_file.read()
                if main.get_states(driver_lua):
                    main.multi_state_driver = True
                else:
                    main.multi_state_driver = False
        if main.multi_state_driver:
            main.edit.entryconfig(main.states_pos, state=NORMAL)
        elif main.states_win:
            main.close_states()
        main.state_dupes = []

        # Update driver prev/next buttons
        if len(self.icons) - 0 if self.show_extra_icons.get() else self.extra_icons == 1:
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
        else:
            self.prev_icon_button['state'] = NORMAL
            self.next_icon_button['state'] = NORMAL
        # Update replacement prev/next buttons
        if main.replacement_panel.replacement_icon and main.driver_selected:
            main.replacement_panel.replace_button['state'] = NORMAL
            main.replacement_panel.replace_all_button['state'] = NORMAL
        else:
            main.replacement_panel.replace_button['state'] = DISABLED
            main.replacement_panel.replace_all_button['state'] = DISABLED
        # Update Export button(s)
        if main.driver_selected:
            main.export_panel.export_button['state'] = NORMAL
            main.export_panel.export_as_button['state'] = NORMAL
        # Update 'Restore All' button in driver panel
        done = False
        self.restore_all_button['state'] = DISABLED
        for path in list_all_sub_directories(driver_folder):
            for file in os.listdir(path):
                # (?<!\.xml) = not preceded by '.xml' and file ends with '.bak' + any characters other than '.'
                if re.search(r'(?<!\.xml)\.bak[^.]*$', file):
                    self.restore_all_button['state'] = NORMAL
                    done = True
                    break
            if done:
                break
        self.update_icon()

        # Remove temp backup directory
        if os.path.isdir(temp_bak):
            shutil.rmtree(temp_bak)

        # Update connections panel
        self.get_connections()
        if main.connections_win:
            main.connections_win.refresh()
        if main.states_win:
            main.states_win.refresh()

        main.ask_to_save = False

    def restore_icon(self):
        self.main.update_undo_history()
        self.icons[self.current_icon].set_restore()
        self.update_icon()
        self.main.ask_to_save = True

    def restore_all(self):
        self.main.update_undo_history()
        show_extra = self.show_extra_icons.get()
        for icon in self.icons:
            if show_extra or not icon.extra:
                icon.set_restore()
        self.update_icon()
        self.main.ask_to_save = True

    def unrestore(self, *_, do_all=False):
        if not do_all:
            self.icons[self.current_icon].restore_bak = False
            self.update_icon()
            return
        for icon in self.icons:
            if not icon.replacement_icon and (icon.restore_bak and icon.bak):
                icon.restore_bak = False
        self.update_icon()

    def inc_icon(self, inc=1, validate=True):
        if not self.main.driver_selected or not inc:
            return

        self.current_icon = (self.current_icon + inc) % len(self.icons)

        if not validate:
            return

        show_extra = self.show_extra_icons.get()
        while self.icons[self.current_icon].extra and not show_extra:
            self.inc_icon(inc=1 if inc > 0 else -1, validate=False)

        self.update_icon()

    def get_connections(self):
        main = self.main
        if not os.path.isfile(os.path.join(main.temp_dir, 'driver', 'driver.xml')) or not main.driver_selected:
            return
        # Reinitialize all connections
        for conn in main.connections:
            conn.__init__(main)

        # Get connections from XML object
        connections = []
        if classname_tags := main.driver_xml.get_tags('classname'):
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
                            if isinstance(child, XMLTag):
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
        if len(connections) > len(main.connections):
            conn_range = len(main.connections) - 1
        else:
            conn_range = len(connections)

        # Assign panel connections to XML tags and update UI
        id_groups = []
        for i in range(conn_range):
            not_in_group = True
            for group in id_groups:
                if group[0] is connections[i][3]:
                    group.append(i)
                    not_in_group = False
            if not_in_group:
                id_groups.append([connections[i][3], i])
            main.connections[i].name_entry_var.set(connections[i][0])
            main.connections[i].type.set(connections[i][1])
            main.connections[i].id = connections[i][2]
            main.connections[i].tag = connections[i][3]
            main.connections[i].original = True

        # Fill in remaining empty connections
        for conn in main.connections:
            if conn.original:
                continue
            new_conn = XMLTag(xml_string=conn_template)
            name_tag = new_conn.get_tag('connectionname')
            name_tag.value = 'Connection Name...'
            new_conn.get_tag('classname').set_value('HDMI IN')
            new_conn.delete = True
            main.driver_xml.get_tag('connections').add_element(new_conn)
            conn.tag = new_conn

        # Form id groups
        for group in id_groups:
            for conn_i in group[1:]:
                new_group = [conn_j for conn_j in group if conn_j != conn_i]
                main.connections[conn_i].id_group = new_group
        for conn in main.connections:
            conn.update_id()

    def drop_in_c4z(self, event):
        # Find '{' + any characters until reaching the first '}' OR at least one char of non-whitespace
        paths = [path[0] if path[0] else path[1] for path in re.findall(r'\{(.*?)}|(\S+)', event.data)]
        threading.Thread(
            target=self.main.replacement_panel.load_replacement, kwargs={'file_path': paths}, daemon=True).start()
        if c4z_path := next((path for path in paths if path.endswith('.c4z') and os.path.isfile(path)), None):
            # noinspection PyUnboundLocalVariable
            self.load_c4z(given_path=c4z_path)

    def right_click_menu(self, event):
        context_menu = Menu(self.main.root, tearoff=0)
        context_menu.add_command(label='View Sub Icons', command=self.toggle_sub_icon_win)
        menu_state = NORMAL if self.icons else DISABLED
        context_menu.entryconfig(1, state=menu_state)
        context_menu.tk_popup(event.x_root, event.y_root)
        context_menu.grab_release()

    def toggle_sub_icon_win(self, close=False):
        if close and self.sub_icon_win:
            self.sub_icon_win.window.destroy()
            self.sub_icon_win = None
            return
        if not self.sub_icon_win:
            self.sub_icon_win = SubIconWin(self.main)
            return
        self.sub_icon_win.window.deiconify()


class ReplacementPanel:
    def __init__(self, main: C4IconSwapper):
        # Initialize Replacement Panel
        self.main = main
        self.x, self.y = (303, 20)
        self.replacement_icon = None
        self.img_bank, self.img_bank_tk_labels = [], []
        self.img_bank_select_lockout = {}
        self.multi_threading = False
        self.replacement_icons_dir = os.path.join(main.temp_dir, 'Replacement Icons')
        if not os.path.isdir(self.replacement_icons_dir):
            os.mkdir(self.replacement_icons_dir)

        # Labels
        self.panel_label = Label(main.root, text='Replacement Icons', font=(label_font, 15))

        self.replacement_img_label = Label(main.root, image=main.blank)
        self.replacement_img_label.image = main.blank

        x_offset = 61
        for i in range(main.img_bank_size):
            self.img_bank_tk_labels.append(Label(main.root, image=main.img_bank_blank))
            self.img_bank_tk_labels[-1].image = main.img_bank_blank
            self.img_bank_tk_labels[-1].bind('<Button-1>', lambda e, bn=i: self.select_img_bank(bn, e))
            self.img_bank_tk_labels[-1].bind('<Button-3>', self.right_click_menu)
            self.img_bank_tk_labels[-1].place(x=31 + self.x + x_offset * i, y=176 + self.y, anchor='nw')
            self.img_bank_tk_labels[-1].drop_target_register(DND_FILES)
            self.img_bank_tk_labels[-1].dnd_bind('<<Drop>>', lambda e, bn=i: self.drop_img_bank(bn, e))

        self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')

        self.replacement_img_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.replacement_img_label.drop_target_register(DND_FILES)
        self.replacement_img_label.dnd_bind('<<Drop>>', self.drop_in_replacement)
        self.replacement_img_label.bind('<Button-3>', self.right_click_menu)

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.load_replacement, takefocus=0)

        self.replace_all_button = Button(main.root, text='Replace All', command=self.replace_all, takefocus=0)
        self.replace_all_button['state'] = DISABLED

        self.replace_button = Button(main.root, text='Replace\nCurrent Icon', command=self.replace_icon, takefocus=0)
        self.replace_button['state'] = DISABLED

        self.prev_icon_button = Button(main.root, text='Prev', command=self.dec_img_bank, width=5, takefocus=0)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = Button(main.root, text='Next', command=self.inc_img_bank, width=5, takefocus=0)
        self.next_icon_button['state'] = DISABLED

        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')
        self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)

        # Entry
        self.file_entry_field = Entry(main.root, width=25, takefocus=0)
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field.drop_target_register(DND_FILES)
        self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_replacement)
        self.file_entry_field.insert(0, 'Select image file...')
        self.file_entry_field['state'] = DISABLED

    def load_replacement(self, file_path=None, bank_index=None):
        if isinstance(file_path, tuple) or isinstance(file_path, list):
            self.multi_threading = True
            for path in file_path:
                if not os.path.isdir(path):
                    self.load_replacement(file_path=path)
                    continue
                for directory in list_all_sub_directories(path, include_root_dir=True):
                    for file in os.listdir(directory):
                        if (img_path := os.path.join(directory, file)).endswith(valid_img_types):
                            self.load_replacement(file_path=img_path)
            self.multi_threading = False
            return
        if not file_path:
            if bank_index is None:
                if self.multi_threading:
                    return
                for path in filedialog.askopenfilenames(filetypes=[('Image', '*.png *.jpg *.jpeg *.gif')]):
                    self.load_replacement(file_path=path)
                return
        elif not os.path.isfile(file_path) or not file_path.endswith(valid_img_types):
            return

        main = self.main

        if file_path:
            new_path = os.path.join(self.replacement_icons_dir, Path(file_path).name)
            next_num = get_next_num(1)
            while os.path.isfile(new_path):
                new_path = os.path.join(
                    self.replacement_icons_dir, f'{Path(file_path).stem}{next(next_num)}{Path(file_path).suffix}')

            with Image.open(file_path) as img:
                output_img = img.resize((1024, 1024), Resampling.LANCZOS)
                output_img.save(new_path)
                new_size = os.path.getsize(new_path)
                # Check if image already in replacement icons directory
                for file in os.listdir(self.replacement_icons_dir):
                    if os.path.getsize(cmp_path := os.path.join(self.replacement_icons_dir, file)) != new_size:
                        continue
                    if cmp_path == new_path or not filecmp.cmp(cmp_path, new_path):
                        continue
                    os.remove(new_path)
                    if not self.img_bank or (len(self.img_bank) < main.img_bank_size and self.replacement_icon):
                        if bank_index is None:
                            return
                        self.img_bank.append(self.replacement_icon)
                        self.refresh_img_bank()
                        self.replacement_icon = None
                        self.replacement_img_label.config(image=main.blank)
                        self.replacement_img_label.image = main.blank
                        self.replace_button['state'] = DISABLED
                        self.replace_all_button['state'] = DISABLED
                        return
                    elif self.replacement_icon and self.replacement_icon.path == cmp_path and bank_index is not None:
                        rp_icon = self.replacement_icon
                        max_bank_size = main.img_bank_size - 1
                        cur_bank_size = len(self.img_bank) - 1
                        bank_index = bank_index if cur_bank_size >= max_bank_size else cur_bank_size
                        self.replacement_icon = self.img_bank[bank_index]
                        self.img_bank[bank_index] = rp_icon
                        self.replacement_img_label.configure(image=self.replacement_icon.tk_icon_lg)
                        self.replacement_img_label.image = self.replacement_icon.tk_icon_lg
                        self.refresh_img_bank()
                        return
                    elif bank_index is None:
                        if existing_icon := next((icon for icon in self.img_bank if icon.path == cmp_path), None):
                            rp_icon = self.replacement_icon if self.replacement_icon else None
                            bank_index = self.img_bank.index(existing_icon)
                            if rp_icon:
                                self.replacement_icon = existing_icon
                                self.img_bank[bank_index] = rp_icon
                            else:
                                self.replacement_icon = self.img_bank.pop(bank_index)
                                self.img_bank_tk_labels[bank_index].configure(image=main.img_bank_blank)
                                self.img_bank_tk_labels[bank_index].image = main.img_bank_blank
                                if len(self.img_bank) <= main.img_bank_size:
                                    self.prev_icon_button['state'] = DISABLED
                                    self.next_icon_button['state'] = DISABLED
                            self.refresh_img_bank()
                            self.replacement_img_label.configure(image=self.replacement_icon.tk_icon_lg)
                            self.replacement_img_label.image = self.replacement_icon.tk_icon_lg
                            return
                    if not len(self.img_bank) > 1:
                        return
                    if not (existing_icon := next((icon for icon in self.img_bank if icon.path == cmp_path), None)):
                        return
                    existing_index = self.img_bank.index(existing_icon)
                    if existing_index == bank_index or bank_index > len(self.img_bank) - 1:
                        return
                    swap_icon = self.img_bank[bank_index]
                    self.img_bank[bank_index] = existing_icon
                    self.img_bank[existing_index] = swap_icon
                    self.refresh_img_bank()
                    return
                new_icon = Icon(new_path, img=output_img)

            if bank_index is not None:
                self.add_to_img_bank(new_icon, bank_index)
                return

        if self.replacement_icon:
            if bank_index is not None:
                rp_icon = self.replacement_icon
                self.replacement_icon = self.img_bank[bank_index]
                self.img_bank[bank_index] = rp_icon
                self.refresh_img_bank()
            else:
                self.add_to_img_bank(self.replacement_icon)
        elif bank_index is not None:
            self.replacement_icon = self.img_bank.pop(bank_index)
            self.img_bank_tk_labels[bank_index].configure(image=main.img_bank_blank)
            self.img_bank_tk_labels[bank_index].image = main.img_bank_blank
            if (label_index := len(self.img_bank)) <= main.img_bank_size:
                self.prev_icon_button['state'] = DISABLED
                self.next_icon_button['state'] = DISABLED
            if label_index < main.img_bank_size:
                self.img_bank_tk_labels[label_index].configure(image=main.img_bank_blank)
                self.img_bank_tk_labels[label_index].image = main.img_bank_blank
            self.refresh_img_bank()

        if file_path:
            self.replacement_icon = new_icon
        else:
            file_path = self.replacement_icon.path

        self.file_entry_field['state'] = NORMAL
        self.file_entry_field.delete(0, 'end')
        self.file_entry_field.insert(0, file_path)
        self.file_entry_field['state'] = 'readonly'

        if main.driver_selected:
            self.replace_button['state'] = NORMAL
            self.replace_all_button['state'] = NORMAL
        else:
            self.replace_button['state'] = DISABLED
            self.replace_all_button['state'] = DISABLED

        main.replacement_selected = True

        self.replacement_img_label.configure(image=self.replacement_icon.tk_icon_lg)
        self.replacement_img_label.image = self.replacement_icon.tk_icon_lg

        if main.driver_selected:
            main.ask_to_save = True

    def add_to_img_bank(self, img: Icon, bank_index=None):
        if img in self.img_bank:
            return

        if bank_index and len(self.img_bank) >= self.main.img_bank_size:
            existing_img = self.img_bank[bank_index]
            self.img_bank[bank_index] = img
            self.img_bank.append(existing_img)
        else:
            self.img_bank.append(img)
        self.refresh_img_bank()
        if len(self.img_bank) > self.main.img_bank_size:
            self.prev_icon_button['state'] = NORMAL
            self.next_icon_button['state'] = NORMAL

        if self.main.driver_selected:
            self.main.ask_to_save = True

    def refresh_img_bank(self):
        for i, img in zip(range(self.main.img_bank_size), self.img_bank):
            self.img_bank_tk_labels[i].configure(image=img.tk_icon_sm)
            self.img_bank_tk_labels[i].image = img.tk_icon_sm

    def dec_img_bank(self):
        if self.multi_threading:
            return
        if len(self.img_bank) <= self.main.img_bank_size:
            return
        temp = self.img_bank[0]
        self.img_bank.pop(0)
        self.img_bank.append(temp)
        self.refresh_img_bank()

    def inc_img_bank(self):
        if self.multi_threading:
            return
        if len(self.img_bank) <= self.main.img_bank_size:
            return
        temp = self.img_bank[-1]
        self.img_bank.pop(-1)
        self.img_bank.insert(0, temp)
        self.refresh_img_bank()

    def replace_icon(self, update_undo_history=True, c4_icn_index=None):
        if self.multi_threading:
            return
        c4z_panel = self.main.c4z_panel
        if c4_icn_index is None:
            c4_icn_index = c4z_panel.current_icon
        elif 0 > c4_icn_index > len(c4z_panel.icons):
            raise ValueError('Current icon index out of range')

        if update_undo_history:
            self.main.update_undo_history()

        c4z_panel.icons[c4_icn_index].replace(self.replacement_icon)
        c4z_panel.restore_all_button['state'] = NORMAL
        c4z_panel.update_icon()
        self.main.ask_to_save = True

    def replace_all(self):
        if self.multi_threading:
            return
        self.main.update_undo_history()
        show_extra = self.main.c4z_panel.show_extra_icons.get()
        for i, icon in enumerate(self.main.c4z_panel.icons):
            if icon.extra and not show_extra:
                continue
            self.replace_icon(update_undo_history=False, c4_icn_index=i)

    def select_img_bank(self, bank_num: int, event):
        if self.multi_threading:
            return
        if not self.img_bank or len(self.img_bank) <= bank_num or not event:
            return
        # Debounce stack selection
        debounce_timer = 0.25
        selected_bank = f'bank{bank_num}'
        if (selected_bank in self.img_bank_select_lockout and
                time.time() - self.img_bank_select_lockout[selected_bank] < debounce_timer):
            return
        self.img_bank_select_lockout[selected_bank] = time.time()
        self.load_replacement(bank_index=bank_num)

    def drop_in_replacement(self, event, paths=None):
        if self.multi_threading:
            return
        if not paths:
            # Find '{' + any characters until reaching the first '}' OR at least one char of non-whitespace
            paths = [path[0] if path[0] else path[1] for path in re.findall(r'\{(.*?)}|(\S+)', event.data)]
        threading.Thread(target=self.load_replacement, kwargs={'file_path': paths}, daemon=True).start()

    def drop_img_bank(self, bank_num: int, event):
        if self.multi_threading:
            return
        # Find '{' + any characters until reaching the first '}' OR at least one char of non-whitespace
        paths = [path[0] if path[0] else path[1] for path in re.findall(r'\{(.*?)}|(\S+)', event.data)]
        if not paths:
            return
        if len(paths) == 1 and os.path.isfile(paths[0]):
            self.load_replacement(paths[0], bank_index=bank_num)
            return
        threading.Thread(target=self.load_replacement, kwargs={'file_path': paths}, daemon=True).start()

    def right_click_menu(self, event):
        # Assume call from replacement label
        img_index = -1
        menu_state = NORMAL
        # Check if called from img bank
        event_widget = event.widget
        for i, bank_label in enumerate(self.img_bank_tk_labels):
            if bank_label is event_widget:
                img_index = i
                if img_index >= len(self.img_bank):
                    menu_state = DISABLED
                break
        if img_index == -1 and not self.replacement_icon:
            menu_state = DISABLED
        context_menu = Menu(self.main.root, tearoff=0)
        context_menu.add_command(label='Delete Image', command=lambda: self.delete_image(img_index))
        context_menu.entryconfig(1, state=menu_state)
        context_menu.tk_popup(event.x_root, event.y_root)
        context_menu.grab_release()

    def delete_image(self, img_index: int):
        if not -1 <= img_index < self.main.img_bank_size:
            return
        if img_index == -1:
            os.remove(self.replacement_icon.path)
            self.replacement_icon = None
            self.replacement_img_label.config(image=self.main.blank)
            self.replacement_img_label.image = self.main.blank
            self.replace_button['state'] = DISABLED
            self.replace_all_button['state'] = DISABLED
            return
        os.remove(self.img_bank[img_index].path)
        self.img_bank.pop(img_index)
        if (label_index := len(self.img_bank)) <= self.main.img_bank_size:
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
        if label_index < self.main.img_bank_size:
            self.img_bank_tk_labels[label_index].configure(image=self.main.img_bank_blank)
            self.img_bank_tk_labels[label_index].image = self.main.img_bank_blank
        self.refresh_img_bank()


class ExportPanel:
    def __init__(self, main: C4IconSwapper):
        # Initialize Export Panel
        self.main = main
        self.x, self.y = (615, -50)
        self.abort = False

        # Labels
        self.panel_label = Label(main.root, text='Export', font=(label_font, 15))
        self.panel_label.place(x=145 + self.x, y=50 + self.y, anchor='n')

        self.driver_name_label = Label(main.root, text='Driver Name:')
        self.driver_name_label.place(x=65 + self.x, y=180 + self.y, anchor='w')

        # Buttons
        self.export_as_button = Button(main.root, text='Export As...', width=20, command=self.do_export, takefocus=0)
        self.export_as_button['state'] = DISABLED

        self.export_as_button.place(x=145 + self.x, y=250 + self.y, anchor='n')
        self.export_button = Button(main.root, text='Quick Export', width=20, command=self.quick_export, takefocus=0)
        self.export_button.place(x=145 + self.x, y=220 + self.y, anchor='n')
        self.export_button['state'] = DISABLED

        # Entry
        self.driver_name_var = StringVar(value='New Driver')
        self.driver_name_var.trace_add('write', self.validate_driver_name)
        self.driver_name_entry = Entry(main.root, width=25, textvariable=self.driver_name_var)
        self.driver_name_entry.place(x=145 + self.x, y=190 + self.y, anchor='n')

        # Checkboxes
        self.inc_driver_version = IntVar(value=1)
        self.inc_driver_version.trace_add('write', self.update_driver_version)
        self.inc_driver_check = Checkbutton(main.root, text='increment driver version',
                                            variable=self.inc_driver_version, takefocus=0)
        self.inc_driver_check.place(x=63 + self.x, y=150 + self.y, anchor='w')

        self.include_backups = IntVar(value=1)
        self.include_backups_check = Checkbutton(main.root, text='include backup files',
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
        if os.path.isfile(os.path.join((main := self.main).cur_dir, f'{driver_name}.c4z')):
            overwrite_pop_up = Toplevel(main.root)
            overwrite_pop_up.title('Overwrite')
            overwrite_pop_up.geometry('239x70')
            overwrite_pop_up.geometry(f'+{main.root.winfo_rootx() + self.x}+{main.root.winfo_rooty()}')
            overwrite_pop_up.protocol('WM_DELETE_WINDOW', abort)
            overwrite_pop_up.grab_set()
            overwrite_pop_up.focus()
            overwrite_pop_up.transient(main.root)
            overwrite_pop_up.resizable(False, False)

            confirm_label = Label(overwrite_pop_up, text='Would you like to overwrite the existing file?')
            confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

            yes_button = Button(overwrite_pop_up, text='Yes', width='10', command=confirm_overwrite)
            yes_button.grid(row=2, column=0, sticky='e', padx=5)

            no_button = Button(overwrite_pop_up, text='No', width='10', command=abort)
            no_button.grid(row=2, column=1, sticky='w', padx=5)
            self.do_export(quick_export=overwrite_pop_up)
            return
        self.do_export(quick_export=True)

    def export_file(self, driver_name: str, path=None):
        main = self.main
        if path is None:
            path = os.path.join(main.cur_dir, f'{driver_name}.c4z')
        bak_files_dict = {}
        bak_files = []
        bak_folder = os.path.join(main.temp_dir, 'bak_files')
        driver_folder = os.path.join(main.temp_dir, 'driver')

        # Backup and move all .bak files if not included
        if not self.include_backups.get():
            directories = list_all_sub_directories(driver_folder, include_root_dir=True)
            if os.path.isdir(bak_folder):
                shutil.rmtree(bak_folder)
            os.mkdir(bak_folder)
            suffix_num = get_next_num()
            for directory in directories:
                for file in os.listdir(directory):
                    if re.search(r'\.bak[^.]*$', file):
                        current_path = os.path.join(directory, file)
                        # I think this is to avoid same name collisions
                        new_path = os.path.join(bak_folder, f'{file}{next(suffix_num)}')
                        bak_files.append(current_path)
                        bak_files_dict[current_path] = new_path
                        shutil.copy(current_path, new_path)
                        os.remove(current_path)

        # Create .c4z file
        zip_path = f'{driver_folder}.zip'
        shutil.make_archive(driver_folder, 'zip', driver_folder)
        shutil.copy(zip_path, path)
        os.remove(zip_path)

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

        main = self.main
        driver_xml = main.driver_xml

        # Validate driver name
        driver_name = re_valid_chars.sub('', self.driver_name_var.get())
        self.driver_name_entry.delete(0, 'end')
        self.driver_name_entry.insert(0, driver_name)
        if not driver_name:
            self.driver_name_entry['background'] = 'pink'
            main.counter = 7
            # noinspection PyTypeChecker
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

            # Update state names in Lua file
            state_name_changes = {}
            if os.path.isfile(lua_path := os.path.join(main.temp_dir, 'driver', 'driver.lua')):
                # Lua file backup
                if os.path.isfile(lua_bak_path := f'{lua_path}.bak'):
                    os.remove(lua_bak_path)
                shutil.copy(lua_path, lua_bak_path)
                for state in main.states:
                    if state.original_name != state.name_var.get():
                        state_name_changes[state.original_name] = state.name_var.get()

                # Modify Lua file
                modified_lua_lines = []
                with open(lua_path, errors='ignore') as driver_lua_file:
                    driver_lua_lines = driver_lua_file.readlines()
                for line in driver_lua_lines:
                    new_line = line
                    for orig_name in state_name_changes:
                        orig_lower = orig_name.lower()
                        new = state_name_changes[orig_name]
                        new_lower = new.lower()
                        if f'{orig_name} ' in line or f'{orig_lower} ' in line:
                            new_line = new_line.replace(f'{orig_name} ', f'{new} ')
                            new_line = new_line.replace(f'{orig_lower} ', f'{new_lower} ')
                        elif f"{orig_name}'" in line or f"{orig_lower}'" in line:
                            new_line = new_line.replace(f"{orig_name}'", f"{new}'")
                            new_line = new_line.replace(f"{orig_lower}'", f"{new_lower}'")
                        elif f'{orig_name}"' in line or f'{orig_lower}"' in line:
                            new_line = new_line.replace(f'{orig_name}"', f'{new}"')
                            new_line = new_line.replace(f'{orig_lower}"', f'{new_lower}"')
                        elif f'{orig_name}=' in line or f'{orig_lower}=' in line:
                            new_line = new_line.replace(f'{orig_name}=', f'{new}=')
                            new_line = new_line.replace(f'{orig_lower}=', f'{new_lower}=')
                    modified_lua_lines.append(new_line)
                with open(lua_path, 'w', errors='ignore') as driver_lua_file:
                    driver_lua_file.writelines(modified_lua_lines)

            # Do multi-state related changes in XML
            if state_name_changes:
                for orig_name in state_name_changes:
                    orig_lower = orig_name.lower()
                    new_name = state_name_changes[orig_name]
                    new_lower = new_name.lower()
                    for item_tag in driver_xml.get_tags('item'):
                        if orig_name == item_tag.value():
                            item_tag.set_value(new_name)
                            break
                        if orig_lower == item_tag.value():
                            item_tag.set_value(new_lower)
                            break
                    for name_tag in driver_xml.get_tags('name'):
                        if orig_name == name_tag.value() or name_tag.value().endswith(orig_name):
                            name_tag.set_value(name_tag.value().replace(orig_name, new_name))
                            break
                        if orig_lower == name_tag.value() or name_tag.value().endswith(orig_lower):
                            name_tag.set_value(name_tag.value().replace(orig_lower, new_lower))
                            break
                    for description_tag in driver_xml.get_tags('description'):
                        if f'{orig_name} ' in description_tag.value():
                            description_tag.set_value(description_tag.value().replace(orig_name, new_name))
                            break
                        if f'{orig_lower} ' in description_tag.value():
                            description_tag.set_value(description_tag.value().replace(orig_lower, new_lower))
                            break
                    for state_tag in driver_xml.get_tags('state'):
                        if state_tag.attributes['id']:
                            if state_tag.attributes['id'] == orig_name:
                                state_tag.attributes['id'] = new_name
                                break
                            if state_tag.attributes['id'] == orig_lower:
                                state_tag.attributes['id'] = new_lower
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

        # Set restore point for XML object
        driver_xml.set_restore_point()

        # Update connection names
        for conn in main.connections:
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
        driver_xml.get_tag('name').set_value(driver_name)
        modified_datestamp = str(datetime.now().strftime('%m/%d/%Y %H:%M'))
        if (self.inc_driver_version.get() and
                int(main.driver_version_var.get()) >= int(main.driver_version_new_var.get())):
            main.driver_version_new_var.set(str(int(main.driver_version_var.get()) + 1))
        driver_xml.get_tag('version').set_value(main.driver_version_new_var.get())
        driver_xml.get_tag('modified').set_value(modified_datestamp)
        driver_xml.get_tag('creator').set_value(main.driver_creator_new_var.get())
        driver_xml.get_tag('manufacturer').set_value(main.driver_manufac_new_var.get())
        for attribute in driver_xml.get_tag('proxy').attributes:
            if attribute[0] == 'name':
                attribute[1] = driver_name
        for icon_tag in driver_xml.get_tags('Icon'):
            # Not OS specific; related to controller directories
            if result := re.search('driver/(.*)/icons', icon_tag.value()):
                result = result[1]
                icon_tag.set_value(icon_tag.value().replace(result, driver_name))

        # Backup XML file and write new XML
        if os.path.isfile(xml_bak_path := os.path.join(main.temp_dir, 'driver', 'driver.xml.bak')):
            os.remove(xml_bak_path)
        os.rename(xml_path := os.path.join(main.temp_dir, 'driver', 'driver.xml'), xml_bak_path)
        with open(xml_path, 'w', errors='ignore') as out_file:
            out_file.writelines(driver_xml.get_lines())

        # Make icon changes
        bak_folder = os.path.join(main.temp_dir, 'bak_files')
        if os.path.isdir(bak_folder):
            shutil.rmtree(bak_folder)
        os.mkdir(bak_folder)
        include_bak = self.include_backups.get()
        for icon in main.c4z_panel.icons:
            if icon.replacement_icon:
                rp_icon = Image.open(icon.replacement_icon.path)
                for sub_icon in icon.icons:
                    if include_bak:
                        sub_icon.bak_path = f'{sub_icon.path}.bak'
                        shutil.copy(sub_icon.path, sub_icon.bak_path)
                    out_icon = rp_icon.resize(sub_icon.size, Resampling.LANCZOS)
                    out_icon.save(sub_icon.path)
                icon.replacement_icon = None
                icon.refresh_tk_img()
            elif icon.restore_bak and icon.bak:
                for sub_icon in icon.icons:
                    if not sub_icon.bak_path:
                        continue
                    if include_bak:
                        temp_bak_path = os.path.join(bak_folder, sub_icon.name)
                        shutil.copy(sub_icon.path, temp_bak_path)
                        shutil.copy(sub_icon.bak_path, sub_icon.path)
                        shutil.copy(temp_bak_path, sub_icon.bak_path)
                        os.remove(temp_bak_path)
                    else:
                        shutil.copy(sub_icon.bak_path, sub_icon.path)
                        os.remove(sub_icon.bak_path)
                        sub_icon.bak_path = None
                icon.restore_bak = False
                icon.bak = None
                icon.bak_tk_icon = None
                icon.refresh_tk_img()

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
            if os.path.isfile(existing_file := os.path.join(main.cur_dir, f'{driver_name}.c4z')):
                os.remove(existing_file)
            self.export_file(driver_name)

        # Restore original XML and Lua
        main.driver_version_var.set(main.driver_version_new_var.get())
        if self.inc_driver_version.get():
            main.driver_version_new_var.set(str(int(main.driver_version_new_var.get()) + 1))
        driver_xml.restore()
        if os.path.isfile(lua_bak_path := os.path.join(main.temp_dir, 'driver', 'driver.lua.bak')):
            os.remove(lua_path := os.path.join(main.temp_dir, 'driver', 'driver.lua'))
            os.rename(lua_bak_path, lua_path)
        os.remove(xml_path := os.path.join(main.temp_dir, 'driver', 'driver.xml'))
        os.rename(f'{xml_path}.bak', xml_path)

    def validate_driver_name(self, *_):
        driver_name_cmp = re_valid_chars.sub('', driver_name := self.driver_name_var.get())

        if str_diff := len(driver_name) - len(driver_name_cmp):
            cursor_pos = self.driver_name_entry.index(INSERT)
            self.driver_name_entry.icursor(cursor_pos - str_diff)
            self.driver_name_var.set(driver_name_cmp)

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
        if not isinstance(main, C4IconSwapper):
            raise TypeError(f'Expected type: {C4IconSwapper.__name__}')
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
        if main.driver_selected:
            shutil.make_archive(driver_path_noext := os.path.join(main.temp_dir, 'driver'), 'zip', driver_path_noext)
            with open(driver_path := f'{driver_path_noext}.zip', 'rb') as driver_zip:
                self.driver_zip = driver_zip.read()
            os.remove(driver_path)

        # Replacement Panel
        if main.replacement_panel.replacement_icon:
            self.replacement = Image.open(main.replacement_panel.replacement_icon.path)
        else:
            self.replacement = None
        self.img_bank = [Image.open(img.path) for img in main.replacement_panel.img_bank]

        self.replacement_panel = {'replace': main.replacement_panel.replace_button['state'],
                                  'replace_all': main.replacement_panel.replace_all_button['state'],
                                  'prev': main.replacement_panel.prev_icon_button['state'],
                                  'next': main.replacement_panel.next_icon_button['state']}


def list_all_sub_directories(directory: str, include_root_dir=False):
    subs = []
    for root, dirs, _ in os.walk(directory):
        for sub in dirs:
            subs.append(os.path.join(root, sub))
    subs.sort()
    return [directory, *subs] if include_root_dir else subs


def natural_key(string: str):
    # Splits numbers from all other chars and creates list of ['string', int, etc.]
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]


def get_next_num(start=0, yield_start=True):
    if not yield_start:
        start += 1
    while True:
        yield str(start)
        start += 1


def asset_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.normpath(os.path.join(base_path, relative_path))


if __name__ == '__main__':
    C4IconSwapper()
