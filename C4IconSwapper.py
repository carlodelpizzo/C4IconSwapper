import contextlib
import copy
import ctypes
import filecmp
import io
import itertools
import os
import pickle
import random
import re
import shutil
import socket
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
from tkinter import filedialog, Toplevel, Checkbutton, IntVar, StringVar, Label, Menu, OptionMenu
from tkinter import DISABLED, NORMAL, END, INSERT, Text, Button, Entry, Frame, Canvas
from tkinter.ttk import Scrollbar, Separator
from tkinterdnd2 import DND_FILES, TkinterDnD

from XMLObject import XMLObject, XMLTag

version = '2.0dev'  # TODO: Change before release

label_font, light_entry_bg, dark_entry_bg = 'Arial', '#FFFFFF', '#282830'
re_valid_chars = re.compile(r'[^\-_ a-zA-Z0-9]')
re_natural_sort = re.compile(r'(\d+)')
valid_img_types = {'.bmp', '.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff', '.webp'}
connection_tag_generic = XMLTag(xml_string="""
<connection>
    <id>0</id>
    <type>0</type>
    <connectionname>Connection Name...</connectionname>
    <consumer>False</consumer>
    <linelevel>True</linelevel>
    <classes>
        <class>
            <classname>HDMI IN</classname>
        </class>
    </classes>
</connection>
""")
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

# TODO: replace os.move with Path.replace; reevaluate os.listdir replace with Path.iterdir()
assets_path = Path(__file__).resolve().parent / 'assets'  # For Nuitka or venv
if hasattr(sys, '_MEIPASS'):
    # noinspection PyProtectedMember
    assets_path = Path(sys._MEIPASS) / 'assets'  # For PyInstaller

max_image_pixels = Image.MAX_IMAGE_PIXELS


# Inter-Process Communication (For running multiple instances simultaneously); Port range: (49200-65500)
# I'm not very happy with separating the IPC functions into their own class, but I think it makes it more readable
# noinspection PyUnresolvedReferences
# noinspection PyAttributeOutsideInit
class IPC:
    def ipc(self, takeover=False, port=None, first_time=False):
        # noinspection PyShadowingNames
        def establish_self_as_server():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', port))  # This is where exception is raised
            print(f'Is Server: {self.instance_id}')
            self.is_server = True

            # Delete unused port files
            port_files.pop(port, None)
            for _, file_path in port_files.items():
                print(f'Trying to delete: {file_path}')
                Path(file_path).unlink(missing_ok=True)
            for file_path in invalid_port_files:
                print(f'Trying to delete: {file_path}')
                Path(file_path).unlink(missing_ok=True)

            # Start heartbeat thread (Create/update current port file)
            threading.Thread(target=self.ipc_server_heartbeat, args=[port], daemon=True).start()

            if first_time:
                if do_conflict_check:  # Check for other servers' port files after a delay
                    threading.Thread(target=self.ipc_server_conflict_check, args=[port], daemon=True).start()
                else:
                    self.finished_server_init = True
                    self.global_temp_cleanup()

            server.listen(7)
            threading.Thread(target=self.ipc_server_loop, args=[server], daemon=True).start()

        def establish_self_as_client():
            nonlocal port
            nonlocal port_files
            nonlocal invalid_port_files
            nonlocal invalid_ports

            ipc_failures = 0
            grace = True
            while True:
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    print(f'Is Client: {self.instance_id}')
                    client.settimeout(0.05)
                    client.connect(('127.0.0.1', port))
                    msg = f'ID:{self.instance_id}\n' if not self.reestablish else f'RE:{self.instance_id}\n'
                    client.sendall(msg.encode('utf-8'))

                    response = client.recv(1024).decode('utf-8')
                    if not response:
                        raise OSError('Server Disconnected; Sent Empty Message')
                    print('From Server:', repr(response))
                    for msg in response.strip().split('\n'):
                        match msg.split(':'):
                            case ['OK', server_id, client_data]:
                                self.curr_server_id = server_id
                                print(f'Became Client of Current Server: {server_id}')
                                if self.reestablish:
                                    self.reestablish = False
                                    print('Reestablishment Ended')
                                client_list = client_data.split('|')
                                self.client_dict = {k: v for s in client_list for k, v in [s.split('~')]}
                                print(self.client_dict)
                                threading.Thread(target=self.ipc_client_loop, args=[client], daemon=True).start()
                                return True
                            case ['INSTANCE ID COLLISION']:
                                if not first_time:
                                    # Hopefully this code should never run
                                    print('--- Something Went Wrong ---')
                                    print('Ignored instruction from server to change instance id')
                                    continue
                                grace = True
                                self.instance_id = str(random.randint(111111, 999999))
                                print('From Server: INSTANCE ID COLLISION')
                                print(f'New Instance ID: {self.instance_id}')
                                break
                            case _:
                                if grace:
                                    grace = False
                                    print(f'Server sent invalid response; given grace: {msg}')
                                    continue
                                raise OSError(f'Server sent invalid response: {msg}')
                except OSError as er:
                    ipc_failures += 1
                    print(er)
                    print('IPC Initialization Failed')
                    if ipc_failures > 3:
                        if port_files:
                            invalid_port_files.add(port_files.pop(port))
                            invalid_ports.add(port)
                            port = next(next_port, None)
                            if port:
                                print(f'Trying New Port: {port}')
                                return False
                        else:
                            invalid_ports.add(port)
                        while port in invalid_ports:
                            port = random.randint(49200, 65500)
                        print(f'Trying New Port: {port}')
                        return False

        port_files = {
            int(re_result.group(1)): port_file_path
            for item in os.listdir(self.appdata_folder)
            if (port_file_path := self.appdata_folder / item).is_file()
            if (re_result := re.search(r'PORT~(\d{5})', item))
        }
        do_conflict_check = False
        if not self.global_temp.is_dir():
            os.mkdir(self.global_temp)
        elif len(port_files) >= 2:
            do_conflict_check = True

        invalid_port_files = set()
        invalid_ports = set()
        if port is None:
            if not port_files:
                port = self.default_port
                print(f'Using Default Port: {port}')
            else:
                sorted_ports = sorted(port_files, key=lambda p: (abs(p - self.default_port), p))
                next_port = iter(sorted_ports)
                port = self.default_port if self.default_port in port_files else next(next_port)
                print(f'Using Default Port: {port}' if port == self.default_port else f'Using Port: {port}')

        if takeover:
            for _ in range(5):
                try:
                    print('Trying Takeover')
                    establish_self_as_server()
                    return
                except OSError as e:
                    print(f'Takeover Failed: {e}')
                    time.sleep(0.01)
            # If takeover fails, erase client_dict and connect as client
            self.client_dict = {}
            establish_self_as_client()
            return
        while True:
            try:
                establish_self_as_server()
                break
            except OSError as e:
                print(f'IPC Error: {e}')
                if establish_self_as_client():
                    break

    def ipc_client_loop(self, client):
        ack_count = 0
        while True:
            try:
                while True:
                    client.sendall(f'HB:{self.instance_id}\n'.encode('utf-8'))  # Heartbeat
                    data = client.recv(1024).decode('utf-8')
                    if not data:
                        raise OSError('Server disconnected; Sent Empty Message')
                    for msg in data.strip().split('\n'):
                        match msg.split(':'):
                            case ['UPDATE', client_data]:
                                if ack_count:
                                    print('')
                                    ack_count = 0
                                client_list = client_data.split('|')
                                self.client_dict = {k: v for s in client_list for k, v in [s.split('~')]}
                                print('--- New Client List ---')
                                print(self.client_dict)
                            case ['ACK']:
                                ack_count += 1
                                if ack_count > 1000000:
                                    ack_count = 1000001
                                    print(f'\rACK (1000000+)', end='', flush=True)
                                    continue
                                print(f'\rACK ({ack_count})', end='', flush=True)
                            case ['MIGRATE', new_port]:
                                if ack_count:
                                    print('')
                                print(f'Server instructed migration to port: {new_port}')
                                self.ipc(port=int(new_port))
                                return
                            case _:
                                if ack_count:
                                    print('')
                                    ack_count = 0
                                print(msg)

                    time.sleep(1)
            except OSError as e:
                if ack_count:
                    print('')
                print(e)
                print('Current Server Disconnected')
                compare_dict = {k: float(v) for k, v in self.client_dict.items()}
                self.reestablish = True
                if min(self.client_dict, key=compare_dict.get) == self.instance_id:
                    print('Selected self as server')
                    del compare_dict
                    self.client_dict.pop(self.instance_id)
                    self.ipc(takeover=True)
                    return
                del compare_dict
                client.close()
                time.sleep(random.uniform(0.75, 1.25))
                print('Attempting Reconnection as Client')
                self.client_dict.pop(self.instance_id)
                self.ipc()
                return

    def ipc_server_loop(self, server):
        self.global_temp: str
        first_client = True
        server.settimeout(1)
        gui_is_alive = self.root.winfo_exists
        if self.reestablish:
            self.reestablish_start = time.time()
            self.reestablish_ids.clear()

        while self.is_server:
            try:
                client, _ = server.accept()
                client.settimeout(2)
                threading.Thread(target=self.ipc_server_client_loop, args=[client], daemon=True).start()
                if first_client:
                    if not self.running_as_exe:
                        self.root.title(f'C4 Icon Swapper ({self.instance_id})')
                    first_client = False

            except socket.timeout:
                # Reestablish ending logic
                with self.socket_lock:
                    reestablish = self.reestablish
                # Reestablishment period can range between 4 and 5 seconds because of server timeout
                if reestablish and time.time() - self.reestablish_start > 4:
                    print('Reestablishment Period Ended')
                    with self.socket_lock:
                        if self.reestablish_ids - self.client_dict.keys():
                            print('--- Something Went Wrong ---')
                            print('Client found in reestablish_ids but not client_dict')
                            print(f'client_dict: {self.client_dict.keys()}')
                            print(f'reestablish_ids: {self.reestablish_ids}')
                        # Remove clients who are in dict but failed to reestablish
                        delete_items = set()
                        recover_items = set()
                        for cid in self.client_dict.keys() - self.reestablish_ids:
                            self.client_dict.pop(cid)
                            if not (client_path := self.global_temp / cid).is_dir():
                                continue
                            has_driver = (client_path / 'driver').exists()
                            rep_imgs_path = client_path / 'Replacement Icons'
                            has_replacements = rep_imgs_path.is_dir() and any(rep_imgs_path.iterdir())
                            if has_driver or has_replacements:
                                recover_items.add(self.global_temp / cid)
                                continue
                            delete_items.add(client_path)
                        if delete_items:
                            print(f'Deleting Clients: {delete_items}')
                            threading.Thread(target=self.handle_dead_clients, kwargs={'delete': True},
                                             args=[delete_items], daemon=True).start()
                        if recover_items:
                            print(f'Moving Client Folders to Recovery: {recover_items}')
                            threading.Thread(target=self.handle_dead_clients, kwargs={'recover': True},
                                             args=[recover_items], daemon=True).start()
                        del delete_items
                        del recover_items
                        for cid in self.client_dict.copy():
                            if not (self.global_temp / cid).is_dir():
                                self.client_dict.pop(cid)
                        print(self.client_dict if self.client_dict else 'No Clients')
                        self.reestablish_ids.clear()
                        self.reestablish_start = None
                        self.reestablish = False
                    self.server_broadcast_id_update()

                # Ghost server check
                if not gui_is_alive():
                    server.close()
                    raise RuntimeError('👻')

            except Exception as e:
                print(f'Server Loop Error: {e}')

    def ipc_server_client_loop(self, client):
        self.global_temp: str
        client_id = None
        gui_is_alive = self.root.winfo_exists
        socket_lock = self.socket_lock
        grace = True
        while True:
            if not gui_is_alive():
                client.close()
                raise RuntimeError('👻')
            try:
                data = client.recv(1024).decode('utf-8')
                if not data:
                    if grace:
                        grace = False
                        print('Client sent empty message; given grace')
                        continue
                    raise OSError('Client disconnected; sent empty message')
                last_seen_time = time.time()
                grace = True
                for msg in data.strip().split('\n'):
                    match msg.split(':'):
                        case ['RE', cid]:
                            client_id = cid
                            client.settimeout(0.5)
                            print(f'Reestablishing Client: {cid}')
                            with socket_lock:
                                client_dict = self.client_dict.copy()
                            if client_id in client_dict:
                                dict_time = client_dict[client_id]
                                new_client = None
                            else:
                                print(f'Client not in dictionary tried to reconnect: {client_id}')
                                dict_time = last_seen_time
                                new_client = (client_id, client)

                            with socket_lock:
                                if reestablish := self.reestablish:
                                    self.client_dict[client_id] = dict_time
                                    self.last_seen[client_id] = last_seen_time
                                    self.socket_dict[client_id] = client
                                    if not new_client:
                                        self.reestablish_ids.add(client_id)

                            if reestablish:
                                client.sendall(f'OK:{self.instance_id}:{client_id}~{dict_time}\n'.encode('utf-8'))
                                continue
                            # If new client tries to "reestablish" while server not in reestablish mode
                            if new_client:
                                self.server_broadcast_id_update(new_connection=new_client)
                                continue
                            # If existing client tries to reestablish while server not in reestablish mode
                            with self.socket_lock:
                                client_list = '|'.join(f'{k}~{v}' for k, v in self.client_dict.items())
                            client.sendall(f'OK:{self.instance_id}:{client_list}\n'.encode('utf-8'))

                        case ['ID', cid]:  # Typical new client establishment
                            client_id = cid
                            client.settimeout(0.5)
                            with socket_lock:
                                client_dict = self.client_dict.copy()
                                reestablish = self.reestablish
                            if client_id in client_dict and client_id in os.listdir(self.global_temp):
                                print('ID collision', client_id, 'in', client_dict)
                                client.sendall('INSTANCE ID COLLISION\n'.encode('utf-8'))
                                continue

                            with socket_lock:
                                self.client_dict[client_id] = last_seen_time
                                self.last_seen[client_id] = last_seen_time
                                self.socket_dict[client_id] = client
                            self.server_broadcast_id_update(new_connection=(client_id, client))

                        case ['HB', client_id]:  # Heartbeat
                            with socket_lock:
                                self.last_seen[client_id] = last_seen_time
                            client.sendall('ACK\n'.encode('utf-8'))

            except OSError as e:
                if not self.is_server:
                    return
                if client_id and time.time() - self.last_seen[client_id] < 2:
                    continue
                print(e)
                if grace:
                    print('Client given grace')
                    grace = False
                    continue
                if not client_id:
                    print(f'Failed to establish client id: {client}')
                    return
                print(f'Client {client_id} disconnected')
                # If client disconnects but leaves folder behind
                if client_id in os.listdir(self.global_temp):
                    has_driver = 'driver' in os.listdir(client_folder := self.global_temp / client_id)
                    has_replacements = os.listdir(client_folder / 'Replacement Icons')
                    if has_driver or has_replacements:
                        threading.Thread(target=self.handle_dead_clients, kwargs={'recover': True},
                                         args=[{client_folder}], daemon=True).start()
                    else:
                        shutil.rmtree(client_folder)
                        print(f'Deleted {client_id} folder')
                with socket_lock:
                    self.client_dict.pop(client_id)
                    self.socket_dict.pop(client_id)
                    self.last_seen.pop(client_id)
                    self.reestablish_ids.discard(client_id)
                self.server_broadcast_id_update()
                return

    def ipc_server_heartbeat(self, port: int, first_time=True):
        heartbeat_interval = 7.77
        port_file = self.appdata_folder / f'PORT~{port}'
        sleep_time = 1.23 if first_time else heartbeat_interval
        while self.is_server:
            port_file.touch()
            time.sleep(sleep_time)
            if not self.root.winfo_exists():  # Ghost thread check
                raise RuntimeError('👻')
            if first_time:
                first_time = False
                sleep_time = heartbeat_interval

    def ipc_server_conflict_check(self, port: int):
        print('Doing server conflict check in 4.20 seconds...')
        time.sleep(4.20)
        port_files = {
            int(re_result.group(1))
            for item in os.listdir(self.appdata_folder)
            if (self.appdata_folder / item).is_file()
            if (re_result := re.search(r'PORT~(\d{5})', item))
            if int(re_result.group(1)) != port
        }

        if port_files:
            print('Detected possible server conflict')
            # Sort ports by which is closest to default port (smaller port number wins tie)
            sorted_ports = sorted(port_files, key=lambda p: (abs(p - self.default_port), p))
            if (new_port := sorted_ports[0]) != port:
                print(f'Found server conflict')
                with self.socket_lock:
                    if self.socket_dict:
                        print('Instructing clients to migrate')
                        for cid, sock in self.socket_dict.items():
                            try:
                                sock.sendall(f'MIGRATE:{new_port}\n'.encode('utf-8'))
                                sock.shutdown(socket.SHUT_WR)
                            except OSError as e:
                                print(f'Broadcast Error with {cid}: {e}')
                    self.is_server = False
                    self.finished_server_init = True
                time.sleep(1.1)  # Ensure server loop exits
                (self.appdata_folder / f'PORT~{port}').unlink(missing_ok=True)
                print(f'Attempting to connect as client on port: {new_port}')
                self.ipc(port=new_port)
                return
            print('Found server conflict; Selected self as valid server')
            self.finished_server_init = True
            return
        print('No conflict found :)')
        self.finished_server_init = True
        time.sleep(2)
        self.global_temp_cleanup()

    def server_broadcast_id_update(self, new_connection=None, force=False):
        with self.socket_lock:
            if self.reestablish and not force:
                print('Broadcast canceled due to reestablishment mode')
                return
            if not self.client_dict and not new_connection:
                print('Broadcast canceled due to empty dictionary')
                return
        resend = True
        while resend:
            resend = False
            with self.socket_lock:
                if new_connection:
                    current_sockets = [(k, v) for k, v in self.socket_dict.items() if k != new_connection[0]]
                else:
                    current_sockets = list(self.socket_dict.items())
                new_client_list = '|'.join(f'{k}~{v}' for k, v in self.client_dict.items())
            if new_connection:
                print('--- New Client Established ---')
                print(f'Client ID: {new_connection[0]}')
                new_connection[1].sendall(f'OK:{self.instance_id}:{new_client_list}\n'.encode('utf-8'))
            print('--- Broadcast New Client List ---')
            print(new_client_list)
            for cid, sock in current_sockets:
                try:
                    sock.sendall(f'UPDATE:{new_client_list}\n'.encode('utf-8'))
                except OSError as e:
                    print(f'Broadcast Error with {cid}: {e}')
                    with self.socket_lock:
                        self.client_dict.pop(cid)
                        self.socket_dict.pop(cid)
                        if not self.socket_dict:
                            return
                        resend = True

    def handle_dead_clients(self, client_paths, recover=False, delete=False):
        if recover:
            if not self.recovery_folder.is_dir():
                os.mkdir(self.recovery_folder)
            for path in client_paths:
                next_num = get_next_num_str(start=len(os.listdir(self.recovery_folder)), yield_start=False)
                try:
                    shutil.move(path, self.recovery_folder / next(next_num))
                    print(f'Moved to Recovery: {path}')
                except PermissionError:
                    print(f'Failed to Move: {path}')
                except OSError as er:
                    print(f'OS Error with {path}: {er}')
            return
        if delete:
            for path in client_paths:
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                        print(f'Deleted: {path}')
                        continue
                    os.remove(path)
                    print(f'Deleted: {path}')
                except PermissionError:
                    print(f'Failed to Delete: {path}')
                except OSError as er:
                    print(f'OS Error with` {path}: {er}')

    def global_temp_cleanup(self):
        print('Starting global temp folder cleanup')
        delete_items = set()
        recover_items = set()
        for item in os.listdir(self.global_temp):
            client_folder = self.global_temp / item
            if not client_folder.is_dir() or item == self.instance_id or item in self.client_dict:
                continue
            has_driver = 'driver' in os.listdir(client_folder)
            has_replacements = False
            if (rep_imgs_path := client_folder / 'Replacement Icons').is_dir():
                has_replacements = os.listdir(rep_imgs_path)
            if has_driver or has_replacements:
                recover_items.add(client_folder)
                continue
            delete_items.add(client_folder)

        if delete_items:
            print(f'Deleting Clients: {delete_items}')
            threading.Thread(target=self.handle_dead_clients, kwargs={'delete': True},
                             args=[delete_items], daemon=True).start()
        if recover_items:
            print(f'Moving Client Folders to Recovery: {recover_items}')
            threading.Thread(target=self.handle_dead_clients, kwargs={'recover': True},
                             args=[recover_items], daemon=True).start()

        if not delete_items and not recover_items:
            print('Nothing to clean up')


# TODO: Require right click menus to use left click to confirm option
class C4IconSwapper(IPC):
    def __init__(self):
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

        if sys.platform != 'win32':
            print('***************************************************')
            print('This application is designed to only run on Windows')
            print('***************************************************')
            return

        self.running_as_exe = getattr(sys, 'frozen', False) or '__compiled__' in globals()
        self.debug_console = None
        recover_path = None if len(sys.argv) <= 1 else Path(sys.argv[1])
        if self.running_as_exe or recover_path:
            self.toggle_debug_console(initialize=True)

        # Common Directories
        self.cur_dir = Path(os.getcwd())
        self.appdata_folder = Path(os.environ.get('APPDATA')) / 'C4IconSwapper'
        self.recovery_folder = self.appdata_folder / 'Recovery'
        self.global_temp = self.appdata_folder / 'C4IconSwapperTemp'

        # Set Instance ID; Check for existing folders with same ID
        self.instance_id = str(random.randint(111111, 999999))
        self.instance_temp = self.global_temp / self.instance_id
        while self.instance_temp.is_dir():
            self.instance_id = str(random.randint(111111, 999999))
            self.instance_temp = self.global_temp / self.instance_id
        print(f'Set Instance ID: {self.instance_id}')
        # instance_temp folder created after IPC validation

        if not self.appdata_folder.is_dir():
            os.mkdir(self.appdata_folder)

        # Initialize root window
        self.root = TkinterDnD.Tk()
        self.root.report_callback_exception, warnings.showwarning = exception_handler, exception_handler
        self.root.geometry('915x287')
        self.root.resizable(False, False)
        self.root.bind('<KeyRelease>', self.key_release)
        self.root.bind('<Control-s>', self.save_project)
        self.root.bind('<Control-o>', self.load_c4is)
        self.root.bind('<Control-z>', self.undo)
        self.root.bind('<Control-w>', self.end_program)

        self.client_dict = {}
        self.socket_dict = {}
        self.last_seen = {}
        self.is_server = False
        self.finished_server_init = False
        self.reestablish = False
        self.reestablish_start = None
        self.reestablish_ids = set()
        self.socket_lock = threading.Lock()
        self.default_port = 61352
        self.ipc(first_time=True)
        os.mkdir(self.instance_temp)

        # Root window title after IPC since ipc can change instance_id
        show_id_in_title = not self.running_as_exe and not self.is_server
        self.root.title(f'C4 Icon Swapper ({self.instance_id})' if show_id_in_title else 'C4 Icon Swapper')

        # Class variables
        self.driver_xml = None
        self.driver_manufac_var = StringVar()
        self.driver_manufac_new_var = StringVar(value='C4IconSwapper')
        self.driver_creator_var = StringVar()
        self.driver_creator_new_var = StringVar(value='C4IconSwapper')
        self.driver_ver_orig = StringVar()
        self.driver_version_var = StringVar()
        self.driver_version_new_var = StringVar(value='1')
        self.multi_state_driver, self.states_shown, self.ask_to_save = False, False, False
        self.counter, self.easter_counter = 0, 0
        self.easter_call_after_id = None
        self.img_bank_size = 4
        self.connections = [Connection(self) for _ in range(18)]
        self.conn_ids = set()
        self.states = [State('') for _ in range(13)]
        self.states_orig_names = []
        self.device_icon_dir = (www_path := self.instance_temp / 'driver' / 'www') / 'icons' / 'device'
        self.icon_dir = www_path / 'icons'
        self.images_dir = www_path / 'images'
        self.orig_file_dir, self.orig_file_path, self.restore_entry_string = '', '', ''
        self.driver_selected, self.schedule_entry_restore = False, False
        self.undo_history = deque(maxlen=100)

        # Creating blank image for panels
        with Image.open(assets_path / 'blank_img.png') as img:
            self.img_blank = ImageTk.PhotoImage(img.resize((128, 128)))
            self.img_bank_blank = ImageTk.PhotoImage(img.resize((60, 60)))

        # Initialize Panels
        self.c4z_panel = C4zPanel(self)
        self.replacement_panel = ReplacementPanel(self)
        self.export_panel = ExportPanel(self)
        self.driver_info_win = None
        self.states_win = None
        self.connections_win = None

        # Panel Separators
        self.separator0 = Separator(self.root, orient='vertical')
        self.separator0.place(x=305, y=0, height=270)
        self.separator1 = Separator(self.root, orient='vertical')
        self.separator1.place(x=610, y=0, height=270)

        # Version Label
        self.version_label = Label(self.root, text=version)
        self.version_label.place(relx=0.997, rely=1.005, anchor='se')
        self.version_label.bind('<Button-1>', self.easter)

        # Menus
        self.menu = Menu(self.root)

        # File Menu
        self.file = Menu(self.menu, tearoff=0)
        self.file.add_command(label='Open Project', command=self.load_c4is)
        self.file.add_command(label='Save Project', command=self.save_project)
        self.file.add_separator()
        self.file.add_command(label='Open C4z', command=self.c4z_panel.load_c4z)
        self.file.add_command(label='Open Replacement Image', command=self.replacement_panel.load_replacement)
        self.file.add_separator()
        self.file.add_command(label='Load Generic Driver', command=self.c4z_panel.load_gen_driver)
        self.file.add_command(label='Load Multi Driver', command=lambda: self.c4z_panel.load_gen_driver(multi=True))

        # Edit Menu
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

        # Debug menu initialized by easter function (repeatedly clicking the version number)
        self.debug_menu = None

        self.menu.add_cascade(label='File', menu=self.file)
        self.menu.add_cascade(label='Edit', menu=self.edit)

        # Create window icon
        self.root.iconbitmap(default=(assets_path / 'icon.ico'))

        if recover_path:
            self.do_recovery(recover_path)
        elif (self.appdata_folder / 'Recovery').is_dir():
            # noinspection PyTypeChecker
            self.root.after(10, lambda: RecoveryWin(self))

        # Main Loop
        self.root.config(menu=self.menu)
        self.root.protocol('WM_DELETE_WINDOW', self.end_program)
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

    # TODO: Completely overhaul everything related to multistate
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

    def close_connections_win(self):
        if self.connections_win is None:
            return
        self.connections_win.window.destroy()
        self.connections_win = None

    def close_driver_info_win(self):
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
        self.driver_info_win = None

    def close_states_win(self):
        if self.states_win is None:
            return
        self.states_win.refresh()
        self.states_win.window.destroy()
        self.states_win = None

    def save_project(self, *_):
        out_file = filedialog.asksaveasfile(initialfile=f'{self.export_panel.driver_name_var.get()}.c4is',
                                            filetypes=[('C4IconSwapper Project', '*.c4is')])
        if not out_file:
            return
        if not (out_file_path := out_file.name).endswith('.c4is'):
            out_file.close()
            curr_path = out_file_path
            os.rename(curr_path, (out_file_path := f'{out_file_path}.c4is'))
        with open(out_file_path, 'wb') as output:
            # noinspection PyTypeChecker
            pickle.dump(C4IS(self), output)
        self.ask_to_save = False

    # TODO: Currently does not validate project file. Unsure what behavior is for invalid file.
    # TODO: Add backwards compatibility.
    def load_c4is(self, *_):
        if not (file := filedialog.askopenfilename(filetypes=[('C4IconSwapper Project', '*.c4is')])):
            return
        while self.replacement_panel.multi_threading:
            pass
        save_state = None
        if isinstance(file, str):
            with open(file, 'rb') as file:
                save_state = pickle.load(file)
        if not isinstance(save_state, C4IS):
            raise TypeError(f'Expected type: {C4IS.__name__}')

        # C4z Panel (and export button)
        self.c4z_panel.icons = []
        self.c4z_panel.current_icon = 0
        self.c4z_panel.c4_icon_label.configure(image=self.img_blank)
        if (driver_folder := self.instance_temp / 'driver').is_dir():
            shutil.rmtree(driver_folder)
        self.c4z_panel.restore_button['state'] = DISABLED
        if save_state.driver_selected:
            with open(saved_driver_path := self.instance_temp / 'saved_driver.c4z', 'wb') as driver_zip:
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
        if replacement_dir.is_dir():
            shutil.rmtree(replacement_dir)
        os.mkdir(replacement_dir)
        if save_state.replacement:
            rp_img = Image.open(io.BytesIO(save_state.replacement))
            rp_img.save(replacement_dir / 'replacement.png')
            self.replacement_panel.replacement_icon = (Icon(replacement_dir / 'replacement.png', img=rp_img))
            rp_img.close()
            self.replacement_panel.replacement_img_label.configure(
                image=self.replacement_panel.replacement_icon.tk_icon_lg)
            self.replacement_panel.replacement_img_label.image = self.replacement_panel.replacement_icon.tk_icon_lg
        self.replacement_panel.img_bank = []
        for img_bank_label in self.replacement_panel.img_bank_tk_labels:
            img_bank_label.configure(image=self.img_bank_blank)
        next_num = map(str, itertools.count(0))
        for img in save_state.img_bank:
            img_path = replacement_dir / f'img_bank{next(next_num)}.png'
            bank_img = Image.open(io.BytesIO(img))
            bank_img.save(img_path)
            self.replacement_panel.img_bank.append(Icon(img_path, img=bank_img))
            bank_img.close()
        self.replacement_panel.refresh_img_bank()
        self.replacement_panel.replace_button['state'] = save_state.replacement_panel['replace']
        self.replacement_panel.replace_all_button['state'] = save_state.replacement_panel['replace_all']
        self.replacement_panel.prev_icon_button['state'] = save_state.replacement_panel['prev']
        self.replacement_panel.next_icon_button['state'] = save_state.replacement_panel['next']

        self.ask_to_save = False

    def do_recovery(self, recover_path: Path):
        has_driver = False
        if (driver_folder := recover_path / 'driver').is_dir():
            zip_path = f'{driver_folder}.zip'
            # noinspection PyTypeChecker
            shutil.make_archive(driver_folder, 'zip', driver_folder)
            shutil.move(zip_path, recovery_c4z_path := self.instance_temp / 'recovery.c4z')
            self.c4z_panel.load_c4z(file_path=recovery_c4z_path)
            os.remove(recovery_c4z_path)
            has_driver = True
        if (recovery_icons_path := recover_path / 'Replacement Icons').is_dir():
            for item in os.listdir(recovery_icons_path):
                self.replacement_panel.load_replacement(file_path=(recovery_icons_path / item))
        shutil.rmtree(recover_path)
        self.ask_to_save = has_driver

    def undo(self, *_):
        if not self.undo_history:
            self.edit.entryconfig(self.undo_pos, state=DISABLED)
            return
        ask_to_save = self.ask_to_save
        self.ask_to_save = False
        undo_dict = self.undo_history.pop()
        for icon in self.c4z_panel.icons:
            undo_icon = undo_dict['icons'][icon]
            icon.replacement_icon = undo_icon['replacement_icon']
            icon.restore_bak = undo_icon['restore_bak']
        self.c4z_panel.current_icon = undo_dict['current_icon']
        self.c4z_panel.update_icon()

        if not self.undo_history:
            self.edit.entryconfig(self.undo_pos, state=DISABLED)
        self.ask_to_save = ask_to_save

    def update_undo_history(self):
        self.undo_history.append({'icons': {icon: {'replacement_icon': icon.replacement_icon,
                                                   'restore_bak': icon.restore_bak} for icon in self.c4z_panel.icons},
                                  'current_icon': self.c4z_panel.current_icon})
        self.edit.entryconfig(self.undo_pos, state=NORMAL)

    def ask_to_save_dialog(self, result_var, on_exit=True):
        def cancel_dialog():
            result_var.set('cancel')
            self.ask_to_save = ask_to_save
            save_dialog.destroy()

        def do_not_save():
            result_var.set('dont')
            save_dialog.destroy()

        def do_project_save():
            result_var.set('do')
            self.save_project()
            save_dialog.destroy()

        ask_to_save = self.ask_to_save
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

        no_button = Button(save_dialog, text='No', width='10', command=do_not_save)
        no_button.grid(row=2, column=1, sticky='w', padx=5)

        self.ask_to_save = False
        return save_dialog

    def end_program(self, *_):
        if self.ask_to_save:
            save_dialog_result = StringVar()
            self.ask_to_save_dialog(save_dialog_result)
            self.root.wait_variable(save_dialog_result)
            if save_dialog_result.get() not in ('do', 'dont'):
                return
        if (recovery_path := self.appdata_folder / 'Recovery').is_dir() and not os.listdir(recovery_path):
            shutil.rmtree(recovery_path)
            print('Deleted empty Recovery folder')
        if not self.is_server:
            print('')
        if self.is_server and not self.client_dict and self.finished_server_init:
            shutil.rmtree(self.global_temp)
            print('Global Delete')
        else:
            shutil.rmtree(self.instance_temp)
            print('Local Delete')

        self.root.destroy()

    def easter(self, *_, increment=True):
        if self.easter_counter < 0:
            self.easter_counter = 0
            return
        if self.easter_call_after_id:
            self.root.after_cancel(self.easter_call_after_id)
        if self.easter_counter > 10:
            if self.debug_console and not self.debug_menu:
                self.root.title(f'C4 Icon Swapper ({self.instance_id})')
                self.debug_menu = Menu(self.menu, tearoff=0)
                self.debug_menu.add_command(label='Show/Hide Console', command=self.toggle_debug_console)
                self.menu.add_cascade(label='Debug', menu=self.debug_menu)
            self.easter_counter = 0
            text, rely = ('\u262D', 1.027) if self.version_label.cget('text') == '\U0001F339' else ('\U0001F339', 1.02)
            self.version_label.config(text=text, font=(label_font, 30))
            self.version_label.place(relx=1.003, rely=rely)
        else:
            self.easter_counter += 1 if increment else -1
            # noinspection PyTypeChecker
            self.easter_call_after_id = self.root.after(500, lambda: self.easter(increment=False))

    # noinspection PyUnresolvedReferences
    def toggle_debug_console(self, initialize=False):
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        if initialize:
            print('Initializing Debug Console')
            kernel32.AllocConsole()
            self.debug_console = kernel32.GetConsoleWindow()
            sys.stdout = open('CONOUT$', 'w')
            sys.stderr = open('CONOUT$', 'w')

            # Disable X to prevent app crash
            hmenu = user32.GetSystemMenu(self.debug_console, False)
            user32.EnableMenuItem(hmenu, 0xF060, 0x01)  # 0xF060 = X button, 0x01 = Greyed out
            user32.ShowWindow(self.debug_console, 0)  # Immediately hide console
            return
        elif not self.debug_console:
            return

        # Toggle console visibility
        if user32.IsWindowVisible(self.debug_console):
            user32.ShowWindow(self.debug_console, 0)  # Hide
        else:
            user32.ShowWindow(self.debug_console, 5)  # Show


class Icon:
    def __init__(self, path: Path, img=None):
        if not path.is_file():
            raise FileNotFoundError('Failed to find path to image file')
        if path.suffix not in valid_img_types:
            raise TypeError(f'Invalid image type: {path}')
        self.path = path
        self.tk_icon_lg = None
        self.tk_icon_sm = None

        def create_tk_icons(pil_img):
            self.tk_icon_lg = ImageTk.PhotoImage(pil_img.resize((128, 128), Resampling.BICUBIC))
            self.tk_icon_sm = ImageTk.PhotoImage(pil_img.resize((60, 60), Resampling.BICUBIC))
        if img:
            create_tk_icons(img)
        else:
            with Image.open(path) as img:
                create_tk_icons(img)


class C4SubIcon:
    def __init__(self, instance_id, root_path: str, img_path: Path,
                 name: str, size: int | tuple[int, int], bak_path=None):
        self.root = root_path  # Path to directory containing image
        self.path = img_path  # Full path to image file
        rel_parts = (parts := img_path.parts)[parts.index(instance_id) + 1:]
        rel_root_index = next((i for i, part in enumerate(rel_parts) if part in {'icons', 'images'}), -1)
        self.rel_path = Path(*rel_parts[rel_root_index + 1:]) if rel_root_index != -1 else Path(*rel_parts)
        self.full_name = img_path.name
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
                self.bak_tk_icon = ImageTk.PhotoImage(img.resize((128, 128), Resampling.BICUBIC))

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

    def refresh_tk_img(self, bak=False):
        if bak and self.bak:
            icon = max(self.icons, key=lambda sub_icon: sub_icon.size[0] if sub_icon.bak_path else None)
            with Image.open(icon.bak_path) as img:
                self.bak_tk_icon = ImageTk.PhotoImage(img.resize((128, 128), Resampling.BICUBIC))
            return
        with Image.open(self.path) as img:
            self.tk_icon_lg = ImageTk.PhotoImage(img.resize((128, 128), Resampling.BICUBIC))


class SubIconWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main
        self.curr_c4_icon = main.c4z_panel.icons[main.c4z_panel.current_icon]
        self.icons = self.curr_c4_icon.icons
        self.num_of_icons = len(self.icons)
        self.curr_index = 0

        # Initialize window
        self.window = window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', lambda: main.c4z_panel.toggle_sub_icon_win(close=True))
        self.window.title('Sub Icons')
        self.window.geometry('225x255')
        self.window.geometry(f'+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        # Labels
        self.sub_icon_label = Label(window, image=main.img_blank)
        self.sub_icon_label.image = main.img_blank
        self.sub_icon_label.place(relx=0.5, y=10, anchor='n')
        self.sub_icon_label.bind('<Button-3>', self.right_click_menu)

        self.name_label = Label(window, text='icon name', font=(label_font, 10, 'bold'))
        self.name_label.place(relx=0.5, y=180, anchor='n')

        self.size_label = Label(window, text='0x0', font=(label_font, 10))
        self.size_label.place(relx=0.5, y=164, anchor='n')

        self.num_label = Label(window, text='0 of 0', font=(label_font, 10))
        self.num_label.place(relx=0.5, y=146, anchor='n')

        # Buttons
        self.prev_button = Button(window, text='Prev', command=lambda: self.inc_icon(inc=-1), width=5, takefocus=0)
        self.prev_button.place(relx=0.5, x=-4, y=222, anchor='e')
        self.next_button = Button(window, text='Next', command=self.inc_icon, width=5, takefocus=0)
        self.next_button.place(relx=0.5, x=4, y=222, anchor='w')

        self.update_icon()

    def update_icon(self):
        if self.curr_c4_icon is not self.main.c4z_panel.icons[self.main.c4z_panel.current_icon]:
            self.curr_c4_icon = self.main.c4z_panel.icons[self.main.c4z_panel.current_icon]
            self.icons = self.curr_c4_icon.icons
            self.num_of_icons = len(self.icons)
            self.curr_index = self.num_of_icons - 1 if self.curr_index >= self.num_of_icons else self.curr_index
        curr_sub_icon = self.icons[self.curr_index]
        with Image.open(curr_sub_icon.path) as img:
            icon_image = ImageTk.PhotoImage(img.resize((128, 128), Resampling.BICUBIC))
            self.sub_icon_label.configure(image=icon_image)
            self.sub_icon_label.image = icon_image
        self.num_label.config(text=f'{self.curr_index + 1} of {self.num_of_icons}')
        self.size_label.config(text=f'{curr_sub_icon.size[0]}x{curr_sub_icon.size[1]}')
        self.name_label.config(text=curr_sub_icon.full_name)
        if self.num_of_icons <= 1:
            self.prev_button['state'] = DISABLED
            self.next_button['state'] = DISABLED
        else:
            self.prev_button['state'] = NORMAL
            self.next_button['state'] = NORMAL

    def inc_icon(self, inc=1):
        self.curr_index = (self.curr_index + inc) % self.num_of_icons
        self.update_icon()

    def right_click_menu(self, event):
        context_menu = Menu(self.main.root, tearoff=0)
        context_menu.add_command(label='Show icon in folder', command=self.open_icon_folder)
        context_menu.tk_popup(event.x_root, event.y_root)
        context_menu.grab_release()

    def open_icon_folder(self, *_):
        path = os.path.normpath(self.icons[self.curr_index].path)  # normalize just to be safe
        subprocess.Popen(f'explorer /select,"{path}"')


class DriverInfoWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', main.close_driver_info_win)
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
                                              lambda name, index, mode: self.validate_man_and_creator(
                                                  entry=self.driver_man_new_entry))

        driver_creator_entry = Entry(self.window, width=entry_width, textvariable=main.driver_creator_var)
        driver_creator_entry['state'] = DISABLED
        self.driver_creator_new_entry = Entry(self.window, width=entry_width,
                                              textvariable=main.driver_creator_new_var)
        main.driver_creator_new_var.trace_add('write',
                                              lambda name, index, mode: self.validate_man_and_creator(
                                                  string_var=main.driver_creator_new_var,
                                                  entry=self.driver_creator_new_entry))

        driver_ver_entry = Entry(self.window, width=entry_width, textvariable=main.driver_version_var)
        driver_ver_entry['state'] = DISABLED
        self.driver_ver_new_entry = Entry(self.window, width=entry_width,
                                          textvariable=main.driver_version_new_var)
        self.driver_ver_new_entry.bind('<FocusOut>', main.export_panel.update_driver_version)
        main.driver_version_new_var.trace_add('write', self.validate_driver_ver)
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

    def validate_man_and_creator(self, string_var=None, entry=None):
        if not string_var or not entry:
            return
        name_compare = re_valid_chars.sub('', name := string_var.get())
        if str_diff := len(name) - len(name_compare):
            cursor_pos = entry.index(INSERT)
            entry.icursor(cursor_pos - str_diff)
            string_var.set(name_compare)

        self.main.ask_to_save = True

    def validate_driver_ver(self, *_):
        version_compare = re.sub(r'\D', '', ver_str := self.main.driver_version_new_var.get()).lstrip('0')

        if str_diff := len(ver_str) - len(version_compare):
            cursor_pos = self.driver_ver_new_entry.index(INSERT)
            self.driver_ver_new_entry.icursor(cursor_pos - str_diff)
            self.main.driver_version_new_var.set(version_compare)

        self.main.ask_to_save = True


class ConnectionsWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main

        # Initialize window
        self.window = Toplevel(self.main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.main.close_connections_win)
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


# TODO: Figure out how id_groups work and fix implementation
class Connection:
    def __init__(self, main: C4IconSwapper):
        self.main = main
        self.id = 0
        self.original, self.in_id_group, self.enabled = False, False, False
        self.delete = True
        self.prior_txt, self.prior_type = '', ''
        self.tag = copy.deepcopy(connection_tag_generic)
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
        if self.id in self.main.conn_ids:
            self.main.conn_ids.remove(self.id)
        self.main.conn_ids.add(valid_id)
        self.id = valid_id
        self.tag.get_tag('type').set_value(conn_id_type[conn_type][1])
        self.tag.get_tag('id').set_value(str(self.id))


class ConnectionEntry:
    def __init__(self, parent: ConnectionsWin, conn_obj: Connection, x_pos: int, y_pos: int):
        # Initialize Connection UI Object
        self.main = parent.main
        self.window = parent.window
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

        self.del_button = Button(self.window, text='Del', width=3, command=self.toggle_delete, takefocus=0)
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
        self.conn_object.tag.delete = False
        self.name_entry['state'] = NORMAL
        self.type_menu['state'] = NORMAL
        self.add_button.place(x=-420, y=-420, anchor='w')
        self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
        self.name_entry['takefocus'] = 1

    def disable(self):
        self.conn_object.enabled = False
        self.conn_object.tag.delete = True
        self.name_entry['state'] = DISABLED
        self.type_menu['state'] = DISABLED
        self.add_button.place(x=self.x, y=self.y, anchor='w')
        self.x_button.place(x=-420, y=-420, anchor='w')
        self.name_entry['takefocus'] = 0

    def toggle_delete(self):
        if not self.conn_object.original:
            return
        if not self.conn_object.delete:
            self.conn_object.delete = True
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
            return
        self.conn_object.delete = False
        self.conn_object.tag.delete = False
        self.name_entry['state'] = NORMAL
        self.name_entry_var.set(self.conn_object.prior_txt)
        self.conn_object.prior_txt = ''
        self.name_entry['state'] = DISABLED
        self.type.set(self.conn_object.prior_type)
        self.conn_object.prior_type = ''
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

        if self.conn_object.original:
            self.add_button.place(x=-420, y=-420, anchor='w')
            self.del_button.place(x=self.x, y=self.y, anchor='w')
            self.x_button.place(x=-420, y=-420, anchor='w')
        elif self.conn_object.enabled:
            self.add_button.place(x=-420, y=-420, anchor='w')
            self.del_button.place(x=-420, y=-420, anchor='w')
            self.x_button.place(x=self.x + 14, y=self.y, anchor='w')
        else:
            self.add_button['state'] = NORMAL if self.main.driver_selected else DISABLED
            self.add_button.place(x=self.x, y=self.y, anchor='w')
            self.del_button.place(x=-420, y=-420, anchor='w')
            self.x_button.place(x=-420, y=-420, anchor='w')

        if self.conn_object.delete:
            self.del_button['text'] = 'Keep'
            self.del_button['width'] = 4
            self.del_button.place(x=self.x + self.del_button.winfo_x() - 6, y=self.y)


class StatesWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', main.close_states_win)
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


class RecoveryWin:
    def __init__(self, main: C4IconSwapper):
        if not (recovery_path := main.appdata_folder / 'Recovery').is_dir():
            return
        # Delete any non-directories in Recovery folder (Just in case)
        for item in os.listdir(recovery_path):
            if (item_path := recovery_path / item).is_dir():
                continue
            os.remove(item_path)
            print(f'Deleted invalid item from Recovery folder {item}')
        if not (num_of_rec_folders := len(os.listdir(recovery_path))):
            shutil.rmtree(recovery_path)
            if not main.is_server:
                print('')
            print('Deleted empty Recovery folder')
            return
        self.window = window = Toplevel(main.root)
        self.main = main
        self.recovery_path = recovery_path
        window.grab_set()
        window.focus()
        window.transient(main.root)
        window.title('Project Recovery')
        window.geometry('355x287')
        window.geometry(f'+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        window.resizable(False, False)
        window.protocol('WM_DELETE_WINDOW', self.close_dialog)

        self.recoverable_projects = [rec_obj for item in os.listdir(recovery_path)
                                     if (rec_obj := RecoveryObject(recovery_path / item))]

        title_label = Label(window, text='Select Projects to Recover', font=(label_font, 14))
        title_label.place(relx=0.5, y=5, anchor='n')

        canvas = Canvas(window)
        scrollable_frame = Frame(canvas)
        if do_scroll := num_of_rec_folders > 8:
            scrollbar = Scrollbar(window, command=canvas.yview)
            scrollable_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.place(relx=1, x=-5, y=35, relheight=1, height=-50, anchor='ne')
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.place(x=10, y=35, relheight=1, height=-80, anchor='nw')

        self.checkboxes = [Checkbutton(
            scrollable_frame, text=f'{project.name} | '
                                   f'{project.num_images} {"image" if project.num_images == 1 else "images"} | '
                                   f'{project.mtime}', variable=project.recover)
                           for project in self.recoverable_projects]
        if num_of_rec_folders == 1:
            self.recoverable_projects[-1].recover.set(1)
        for check in self.checkboxes:
            check.pack(anchor='w')
            if do_scroll:
                check.bind('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

        recover_button = Button(window, text='Recover', width=10, command=self.do_recovery)
        recover_button.place(relx=0.5, x=-4, rely=1, y=-3, anchor='se')

        delete_button = Button(window, text='Delete' if num_of_rec_folders == 1 else 'Delete All',
                               width=10, command=self.close_dialog)
        delete_button.place(relx=0.5, x=4, rely=1, y=-3, anchor='sw')

    def close_dialog(self):
        def exit_close_dialog():
            close_dialog.destroy()
            self.window.deiconify()
            self.window.focus()

        def do_delete():
            shutil.rmtree(self.recovery_path)
            close_dialog.destroy()
            self.window.destroy()
            self.main.root.deiconify()
            self.main.root.focus()

        close_dialog = Toplevel(self.window)
        close_dialog.title('Are you sure?')
        close_dialog.geometry('239x70')
        close_dialog.geometry(f'+{self.window.winfo_rootx()}+{self.window.winfo_rooty()}')
        close_dialog.protocol('WM_DELETE_WINDOW', exit_close_dialog)
        close_dialog.grab_set()
        close_dialog.focus()
        close_dialog.transient(self.window)
        close_dialog.resizable(False, False)

        label = Label(close_dialog, text='Delete recovered project?' if len(self.recoverable_projects) == 1 else
                        'Delete all recovered projects?', font=(label_font, 10, 'bold'))
        label.place(relx=0.5, y=3, anchor='n')

        yes_button = Button(close_dialog, text='Yes', width='10', command=do_delete)
        yes_button.place(relx=0.5, x=-4, rely=1, y=-8, anchor='se')

        no_button = Button(close_dialog, text='No', width='10', command=exit_close_dialog)
        no_button.place(relx=0.5, x=4, rely=1, y=-8, anchor='sw')

    def warning_dialog(self, dialog_response_var):
        def close_dialog():
            warning_dialog.destroy()
            self.window.deiconify()
            self.window.focus()

        def abort_recovery():
            dialog_response_var.set(1)
            close_dialog()

        def do_recovery():
            dialog_response_var.set(0)
            close_dialog()

        warning_dialog = Toplevel(self.window)
        warning_dialog.title('Warning')
        warning_dialog.geometry('260x85')
        warning_dialog.geometry(f'+{self.window.winfo_rootx()}+{self.window.winfo_rooty()}')
        warning_dialog.protocol('WM_DELETE_WINDOW', abort_recovery)
        warning_dialog.grab_set()
        warning_dialog.focus()
        warning_dialog.transient(self.window)
        warning_dialog.resizable(False, False)

        label = Label(warning_dialog, text='All unselected projects will be deleted.\nAre you sure?',
                      font=(label_font, 10, 'bold'))
        label.place(relx=0.5, y=3, anchor='n')

        yes_button = Button(warning_dialog, text='Yes', width='10', command=do_recovery)
        yes_button.place(relx=0.5, x=-4, rely=1, y=-8, anchor='se')

        no_button = Button(warning_dialog, text='No', width='10', command=abort_recovery)
        no_button.place(relx=0.5, x=4, rely=1, y=-8, anchor='sw')

        return warning_dialog

    def do_recovery(self):
        selected = [rec_obj for rec_obj in self.recoverable_projects if rec_obj.recover.get()]
        if not selected:
            return
        # Warn that unselected projects will be deleted
        if len(selected) != len(self.recoverable_projects):
            abort_recovery = IntVar()
            self.warning_dialog(abort_recovery)
            self.window.wait_variable(abort_recovery)
            if abort_recovery.get():
                return
        own_project = None
        # Delete projects which were not selected
        for recovery_obj in [rec_obj for rec_obj in self.recoverable_projects if rec_obj not in selected]:
            shutil.rmtree(recovery_obj.path)
        # Flag first project to open in self and start new programs to open any remaining projects
        for recovery_obj in selected:
            if not own_project and not self.main.driver_selected:
                own_project = recovery_obj.path
                continue

            if self.main.running_as_exe:
                args = [sys.executable, recovery_obj.path]
            else:
                # Path to exe, path to python script, recovery path variable
                args = [sys.executable, os.path.abspath(sys.argv[0]), recovery_obj.path]

            # Start debug console hidden
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            print('Launching new application to open recovered project')
            subprocess.Popen(args, startupinfo=startupinfo, creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)

        # Open recovery project
        if own_project:
            print('Opening recovered project')
            self.main.do_recovery(own_project)
        self.window.destroy()
        self.main.root.deiconify()
        self.main.root.focus()


class RecoveryObject:
    def __init__(self, instance_path: Path):
        if not instance_path.is_dir():
            return
        self.name = 'No Driver' if 'driver' not in os.listdir(instance_path) else 'MsgNotFound'
        self.path = instance_path
        self.num_images = 0
        self.mtime = datetime.fromtimestamp(os.path.getmtime(instance_path)).strftime("%m/%d %H:%M:%S")
        self.recover = IntVar()

        for item in os.listdir(instance_path):
            if item == 'driver':
                if (xml_path := instance_path / 'driver' / 'driver.xml').is_file():
                    driver_xml = XMLObject(xml_path)
                    if name := driver_xml.get_tag('name').value():
                        self.name = name
            elif item == 'Replacement Icons':
                self.num_images = len(os.listdir(instance_path / 'Replacement Icons'))


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

        self.c4_icon_label = Label(main.root, image=main.img_blank)
        self.c4_icon_label.image = main.img_blank
        self.c4_icon_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.c4_icon_label.bind('<Button-3>', self.right_click_menu)

        self.icon_num_label = Label(main.root, text='0 of 0', font=(label_font, 10))
        self.icon_num_label.place(x=108 + self.x, y=180 + self.y, anchor='n')

        self.icon_name_label = Label(main.root, text='icon name', font=(label_font, 10, 'bold'))
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

        self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')
        self.c4_icon_label.drop_target_register(DND_FILES)
        self.c4_icon_label.dnd_bind('<<Drop>>', self.drop_in_c4z)

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.load_c4z, takefocus=0)
        self.restore_button = Button(main.root, text='Restore\nOriginal Icon', command=self.restore, takefocus=0)
        self.restore_button['state'] = DISABLED

        self.restore_all_button = Button(
            main.root, text='Restore All', command=lambda: self.restore(do_all=True), takefocus=0)
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
        self.show_extra_icons_check.place(x=177 + self.x, y=176 + self.y, anchor='nw')
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
            save_dialog_result = StringVar()
            main.ask_to_save_dialog(save_dialog_result, on_exit=False)
            main.root.wait_variable(save_dialog_result)
            if save_dialog_result.get() not in ('do', 'dont'):
                return

        with Image.open(assets_path / 'loading_img.png') as img:
            icon = ImageTk.PhotoImage(img)
            self.c4_icon_label.configure(image=icon)
            self.c4_icon_label.image = icon
        main.root.update()

        gen_driver_path = assets_path / ('multi_generic.c4z' if multi else 'generic.c4z')

        if (temp_driver_path := main.instance_temp / 'driver').is_dir():
            shutil.rmtree(temp_driver_path)

        shutil.unpack_archive(gen_driver_path, temp_driver_path, 'zip')

        sizes = [70, 90, 300, 512]
        root_size = '1024'
        temp_dir = main.instance_temp / 'temp_unpacking'
        os.mkdir(temp_dir)
        for img_name in os.listdir(main.device_icon_dir):
            with Image.open(main.device_icon_dir / img_name) as img:
                for size in sizes:
                    resized_img = img.resize((size, size), Resampling.LANCZOS)
                    resized_img.save(temp_dir / img_name.replace(root_size, str(size)))
        for img in os.listdir(temp_dir):
            shutil.move(temp_dir / img, main.device_icon_dir / img)

        # noinspection PyTypeChecker
        shutil.make_archive(temp_dir / 'driver', 'zip', temp_driver_path)
        self.load_c4z(f'{temp_dir / "driver"}.zip')
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

    def load_c4z(self, file_path=None):
        if (main := self.main).ask_to_save:
            save_dialog_result = StringVar()
            main.ask_to_save_dialog(save_dialog_result, on_exit=False)
            main.root.wait_variable(save_dialog_result)
            if save_dialog_result.get() not in ('do', 'dont'):
                return

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
        temp_bak = main.instance_temp / 'temp_driver_backup'
        driver_path = main.instance_temp / 'driver'
        icons_bak = None
        if self.icons:
            icons_bak = self.icons
            if driver_path.is_dir():
                shutil.move(driver_path, temp_bak)

        # File select dialog
        if file_path is None:
            file_path = filedialog.askopenfilename(filetypes=[('Control4 Drivers', '*.c4z *.zip')])
            if not file_path:  # If no file selected
                if temp_bak.is_dir():
                    shutil.move(temp_bak, driver_path)
                return

        # Delete existing driver
        main.driver_selected = False
        if (driver_folder := main.instance_temp / 'driver').is_dir():
            shutil.rmtree(driver_folder)

        # Unpack selected driver
        shutil.unpack_archive(file_path, driver_folder, 'zip')

        # Read XML
        curr_xml = main.driver_xml  # store current XML in case of abort
        main.driver_xml = XMLObject(main.instance_temp / 'driver' / 'driver.xml')

        # Get icons
        def get_icons(root_directory):
            if not root_directory:
                return []
            directories = set()
            if isinstance(root_directory, (list, tuple)):
                for item in root_directory:
                    if not item.is_dir():
                        continue
                    directories.update(list_all_sub_directories(item, include_root_dir=True))
                if not directories:
                    return []
            elif isinstance(root_directory, Path):
                if not root_directory.is_dir():
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
                    if not item.is_file() or not os.path.splitext(item.name)[1].lower() in valid_img_types:
                        continue
                    if re.search(r'\.bak[^.]*$', item.name):
                        root_name = re.sub(r'\.bak[^.]*$', '', item.name)
                        bak_files[Path(directory, root_name)] = Path(directory, item.name)
                        continue
                    try:
                        with Image.open(item.path) as img:
                            actual_size = img.size[0]
                    except Image.DecompressionBombError:
                        print(f'Skipping potential decompression bomb: {item.path}')
                        continue
                    except (UnidentifiedImageError, OSError):
                        print(f'Issue with item in get_icons: {item.path}')
                        continue
                    file_stem, file_ext = os.path.splitext(item.name)
                    img_info = re.search(r'^(?:(\d+)_)?(.+?)(?:_(\d+))?$', file_stem).groups()
                    l_label, img_name, r_label = img_info[0], img_info[1], img_info[2]
                    if not img_name or file_stem in ('device_sm', 'device_lg'):
                        img_name = file_stem
                    item_path = Path(directory) / item.name
                    # If XOR left/right size labels exist
                    if bool(l_label) ^ bool(r_label):
                        if (l_label and int(l_label) == actual_size) or int(r_label) == actual_size:
                            icon_groups[img_name].append(C4SubIcon(self.main.instance_id, directory,
                                                                   item_path, img_name, actual_size))
                            all_sub_icons.append(icon_groups[img_name][-1])
                            continue
                    elif l_label and r_label:
                        r_size = int(r_label)
                        if l_label == r_label and r_size == actual_size:
                            both_scheme.append(C4SubIcon(self.main.instance_id, directory,
                                                         item_path, img_name, actual_size))
                            all_sub_icons.append(both_scheme[-1])
                            continue
                        elif r_size == actual_size:
                            img_name = f'{l_label}_{img_name}'
                        elif int(l_label) == actual_size:
                            img_name = f'{img_name}_{r_label}'
                        icon_groups[img_name].append(C4SubIcon(self.main.instance_id, directory, item_path,
                                                               img_name, actual_size))
                        all_sub_icons.append(icon_groups[img_name][-1])
                        continue
                    icon_groups[img_name].append(C4SubIcon(self.main.instance_id, directory, item_path,
                                                           img_name, actual_size))
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
            # TODO: Reevaluate this loop. Does not seem to be working; Icons given wrong display name
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
                if 'controller://' not in (tag_value := tag.value()):
                    print(f'Could not parse Icon tag value in xml: {tag_value}')
                    continue
                group_name = tag.parent.attributes.get('id')
                rel_path = tag_value.split('controller://')[1]
                if 'icons' in rel_path:
                    rel_path = rel_path.split('icons')[1].strip(os.sep)
                elif 'images' in rel_path:
                    rel_path = rel_path.split('images')[1].strip(os.sep)
                icon_groups[(group_name if group_name else tag.parent.name, tag.parent)].add(rel_path)

            seen_groups = {}
            duplicates = set()
            for name_and_tag, group_set in icon_groups.items():
                current_group_set = frozenset(group_set)
                if current_group_set in seen_groups:
                    existing_name_and_tag = seen_groups[current_group_set]
                    if (not existing_name_and_tag[1].attributes.get('id')) and name_and_tag[1].attributes.get('id'):
                        duplicates.add(existing_name_and_tag)
                        seen_groups[current_group_set] = name_and_tag
                    else:
                        duplicates.add(name_and_tag)
                else:
                    seen_groups[current_group_set] = name_and_tag
            for dupe in duplicates:
                del icon_groups[dupe]

            return icon_groups

        # TODO: Change this to be a setting?
        get_all_images = True
        if get_all_images:
            self.icons = get_icons((main.instance_temp / 'driver'))
        else:
            self.icons = get_icons((main.icon_dir, main.images_dir))

        # Update entry fields and restore driver if necessary
        if not self.icons:
            main.driver_xml = curr_xml
            self.file_entry_field['state'] = NORMAL
            if self.file_entry_field.get() not in ('Select .c4z file...', 'Invalid driver selected...'):
                # Restore existing driver data if invalid driver selected
                self.icons = icons_bak
                if temp_bak.is_dir():
                    if driver_folder.is_dir():
                        shutil.rmtree(driver_folder)
                    temp_bak.replace(driver_folder)
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
        self.file_entry_field.insert(0, file_path)
        self.file_entry_field['state'] = 'readonly'

        orig_file_path = Path(file_path)
        main.orig_file_dir = orig_file_path.parent
        if (orig_driver_name := orig_file_path.stem) not in ('generic', 'multi generic'):
            main.export_panel.driver_name_entry.delete(0, 'end')
            main.export_panel.driver_name_entry.insert(0, orig_driver_name)
        if not main.export_panel.driver_name_entry.get():
            main.export_panel.driver_name_entry.insert(0, 'New Driver')

        main.driver_selected = True
        main.undo_history.clear()
        self.current_icon = 0
        self.update_icon()

        # Update show extra icons checkbox
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
            main.conn_ids = set()
            for id_tag in id_tags:
                with contextlib.suppress(ValueError):
                    if int(id_tag.value()) not in main.conn_ids:
                        main.conn_ids.add(int(id_tag.value()))

        # Check Lua file for multi-state
        main.multi_state_driver = False
        main.edit.entryconfig(main.states_pos, state=DISABLED)
        if (lua_path := main.instance_temp / 'driver' / 'driver.lua').is_file():
            with open(lua_path, errors='ignore') as driver_lua_file:
                driver_lua = driver_lua_file.read()
                if main.get_states(driver_lua):
                    main.multi_state_driver = True
                else:
                    main.multi_state_driver = False
        if main.multi_state_driver:
            main.edit.entryconfig(main.states_pos, state=NORMAL)
        elif main.states_win:
            main.close_states_win()

        # Update driver prev/next buttons
        visible_icons = len(self.icons) - (self.extra_icons if not self.show_extra_icons.get() else 0)
        if visible_icons <= 1:
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
        if temp_bak.is_dir():
            shutil.rmtree(temp_bak)

        # Update connections panel
        self.get_connections()
        if main.connections_win:
            main.connections_win.refresh()
        if main.states_win:
            main.states_win.refresh()

        main.ask_to_save = False

    def restore(self, do_all=False):
        self.main.update_undo_history()
        if do_all:
            show_extra = self.show_extra_icons.get()
            for icon in self.icons:
                if not icon.extra or show_extra:
                    icon.set_restore()
        else:
            self.icons[self.current_icon].set_restore()
        self.update_icon()
        self.main.ask_to_save = True

    def unrestore(self, *_, do_all=False):
        self.main.update_undo_history()
        if do_all:
            for icon in self.icons:
                if not icon.replacement_icon and (icon.restore_bak and icon.bak):
                    icon.restore_bak = False
        else:
            self.icons[self.current_icon].restore_bak = False
        self.update_icon()
        self.main.ask_to_save = True

    def inc_icon(self, inc=1, validate=True):
        if not self.main.driver_selected or not inc:
            return

        self.current_icon = (self.current_icon + inc) % len(self.icons)

        if not validate:
            return

        show_extra = self.show_extra_icons.get()
        while self.icons[self.current_icon].extra and not show_extra:
            self.inc_icon(inc=1 if inc > 0 else -1, validate=False)

        if self.sub_icon_win:
            self.sub_icon_win.update_icon()

        self.update_icon()

    def get_connections(self):
        main = self.main
        if not (main.instance_temp / 'driver' / 'driver.xml').is_file() or not main.driver_selected:
            return

        # Reinitialize all connections
        for conn in main.connections:
            conn.__init__(main)

        # Get connections from XML object
        connections = [
            tag_dict | {'connection_tag': tag}
            for tag in main.driver_xml.get_tags('connection')
            if len(tag_dict := tag.get_tags_dict({'class', 'classname', 'connectionname', 'id', 'type'})) == 5
            if tag_dict['classname'].value() in self.valid_connections
        ]

        # Update connection entries up to max number of connections
        for i, tag_dict in enumerate(connections[:len(main.connections)]):
            main.connections[i].name_entry_var.set(tag_dict['connectionname'].value())
            main.connections[i].type.set(tag_dict['classname'].value())
            main.connections[i].id = tag_dict['id'].value()
            main.connections[i].tag = tag_dict['connection_tag']
            main.connections[i].original = True

        # Assign panel connections to XML tags and update UI
        id_groups = []
        # 0: connectionname, 1: classname, 2: id, 3: connection_tag
        # TODO: Rewrite for new data structure
        # for i in range(conn_range):
        #     not_in_group = True
        #     for group in id_groups:
        #         if group[0] is connections[i][3]:
        #             group.append(i)
        #             not_in_group = False
        #     if not_in_group:
        #         id_groups.append([connections[i][3], i])
        #     main.connections[i].name_entry_var.set(connections[i][0])
        #     main.connections[i].type.set(connections[i][1])
        #     main.connections[i].id = connections[i][2]
        #     main.connections[i].tag = connections[i][3]
        #     main.connections[i].original = True

        # Form id groups
        for group in id_groups:
            for conn_i in group[1:]:
                new_group = [conn_j for conn_j in group if conn_j != conn_i]
                main.connections[conn_i].id_group = new_group
        for conn in main.connections:
            conn.update_id()

    def drop_in_c4z(self, event):
        paths = parse_drop_event(event)
        threading.Thread(target=self.main.replacement_panel.load_replacement,
                         kwargs={'file_path': paths}, daemon=True).start()
        if c4z_path := next((path for path in paths if path.suffix == '.c4z' and path.is_file()), None):
            # noinspection PyUnboundLocalVariable
            self.load_c4z(file_path=c4z_path)

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
        self.replacement_icons_dir = main.instance_temp / 'Replacement Icons'
        if not self.replacement_icons_dir.is_dir():
            os.mkdir(self.replacement_icons_dir)

        # Labels
        self.panel_label = Label(main.root, text='Replacement Icons', font=(label_font, 15))

        self.replacement_img_label = Label(main.root, image=main.img_blank)
        self.replacement_img_label.image = main.img_blank

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

    # TODO: Reevaluate threaded usage; Spam UI while large folder of images is being processed
    def load_replacement(self, file_path: Path | str | list | tuple = None, bank_index=None):
        if not file_path:
            if bank_index is None:
                if self.multi_threading:
                    return
                for path in filedialog.askopenfilenames(filetypes=[('Image', ' '.join(valid_img_types))]):
                    self.load_replacement(file_path=path)
                return
        elif isinstance(file_path, str):
            file_path = Path(file_path)
        elif isinstance(file_path, tuple) or isinstance(file_path, list):
            self.multi_threading = True
            for path in file_path:
                if not path.is_dir():
                    self.load_replacement(file_path=path)
                    continue
                for directory in list_all_sub_directories(path, include_root_dir=True):
                    for file in os.listdir(directory):
                        if os.path.splitext(file)[1].lower() in valid_img_types:
                            self.load_replacement(file_path=directory / file)
            self.multi_threading = False
            return
        elif not file_path.is_file() or not os.path.splitext(file_path)[1].lower() in valid_img_types:
            return

        main = self.main

        if file_path:
            new_path = self.replacement_icons_dir / file_path.name
            next_num = map(str, itertools.count(1))
            while new_path.is_file():
                new_path = self.replacement_icons_dir / f'{file_path.stem}{next(next_num)}{file_path.suffix}'

            try:
                Image.MAX_IMAGE_PIXELS = None
                with (Image.open(file_path) as img):
                    Image.MAX_IMAGE_PIXELS = max_image_pixels
                    img.draft('RGB', (1024, 1024))
                    img.thumbnail((1024, 1024), Resampling.LANCZOS)
                    img.save(new_path)
                    new_file_size = os.path.getsize(new_path)
                    # Check if image already in replacement icons directory
                    for file in os.listdir(self.replacement_icons_dir):
                        if os.path.getsize(cmp_path := self.replacement_icons_dir / file) != new_file_size:
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
                            self.replacement_img_label.config(image=main.img_blank)
                            self.replacement_img_label.image = main.img_blank
                            self.replace_button['state'] = DISABLED
                            self.replace_all_button['state'] = DISABLED
                            return
                        elif (self.replacement_icon and
                                self.replacement_icon.path == cmp_path and bank_index is not None):
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
                    new_icon = Icon(new_path, img=img)
            finally:
                Image.MAX_IMAGE_PIXELS = max_image_pixels

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

    # TODO: Bug if existing img in bank is dropped on replacement, it does not swap
    def drop_in_replacement(self, event, paths=None):
        if self.multi_threading:
            return
        if not paths:
            if not (paths := parse_drop_event(event)):
                return
        threading.Thread(target=self.load_replacement, kwargs={'file_path': paths}, daemon=True).start()

    # TODO: Bug if existing bank img is dropped in while bank is not full and existing replacement img,
    #  replacement is moved to bank
    def drop_img_bank(self, bank_num: int, event):
        if self.multi_threading:
            return
        paths = parse_drop_event(event)
        if not paths:
            return
        # If multiple paths, ignore bank_num and load all images as replacement
        if len(paths) > 1:
            threading.Thread(target=self.load_replacement, kwargs={'file_path': paths}, daemon=True).start()
            return
        self.load_replacement(paths[0], bank_index=bank_num)

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

    # TODO: Had unknown bug occur during delete. Unsure of how to reproduce.
    #  I seem to have the last bank img after clicking delete with no replacement selected.
    #  Should add img_bank_select_lockout regardless.
    def delete_image(self, img_index: int):
        if not -1 <= img_index < self.main.img_bank_size:
            return
        if img_index == -1:
            os.remove(self.replacement_icon.path)
            self.replacement_icon = None
            self.replacement_img_label.config(image=self.main.img_blank)
            self.replacement_img_label.image = self.main.img_blank
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
        if ((main := self.main).cur_dir / f'{driver_name}.c4z').is_file():
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
            path = main.cur_dir / f'{driver_name}.c4z'
        bak_files_dict = {}
        bak_folder = main.instance_temp / 'bak_files'
        driver_folder = main.instance_temp / 'driver'

        # Backup and move all .bak files if not included
        if not self.include_backups.get():
            directories = list_all_sub_directories(driver_folder, include_root_dir=True)
            if bak_folder.is_dir():
                shutil.rmtree(bak_folder)
            os.mkdir(bak_folder)
            suffix_num = map(str, itertools.count(0))
            for directory in directories:
                for file in os.listdir(directory):
                    if re.search(r'\.bak[^.]*$', file):
                        current_path = directory / file
                        # I think this is to avoid same name collisions
                        new_path = bak_folder / f'{file}{next(suffix_num)}'
                        bak_files_dict[current_path] = new_path
                        shutil.move(current_path, new_path)

        # Create .c4z file
        zip_path = f'{driver_folder}.zip'
        # noinspection PyTypeChecker
        shutil.make_archive(driver_folder, 'zip', driver_folder)
        shutil.move(zip_path, path)

        # Restore .bak files
        if not self.include_backups.get():
            for file in bak_files_dict:
                shutil.move(bak_files_dict[file], file)
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
            if (lua_path := main.instance_temp / 'driver' / 'driver.lua').is_file():
                for state in main.states:
                    if state.original_name != state.name_var.get():
                        state_name_changes[state.original_name] = state.name_var.get()

                # Read Lua file
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
                # Backup Lua file and write modified version
                os.replace(lua_path, f'{lua_path}.bak')
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

        # Backup driver files
        driver_bak_folder = main.instance_temp / 'driver_bak'
        shutil.copytree(main.instance_temp / 'driver', driver_bak_folder)

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
        xml_path = main.instance_temp / 'driver' / 'driver.xml'
        os.replace(xml_path, f'{xml_path}.bak')
        with open(xml_path, 'w', errors='ignore') as out_file:
            out_file.writelines(driver_xml.get_lines())

        # Make icon changes
        bak_folder = main.instance_temp / 'bak_files'
        if bak_folder.is_dir():
            shutil.rmtree(bak_folder)
        os.mkdir(bak_folder)
        include_bak = self.include_backups.get()
        for icon in main.c4z_panel.icons:
            if icon.replacement_icon:
                with Image.open(icon.replacement_icon.path) as rp_icon:
                    for sub_icon in icon.icons:
                        if include_bak:
                            sub_icon.bak_path = f'{sub_icon.path}.bak'
                            shutil.copy(sub_icon.path, sub_icon.bak_path)
                        out_icon = rp_icon.resize(sub_icon.size, Resampling.LANCZOS)
                        out_icon.save(sub_icon.path)
            elif icon.restore_bak and icon.bak:
                for sub_icon in icon.icons:
                    if not sub_icon.bak_path:
                        continue
                    if include_bak:
                        temp_bak_path = bak_folder / sub_icon.name
                        shutil.move(sub_icon.path, temp_bak_path)
                        shutil.move(sub_icon.bak_path, sub_icon.path)
                        shutil.move(temp_bak_path, sub_icon.bak_path)
                        os.remove(temp_bak_path)
                    else:
                        shutil.move(sub_icon.bak_path, sub_icon.path)
        shutil.rmtree(bak_folder)

        # Save As Dialog and export file
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
                if out_file_path.is_file():
                    os.remove(out_file_path)
                self.export_file(driver_name, path=out_file_path)
        else:
            if (existing_file := main.cur_dir / f'{driver_name}.c4z').is_file():
                os.remove(existing_file)
            self.export_file(driver_name)

        # Restore original files
        main.driver_version_var.set(main.driver_version_new_var.get())
        if self.inc_driver_version.get():
            main.driver_version_new_var.set(str(int(main.driver_version_new_var.get()) + 1))
        driver_xml.restore()
        shutil.rmtree(main.instance_temp / 'driver')
        shutil.move(driver_bak_folder, main.instance_temp / 'driver')

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
        self.version = version
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
            driver_path_noext = main.instance_temp / 'driver'
            # noinspection PyTypeChecker
            shutil.make_archive(driver_path_noext, 'zip', driver_path_noext)
            with open(driver_path := f'{driver_path_noext}.zip', 'rb') as driver_zip:
                self.driver_zip = driver_zip.read()
            os.remove(driver_path)

        # Replacement Panel
        if main.replacement_panel.replacement_icon:
            with open(main.replacement_panel.replacement_icon.path, 'rb') as img:
                self.replacement = img.read()
        else:
            self.replacement = None
        self.img_bank = [open(img.path, 'rb').read() for img in main.replacement_panel.img_bank]

        self.replacement_panel = {'replace': main.replacement_panel.replace_button['state'],
                                  'replace_all': main.replacement_panel.replace_all_button['state'],
                                  'prev': main.replacement_panel.prev_icon_button['state'],
                                  'next': main.replacement_panel.next_icon_button['state']}


def list_all_sub_directories(directory: Path, include_root_dir=False) -> list[Path]:
    subs = sorted([item for item in directory.rglob('*') if item.is_dir()])
    return [directory] + subs if include_root_dir else subs


def parse_drop_event(event) -> list[Path]:
    # Find '{' + any characters until reaching the first '}' OR at least one char of non-whitespace
    return [Path(path[0]) if path[0] else Path(path[1]) for path in re.findall(r'\{(.*?)}|(\S+)', event.data)]


def natural_key(string: str) -> list[str | int]:
    # Splits numbers that are grouped together from all other chars
    return [int(s) if s.isdigit() else s for s in re_natural_sort.split(string)]


if __name__ == '__main__':
    C4IconSwapper()
