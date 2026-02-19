from __future__ import annotations
import contextlib
import ctypes
import filecmp
import io
import itertools
import json
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
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageTk, UnidentifiedImageError
from PIL.Image import Resampling
from tkinter import filedialog
from tkinter import DISABLED, END, INSERT, NORMAL
from tkinter import BooleanVar, IntVar, StringVar
from tkinter import Button, Canvas, Checkbutton, Entry, Frame, Label, Menu, OptionMenu, Text, Toplevel
from tkinter.ttk import Scrollbar, Separator
from tkinterdnd2 import DND_FILES, TkinterDnD

from XMLObject import XMLObject, XMLTag

version = '2.0dev'  # TODO: Change before release; Update README

label_font, light_entry_bg, readonly_bg = 'Arial', '#FFFFFF', '#F0F0F0'
re_valid_chars = re.compile(r'[^\-_ a-zA-Z0-9]')
re_natural_sort = re.compile(r'(\d+)')
valid_img_types = {'.bmp', '.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff', '.webp'}
connection_tag_generic = """
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
"""
video_connections = ('HDMI', 'COMPOSITE', 'VGA', 'COMPONENT', 'DVI')
audio_connections = ('STEREO', 'DIGITAL_OPTICAL')
selectable_connections = tuple(
    f'{connection_type} {suffix}'
    for connection_type in (*video_connections, *audio_connections)
    for suffix in ('IN', 'OUT')
) + ('IR_OUT',)
valid_connections = {*video_connections, *audio_connections, *selectable_connections}
conn_id_type_ref = {video_connections: (2000, 1900, '5'), audio_connections: (4000, 3900, '6')}
conn_id_type = {
    f'{connection_type} {suffix}': (in_id if suffix == 'IN' else out_id, type_val)
    for connections, (in_id, out_id, type_val) in conn_id_type_ref.items()
    for connection_type in connections
    for suffix in ('IN', 'OUT')
}
conn_id_type['IR_OUT'] = (1, '1')

assets_path = Path(__file__).resolve().parent / 'assets'  # For Nuitka or venv
if hasattr(sys, '_MEIPASS'):
    # noinspection PyProtectedMember
    assets_path = Path(sys._MEIPASS) / 'assets'  # For PyInstaller

max_image_pixels = Image.MAX_IMAGE_PIXELS


class PathStringVar(StringVar):
    def get(self, blank_gives_cwd=False):
        return str(Path.cwd()) if not (value := super().get()) and blank_gives_cwd else value


# Inter-Process Communication (For running multiple instances simultaneously); Port range: (49200-65500)
# I'm not very happy with separating the IPC functions into their own class, but I think it makes it more readable
class IPC:
    self: C4IconSwapper
    root: TkinterDnD.Tk
    instance_id: str
    appdata_dir: Path
    global_temp: Path
    recovery_dir: Path
    running_as_exe: bool

    def __init__(self):
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

    def ipc(self, takeover=False, port: int = None, first_time=False):
        # noinspection PyShadowingNames
        def establish_self_as_server():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', port))  # This is where exception is raised
            print(f'(IPC) Is Server: {self.instance_id}')
            self.is_server = True

            # Delete unused port files
            port_files.pop(port, None)
            for _, file_path in port_files.items():
                print(f'(IPC) Trying to delete: {file_path}')
                file_path.unlink(missing_ok=True)
            for file_path in invalid_port_files:
                print(f'(IPC) Trying to delete: {file_path}')
                file_path.unlink(missing_ok=True)

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
                    print(f'(IPC) Is Client: {self.instance_id}')
                    client.settimeout(0.05)
                    client.connect(('127.0.0.1', port))
                    msg = f'ID:{self.instance_id}\n' if not self.reestablish else f'RE:{self.instance_id}\n'
                    client.sendall(msg.encode('utf-8'))

                    response = client.recv(1024).decode('utf-8')
                    if not response:
                        raise OSError('Server Disconnected; Sent Empty Message')
                    print('(IPC) From Server:', repr(response))
                    for msg in response.strip().split('\n'):
                        match msg.split(':'):
                            case ['OK', server_id, client_data]:
                                self.curr_server_id = server_id
                                print(f'(IPC) Became Client of Current Server: {server_id}')
                                if self.reestablish:
                                    self.reestablish = False
                                    print('(IPC) Reestablishment Ended')
                                client_list = client_data.split('|')
                                self.client_dict = {k: v for s in client_list for k, v in [s.split('~')]}
                                print(f'(IPC) {self.client_dict}')
                                threading.Thread(target=self.ipc_client_loop, args=[client], daemon=True).start()
                                return True
                            case ['INSTANCE ID COLLISION']:
                                if not first_time:
                                    # Hopefully this code should never run
                                    print('(IPC) --- Something Went Wrong ---')
                                    print('(IPC) Ignored instruction from server to change instance id')
                                    continue
                                grace = True
                                self.instance_id = str(random.randint(111111, 999999))
                                print('(IPC) From Server: INSTANCE ID COLLISION')
                                print(f'(IPC) New Instance ID: {self.instance_id}')
                                break
                            case _:
                                if grace:
                                    grace = False
                                    print(f'(IPC) Server sent invalid response; given grace: {msg}')
                                    continue
                                raise OSError(f'Server sent invalid response: {msg}')
                except OSError as er:
                    ipc_failures += 1
                    print(f'IPC Error: {er}')
                    print('IPC Initialization Failed')
                    if ipc_failures > 3:
                        if port_files:
                            invalid_port_files.add(port_files.pop(port))
                            invalid_ports.add(port)
                            port = next(next_port, None)
                            if port:
                                print(f'(IPC) Trying New Port: {port}')
                                return False
                        else:
                            invalid_ports.add(port)
                        while port in invalid_ports:
                            port = random.randint(49200, 65500)
                        print(f'(IPC) Trying New Port: {port}')
                        return False

        port_files = {
            int(re_result.group(1)): path
            for path in self.appdata_dir.iterdir()
            if path.is_file()
            if (re_result := re.search(r'PORT~(\d{5})', path.name))
        }
        do_conflict_check = False
        if not self.global_temp.is_dir():
            self.global_temp.mkdir()
        elif len(port_files) >= 2:
            do_conflict_check = True

        invalid_port_files = set()
        invalid_ports = set()
        if port is None:
            if not port_files:
                port = self.default_port
                print(f'(IPC) Using Default Port: {port}')
            else:
                sorted_ports = sorted(port_files, key=lambda p: (abs(p - self.default_port), p))
                next_port = iter(sorted_ports)
                port = self.default_port if self.default_port in port_files else next(next_port)
                print(f'(IPC) Using Default Port: {port}' if port == self.default_port else f'Using Port: {port}')

        if takeover:
            for _ in range(5):
                try:
                    print('(IPC) Trying Takeover')
                    establish_self_as_server()
                    return
                except OSError as e:
                    print(f'(IPC) Takeover Failed: {e}')
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
                                print('(IPC) --- New Client List ---')
                                print(f'(IPC) {self.client_dict}')
                            case ['ACK']:
                                ack_count += 1
                                if ack_count > 1000000:
                                    ack_count = 1000001
                                    print(f'\r(IPC) ACK (1000000+)', end='', flush=True)
                                    continue
                                print(f'\r(IPC) ACK ({ack_count})', end='', flush=True)
                            case ['MIGRATE', new_port]:
                                if ack_count:
                                    print('')
                                print(f'(IPC) Server instructed migration to port: {new_port}')
                                self.ipc(port=int(new_port))
                                return
                            case _:
                                if ack_count:
                                    print('')
                                    ack_count = 0
                                print(f'(IPC) {msg}')

                    time.sleep(1)
            except OSError as e:
                if ack_count:
                    print('')
                print(f'IPC Error: {e}')
                print('(IPC) Current Server Disconnected')
                compare_dict = {k: float(v) for k, v in self.client_dict.items()}
                self.reestablish = True
                if min(self.client_dict, key=compare_dict.get) == self.instance_id:
                    print('(IPC) Selected self as server')
                    del compare_dict
                    self.client_dict.pop(self.instance_id)
                    self.ipc(takeover=True)
                    return
                del compare_dict
                client.close()
                time.sleep(random.uniform(0.75, 1.25))
                print('(IPC) Attempting Reconnection as Client')
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
                    print('(IPC) Reestablishment Period Ended')
                    with self.socket_lock:
                        if self.reestablish_ids - self.client_dict.keys():
                            print('(IPC) --- Something Went Wrong ---')
                            print('(IPC) Client found in reestablish_ids but not client_dict')
                            print(f'(IPC) client_dict: {self.client_dict.keys()}')
                            print(f'(IPC) reestablish_ids: {self.reestablish_ids}')
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
                            print(f'(IPC) Deleting Clients: {delete_items}')
                            threading.Thread(target=self.handle_dead_clients, kwargs={'delete': True},
                                             args=[delete_items], daemon=True).start()
                        if recover_items:
                            print(f'(IPC) Moving Client Folders to Recovery: {recover_items}')
                            threading.Thread(target=self.handle_dead_clients, kwargs={'recover': True},
                                             args=[recover_items], daemon=True).start()
                        del delete_items
                        del recover_items
                        for cid in self.client_dict.copy():
                            if not (self.global_temp / cid).is_dir():
                                self.client_dict.pop(cid)
                        print(f'(IPC) {self.client_dict or "No Clients"}')
                        self.reestablish_ids.clear()
                        self.reestablish_start = None
                        self.reestablish = False
                    self.server_broadcast_id_update()

                # Ghost server check
                if not gui_is_alive():
                    server.close()
                    raise RuntimeError('👻')

            except Exception as e:
                print(f'(IPC) Server Loop Error: {e}')

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
                        print('(IPC) Client sent empty message; given grace')
                        continue
                    raise OSError('Client disconnected; sent empty message')
                last_seen_time = time.time()
                grace = True
                for msg in data.strip().split('\n'):
                    match msg.split(':'):
                        case ['RE', cid]:
                            client_id = cid
                            client.settimeout(0.5)
                            print(f'(IPC) Reestablishing Client: {cid}')
                            with socket_lock:
                                client_dict = self.client_dict.copy()
                            if client_id in client_dict:
                                dict_time = client_dict[client_id]
                                new_client = None
                            else:
                                print(f'(IPC) Client not in dictionary tried to reconnect: {client_id}')
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
                            if client_id in client_dict and (self.global_temp / client_id).exists():
                                print('(IPC) ID collision', client_id, 'in', client_dict)
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
                print(f'IPC Error: {e}')
                if grace:
                    print('(IPC) Client given grace')
                    grace = False
                    continue
                if not client_id:
                    print(f'(IPC) Failed to establish client id: {client}')
                    return
                print(f'(IPC) Client {client_id} disconnected')
                # If client disconnects but leaves folder behind
                if (self.global_temp / client_id).exists():
                    has_driver = ((client_folder := self.global_temp / client_id) / 'driver').exists()
                    has_replacements = any((client_folder / 'Replacement Icons').iterdir())
                    if has_driver or has_replacements:
                        threading.Thread(target=self.handle_dead_clients, kwargs={'recover': True},
                                         args=[{client_folder}], daemon=True).start()
                    else:
                        shutil.rmtree(client_folder)
                        print(f'(IPC) Deleted {client_id} folder')
                with socket_lock:
                    self.client_dict.pop(client_id)
                    self.socket_dict.pop(client_id)
                    self.last_seen.pop(client_id)
                    self.reestablish_ids.discard(client_id)
                self.server_broadcast_id_update()
                return

    def ipc_server_heartbeat(self, port: int, first_time=True):
        heartbeat_interval = 7.77
        port_file = self.appdata_dir / f'PORT~{port}'
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
        print('(IPC) Doing server conflict check in 4.20 seconds...')
        time.sleep(4.20)
        port_files = {
            path_port_int: path
            for path in self.appdata_dir.iterdir()
            if path.is_file()
            if (re_result := re.search(r'PORT~(\d{5})', path.name))
            if (path_port_int := int(re_result.group(1))) != port
        }

        if port_files:
            print('(IPC) Detected possible server conflict')
            # Sort ports by which is closest to default port (smaller port number wins tie)
            sorted_ports = sorted(port_files, key=lambda p: (abs(p - self.default_port), p))
            if (new_port := sorted_ports[0]) != port:
                print('(IPC) Found server conflict')
                with self.socket_lock:
                    if self.socket_dict:
                        print('(IPC) Instructing clients to migrate')
                        for cid, sock in self.socket_dict.items():
                            try:
                                sock.sendall(f'MIGRATE:{new_port}\n'.encode('utf-8'))
                                sock.shutdown(socket.SHUT_WR)
                            except OSError as e:
                                print(f'(IPC) Broadcast Error with {cid}: {e}')
                    self.is_server = False
                    self.finished_server_init = True
                time.sleep(1.1)  # Ensure server loop exits
                (self.appdata_dir / f'PORT~{port}').unlink(missing_ok=True)
                print(f'(IPC) Attempting to connect as client on port: {new_port}')
                self.ipc(port=new_port)
                return
            print('(IPC) Found server conflict; Selected self as valid server')
            self.finished_server_init = True
            return
        print('(IPC) No conflict found :)')
        self.finished_server_init = True
        time.sleep(2)
        self.global_temp_cleanup()

    def server_broadcast_id_update(self, new_connection=None, force=False):
        with self.socket_lock:
            if self.reestablish and not force:
                print('(IPC) Broadcast canceled due to reestablishment mode')
                return
            if not self.client_dict and not new_connection:
                print('(IPC) Broadcast canceled due to empty dictionary')
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
                print('(IPC) --- New Client Established ---')
                print(f'(IPC) Client ID: {new_connection[0]}')
                new_connection[1].sendall(f'OK:{self.instance_id}:{new_client_list}\n'.encode('utf-8'))
            print('(IPC) --- Broadcast New Client List ---')
            print(f'(IPC) {new_client_list}')
            for cid, sock in current_sockets:
                try:
                    sock.sendall(f'UPDATE:{new_client_list}\n'.encode('utf-8'))
                except OSError as e:
                    print(f'(IPC) Broadcast Error with {cid}: {e}')
                    with self.socket_lock:
                        self.client_dict.pop(cid)
                        self.socket_dict.pop(cid)
                        if not self.socket_dict:
                            return
                        resend = True

    def handle_dead_clients(self, client_paths, recover=False, delete=False):
        if recover:
            self.recovery_dir.mkdir(exist_ok=True)
            for path in client_paths:
                next_num = map(str, itertools.count(len(os.listdir(self.recovery_dir)) + 1))
                try:
                    path.replace(self.recovery_dir / next(next_num))
                    print(f'(IPC) Moved to Recovery: {path}')
                except PermissionError:
                    print(f'(IPC) Failed to Move: {path}')
                except OSError as er:
                    print(f'(IPC) OS Error with {path}: {er}')
            return
        if delete:
            for path in client_paths:
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                        print(f'(IPC) Deleted: {path}')
                        continue
                    path.unlink()
                    print(f'(IPC) Deleted: {path}')
                except PermissionError:
                    print(f'(IPC) Failed to Delete: {path}')
                except OSError as er:
                    print(f'(IPC) OS Error with {path}: {er}')

    def global_temp_cleanup(self):
        print('(IPC) Starting global temp folder cleanup')
        delete_items = set()
        recover_items = set()
        for client_folder in self.global_temp.iterdir():
            if (not client_folder.is_dir() or client_folder.name == self.instance_id or
                    client_folder.name in self.client_dict):
                continue
            has_driver = (client_folder / 'driver').exists()
            has_replacements = False
            if (rep_imgs_path := client_folder / 'Replacement Icons').is_dir():
                has_replacements = any(rep_imgs_path.iterdir())
            if has_driver or has_replacements:
                recover_items.add(client_folder)
                continue
            delete_items.add(client_folder)

        if delete_items:
            print(f'(IPC) Deleting Clients: {delete_items}')
            threading.Thread(target=self.handle_dead_clients, kwargs={'delete': True},
                             args=[delete_items], daemon=True).start()
        if recover_items:
            print(f'(IPC) Moving Client Folders to Recovery: {recover_items}')
            threading.Thread(target=self.handle_dead_clients, kwargs={'recover': True},
                             args=[recover_items], daemon=True).start()

        if not delete_items and not recover_items:
            print('(IPC) Nothing to clean up')


# TODO: Add ability to rename icons which are found in XML eg ON/OFF
# TODO: Create savestate json for more inclusive undo history and robust app crash recovery
# TODO: Reevaluate when ask_to_save is set to True
class C4IconSwapper(IPC):
    def __init__(self):
        if sys.platform != 'win32':
            raise OSError('This application only supports Windows')

        self.root = TkinterDnD.Tk()

        # Default App settings
        self.def_get_all_driver_imgs = BooleanVar()
        self.def_get_all_connections = BooleanVar()
        self.def_use_original_xml = BooleanVar()
        self.def_merge_on_load = IntVar(value=-1)  # Default: Ask each time
        self.def_include_backup_files = BooleanVar(value=True)
        self.def_inc_driver_version = BooleanVar(value=True)
        self.def_driver_manufacturer = StringVar(value='C4IconSwapper')
        self.def_driver_creator = StringVar(value='C4IconSwapper')
        self.def_quick_export_dir = PathStringVar()

        self.setting_names = {}
        self.setting_defaults = {}
        ignore_vars = {id(self.root), id(self.setting_names), id(self.setting_defaults)}
        for setting_name, var in self.__dict__.items():
            if (var_id := id(var)) in ignore_vars:
                continue
            self.setting_names[var_id] = setting_name
            self.setting_defaults[setting_name] = var.get()

        # Common Directories
        self.appdata_dir = Path(os.environ['APPDATA']) / 'C4IconSwapper'
        self.recovery_dir = self.appdata_dir / 'Recovery'
        self.global_temp = self.appdata_dir / 'C4IconSwapperTemp'
        self.settings_file = self.appdata_dir / 'settings.json'

        self.appdata_dir.mkdir(exist_ok=True)

        # Read saved user settings from file
        if self.settings_file.exists():
            try:
                if settings_json := json.loads(self.settings_file.read_text()):
                    print('Found user settings in file')
                    invalid_settings = set()
                    missing_settings = self.settings.keys() - settings_json.keys()
                    for setting_name, val in settings_json.items():
                        if setting_name not in self.settings:
                            invalid_settings.add(setting_name)
                            continue
                        if val == self.settings[setting_name]:
                            continue
                        getattr(self, setting_name).set(val)
                    if invalid_settings or missing_settings:
                        self.settings_file.write_text(json.dumps(self.settings, indent='\t'))
                        print('Discrepancy between settings file and default settings')
                        if invalid_settings:
                            print(f'Invalid settings in file: {invalid_settings}')
                        if missing_settings:
                            print(f'Settings missing from file: {missing_settings}')
                else:
                    print('Empty settings file; Reverting to Defaults')
                    self.settings_file.write_text(json.dumps(self.settings, indent='\t'))
            except json.JSONDecodeError:
                print('Problem decoding settings file; Reverting to Defaults')
                self.settings_file.write_text(json.dumps(self.settings, indent='\t'))
        else:
            self.settings_file.write_text(json.dumps(self.settings, indent='\t'))
        settings_str = ',\n\t'.join([f'{setting}: {val}' for setting, val in self.settings.items()])
        print(f'Using settings: {{\n\t{settings_str}\n}}')

        # Exception Handler Variables
        self.warnings = deque()
        self.exceptions = deque()
        self.handler_recall_id = None
        self.alert_warnings = False

        self.running_as_exe = getattr(sys, 'frozen', False) or '__compiled__' in globals()
        self.debug_console = None
        recover_path = None if len(sys.argv) <= 1 else Path(sys.argv[1])
        if self.running_as_exe or recover_path:
            self.toggle_debug_console(initialize=True)

        # Set Instance ID; Check for existing folders with same ID
        self.instance_id = str(random.randint(111111, 999999))
        while (self.global_temp / self.instance_id).is_dir():
            self.instance_id = str(random.randint(111111, 999999))
        print(f'Set Instance ID: {self.instance_id}')

        # Initialize Inter-Process Communication
        super().__init__()
        self.ipc(first_time=True)

        # Instance Directories
        self.instance_temp = self.global_temp / self.instance_id
        self.instance_temp.mkdir()
        self.replacement_icons_dir = self.instance_temp / 'Replacement Icons'
        self.replacement_icons_dir.mkdir(exist_ok=True)

        # Root window title after IPC since instance_id can change during IPC initialization
        show_id_in_title = not self.running_as_exe and not self.is_server
        self.root.title(f'C4 Icon Swapper ({self.instance_id})' if show_id_in_title else 'C4 Icon Swapper')

        # Class variables
        self.driver_xml = None
        self.driver_manufac_var = StringVar()
        self.driver_manufac_new_var = StringVar(value=self.def_driver_manufacturer.get())
        self.driver_creator_var = StringVar()
        self.driver_creator_new_var = StringVar(value=self.def_driver_creator.get())
        self.driver_ver_orig = StringVar()
        self.driver_version_var = StringVar()
        self.driver_version_new_var = StringVar(value='1')
        self.multi_state_driver = False
        self.ask_to_save = False
        self.counter, self.easter_counter = 0, 0
        self.easter_call_after_id = None
        self.img_bank_size = 4
        self.taken_conn_ids = {}
        self.connections = [Connection(self)]
        self.states_orig_names = []
        self.states = [State('') for _ in range(13)]
        self.driver_selected = False
        self.undo_history = deque(maxlen=100)
        self.thread_lock = threading.Lock()
        self.pending_load_save = False  # TODO: Change to threading.Event()

        # Creating blank image for panels
        with Image.open(assets_path / 'blank_img.png') as img:
            self.img_blank = ImageTk.PhotoImage(img.resize((128, 128)))
            self.img_bank_blank = ImageTk.PhotoImage(img.resize((60, 60)))

        # Initialize Panels
        self.c4z_panel = C4zPanel(self)
        self.replacement_panel = ReplacementPanel(self)
        self.export_panel = ExportPanel(self)

        # Popup window variables
        self.driver_info_win, self.states_win, self.connections_win, self.settings_win = None, None, None, None

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
        self.file.add_command(label='Open Project', command=self.load_project)
        self.file.add_command(label='Save Project', command=self.save_project)
        self.file.add_separator()
        self.file.add_command(label='Open C4z', command=self.c4z_panel.load_c4z)
        self.file.add_command(label='Open Replacement Image', command=self.replacement_panel.process_image)
        self.file.add_separator()
        self.file.add_command(label='Load Generic Driver', command=self.c4z_panel.load_gen_driver)
        self.file.add_command(label='Load Multi Driver', command=lambda: self.c4z_panel.load_gen_driver(multi=True))
        self.file.add_separator()
        self.file.add_command(label='Settings', command=lambda: self.open_edit_win(self.settings_win, 'settings'))

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

        # Load recovered project or prompt user how to handle recovered projects
        if recover_path:
            self.do_recovery(recover_path)
        elif self.recovery_dir.is_dir():
            self.root.after(7, RecoveryWin, self)
        # Initialize root window
        self.root.report_callback_exception, warnings.showwarning = self.exception_handler, self.exception_handler
        self.root.geometry('915x287')
        self.root.resizable(False, False)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.bind('<Control-s>', self.save_project)
        self.root.bind('<Control-o>', self.load_project)
        self.root.bind('<Control-z>', self.undo)
        self.root.bind('<Control-w>', self.end_program)
        self.root.config(menu=self.menu)
        self.root.protocol('WM_DELETE_WINDOW', self.end_program)
        self.root.focus_force()
        self.root.mainloop()

    @property
    def settings(self):
        return {
            setting_name: (
                (None if (val := var.get()) < 0 else bool(val))
                if type(var := getattr(self, setting_name)) is IntVar
                else var.get()
            )
            for setting_name in self.setting_names.values()
        }

    def exception_window(self, *args, message_txt=None):
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
        max_rel_w = 0.75
        max_rel_h = 0.75
        w = int(screen_width * max_rel_w) if root.winfo_width() > screen_width * max_rel_w else root.winfo_width()
        h = int(screen_height * max_rel_h) if root.winfo_height() > screen_height * max_rel_h else root.winfo_height()
        root.geometry(f'{w}x{h}')

        text_widget.config(state='disabled')
        root.resizable(False, False)
        root.focus()
        return

    def exception_handler(self, *args):
        if args:
            if len(args) >= 4:
                exc_msg, exc_type, file, line = args[:4]
                if issubclass(exc_type, Warning):
                    self.warnings.append(f'{exc_type.__name__}\nMessage: {exc_msg}\n{file}, Line: {line}')
                else:
                    self.exceptions.append(''.join(traceback.format_exception(*args[:3])))
            else:
                self.exceptions.append('\n'.join(traceback.format_exception(*args)))
            if self.handler_recall_id:
                self.root.after_cancel(self.handler_recall_id)
                self.handler_recall_id = None
            self.handler_recall_id = self.root.after(50, self.exception_handler)  # type: ignore
            return
        if self.warnings and not self.alert_warnings:
            print(f'\n', '\n\n'.join(self.warnings), '\n', sep='')
            self.warnings.clear()
        if not self.warnings and not self.exceptions:
            return
        if len(self.warnings) + len(self.exceptions) == 1:
            self.exception_window(message_txt=(self.warnings or self.exceptions).pop())
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
        self.exception_window(message_txt=f'{header}\n\n{msg_txt}')

    def on_key_release(self, event):
        match event.keysym:
            case 'Right':
                self.c4z_panel.inc_icon()
            case 'Left':
                self.c4z_panel.inc_icon(inc=-1)
            case 'Up':
                self.replacement_panel.inc_img_bank()
            case 'Down':
                self.replacement_panel.inc_img_bank(inc=0)

    def blink_driver_name_entry(self, *_):
        if not self.counter:
            return
        self.counter -= 1
        if self.export_panel.driver_name_entry['background'] != light_entry_bg:
            self.export_panel.driver_name_entry['background'] = light_entry_bg
        else:
            self.export_panel.driver_name_entry['background'] = 'pink'
        self.root.after(150, self.blink_driver_name_entry)  # type: ignore

    def validate_man_and_creator(self, string_var: StringVar, entry: Entry):
        name_compare = re_valid_chars.sub('', name := string_var.get())
        if str_diff := len(name) - len(name_compare):
            cursor_pos = entry.index(INSERT)
            entry.icursor(cursor_pos - str_diff)
            string_var.set(name_compare)
            return
        self.ask_to_save = True

    def validate_driver_ver(self, *_):
        version_compare = re.sub(r'\D', '', ver_str := self.driver_version_new_var.get()).lstrip('0')
        if str_diff := len(ver_str) - len(version_compare):
            cursor_pos = self.driver_info_win.driver_ver_new_entry.index(INSERT)
            self.driver_info_win.driver_ver_new_entry.icursor(cursor_pos - str_diff)
            self.driver_version_new_var.set(version_compare)
            return
        self.ask_to_save = True

    # TODO: schedule for update after pending_load_save
    def toggle_use_original_xml(self, *_):
        if self.pending_load_save:
            print('TODO: schedule for update after pending_load_save')
            return
        state = DISABLED if self.export_panel.use_orig_xml.get() else NORMAL
        self.export_panel.inc_driver_check['state'] = state
        if win := self.driver_info_win:
            win.update_entries()
        if win := self.connections_win:
            win.refresh()

    def update_driver_version(self, *_):
        if not self.export_panel.inc_driver_version.get():
            curr_ver = self.driver_version_var.get()
            alt_ver = self.driver_version_new_var.get() or '1'
            self.driver_version_new_var.set(curr_ver or alt_ver)
            return
        try:
            curr_ver = int(self.driver_version_var.get())
            new_ver = int(self.driver_version_new_var.get())
        except ValueError:
            return
        if curr_ver >= new_ver:
            self.ask_to_save = True
            self.driver_version_new_var.set(str(curr_ver + 1))

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

    # TODO: add waits for opening conn and states windows during pending_load_save
    def open_edit_win(self, main_win_var, win_type: str):
        if main_win_var:
            main_win_var.window.deiconify()
            main_win_var.window.focus()
            return
        match win_type:
            case 'conn':
                self.connections_win = ConnectionsWin(self)
            case 'driver':
                self.driver_info_win = DriverInfoWin(self)
            case 'states':
                self.states_win = StatesWin(self)
            case 'settings':
                self.settings_win = SettingsWin(self)

    def save_project(self, *_, out_file_str='', scheduled=False):
        if scheduled:
            self.replacement_panel.threading_event.wait()
        elif self.pending_load_save:
            return

        if not out_file_str:
            out_file_str = filedialog.asksaveasfilename(initialfile=f'{self.export_panel.driver_name_var.get()}.c4is',
                                                        filetypes=[('C4IconSwapper Project', '*.c4is'),
                                                                   ('All Files', '*.*')],
                                                        defaultextension='.c4is')
            if not out_file_str:
                return

        if not self.replacement_panel.threading_event.is_set():
            with self.thread_lock:
                self.pending_load_save = True
            threading.Thread(target=self.save_project,
                             kwargs={'out_file_str': out_file_str, 'scheduled': True}, daemon=True).start()
            return

        with open(out_file_str, 'wb') as output:
            pickle.dump(C4IS(self), output)  # type: ignore
        self.ask_to_save = False
        self.pending_load_save = False

    # NOTE: Merging projects does not prevent duplicate replacement images
    def load_project(self, *_, path_str='', scheduled=False, merge_project=None):
        if scheduled:
            self.replacement_panel.threading_event.wait()
        elif self.pending_load_save:
            return

        if not path_str:
            path_str = filedialog.askopenfilename(filetypes=[('C4IconSwapper Project', '*.c4is'), ('All Files', '*.*')])
            if not path_str:
                return

        existing_driver = self.driver_selected
        curr_label_img = self.c4z_panel.c4_icon_label.image
        with Image.open(assets_path / 'loading_img.png') as img:
            icon = ImageTk.PhotoImage(img)
            self.c4z_panel.c4_icon_label.configure(image=icon)
            self.c4z_panel.c4_icon_label.image = icon
            self.root.update_idletasks()

        def restore_label_img(update_idletasks=True):
            self.c4z_panel.c4_icon_label.configure(image=curr_label_img)
            self.c4z_panel.c4_icon_label.image = curr_label_img
            if update_idletasks:
                self.root.update_idletasks()

        def abort(reason=None):
            restore_label_img()
            abort_dialog = Toplevel(self.root)
            abort_dialog.title('Project Load Aborted')
            abort_dialog.geometry(f'255x65+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}')
            abort_dialog.grab_set()
            abort_dialog.focus()
            abort_dialog.transient(self.root)
            abort_dialog.resizable(False, False)
            if reason is None:
                reason = 'Project load aborted because of an issue'
            confirm_label = Label(abort_dialog, text=reason, font=(label_font, 12), wraplength=225)
            confirm_label.pack(fill='both', expand=True)

        # Create C4IS object from file
        try:
            with open(path_str, 'rb') as project_file:
                c4is = pickle.load(project_file)
        except (pickle.UnpicklingError, EOFError, AttributeError):
            abort(reason='File corrupted or invalid format')
            return
        if not isinstance(c4is, C4IS):
            abort(reason='File contains incompatible data structure')
            return
        saved_has_imgs = c4is.replacement or c4is.img_bank
        if not c4is.driver_selected and not saved_has_imgs:
            abort(reason='Cannot load an empty project')
            return
        if c4is.version <= 1:
            abort(reason='Projects created by versions older than 2.0 are not supported')
            return

        if merge_project is None:
            merge_project = None if (setting_val := self.def_merge_on_load.get()) < 0 else bool(setting_val)
        has_images = self.replacement_panel.replacement_icon or self.replacement_panel.img_bank
        if merge_project is None and (has_images or (self.driver_selected and not c4is.driver_selected)):
            merge_dialog_result = StringVar()
            self.ask_to_merge_dialog(merge_dialog_result)
            self.root.wait_variable(merge_dialog_result)
            match merge_dialog_result.get():
                case 'do':
                    merge_project = True
                case 'dont':
                    merge_project = False
                case _:
                    restore_label_img()
                    return

        # If images are currently being processed by replacement panel, start new thread waiting for it to finish
        if not self.replacement_panel.threading_event.is_set():
            self.pending_load_save = True
            threading.Thread(target=self.load_project,
                             kwargs={'path_str': path_str, 'scheduled': True, 'merge_project': merge_project},
                             daemon=True).start()
            return

        # If saved project has a driver, or it is overwriting current project's driver
        if c4is.driver_selected or not merge_project:
            self.c4z_panel.icons = []
            self.c4z_panel.current_icon = 0
            self.c4z_panel.c4_icon_label.configure(image=self.img_blank)
            shutil.rmtree(self.instance_temp / 'driver', ignore_errors=True)
            if c4is.driver_selected:
                self.c4z_panel.restore_button['state'] = DISABLED
                with open(saved_driver_path := self.instance_temp / 'saved_driver.c4z', 'wb') as driver_zip:
                    driver_zip.write(c4is.driver_zip)
                self.c4z_panel.load_c4z(saved_driver_path, c4is=c4is, bypass_ask_save=True, new_thread=False,
                                        force=scheduled)
                saved_driver_path.unlink()
            elif not merge_project:
                self.export_panel.export_button['state'] = DISABLED
                self.export_panel.export_as_button['state'] = DISABLED
                self.c4z_panel.icon_name_label.config(text='icon name')
                self.c4z_panel.icon_num_label.config(text='0 of 0')
            self.driver_selected = c4is.driver_selected
            self.driver_manufac_var.set(c4is.driver_manufac_var)
            self.driver_manufac_new_var.set(c4is.driver_manufac_new_var)
            self.driver_creator_var.set(c4is.driver_creator_var)
            self.driver_creator_new_var.set(c4is.driver_creator_new_var)
            self.driver_ver_orig.set(c4is.driver_ver_orig)
            self.driver_version_var.set(c4is.driver_version_var)
            self.driver_version_new_var.set(c4is.driver_version_new_var)

            # Multi State
            self.states_orig_names = c4is.states_orig_names
            self.multi_state_driver = c4is.multi_state_driver
            if self.multi_state_driver:
                self.edit.entryconfig(self.states_pos, state=NORMAL)
            else:
                self.edit.entryconfig(self.states_pos, state=DISABLED)
                if self.states_win:
                    self.states_win.close()
            for i, state in enumerate(c4is.states):
                self.states[i].original_name = state['original_name']
                self.states[i].name_var.set(state['name_var'])

            # Connection Panel
            for conn in self.connections:
                conn.__init__(self)
            self.taken_conn_ids.clear()
            for i, conn in enumerate(c4is.connections):
                self.connections[i].id = conn_id = conn['id']
                if conn_id >= 0:
                    self.taken_conn_ids[conn_id] = self.connections[i]
                self.connections[i].original = conn['original']
                self.connections[i].delete = conn['delete']
                self.connections[i].tag = conn['tag']
                self.connections[i].type_var.set(conn['type'])
                self.connections[i].name_entry_var.set(conn['name'])
                self.connections[i].enabled = conn['state']
            if self.connections_win:
                self.connections_win.refresh(hard=True)
            if self.states_win:
                self.states_win.refresh()

            # Export Panel
            self.export_panel.driver_name_var.set(c4is.driver_name_var)
            self.export_panel.inc_driver_version.set(c4is.inc_driver_version)
            self.export_panel.include_backups.set(c4is.include_backups)

        # noinspection PyShadowingNames
        def save_img_bank():
            next_num = itertools.count(len(self.replacement_panel.img_bank) + 1)
            for img in c4is.img_bank:
                while (img_path := self.replacement_icons_dir / f'img_bank{next(next_num)}.png').exists():
                    pass
                with Image.open(io.BytesIO(img)) as bank_img:
                    bank_img.save(img_path)
                    self.replacement_panel.img_bank.append(Icon(img_path, img=bank_img))

        def save_replacement_img():
            next_num = itertools.chain([''], itertools.count(0))
            while (rp_path := self.replacement_icons_dir / f'replacement{next(next_num)}.png').exists():
                pass
            with Image.open(io.BytesIO(c4is.replacement)) as rp_img:
                rp_img.save(rp_path)
                self.replacement_panel.replacement_icon = (Icon(rp_path, img=rp_img))

        # Replacement Panel
        if not merge_project:
            self.replacement_panel.img_bank_lockout_dict = {}
            self.replacement_panel.img_bank = []
            replacement_dir = self.replacement_icons_dir
            shutil.rmtree(replacement_dir, ignore_errors=True)
            replacement_dir.mkdir()
            for img_bank_label in self.replacement_panel.img_bank_tk_labels:
                img_bank_label.configure(image=self.img_bank_blank)
        elif existing_driver and not c4is.driver_selected:
            restore_label_img(update_idletasks=True)
        if c4is.replacement:
            if merge_project and self.replacement_panel.replacement_icon:
                c4is.img_bank.append(c4is.replacement)
            else:
                save_replacement_img()
                rp_tk_img = self.replacement_panel.replacement_icon.tk_icon_lg
                self.replacement_panel.replacement_img_label.configure(image=rp_tk_img)
                self.replacement_panel.replacement_img_label.image = rp_tk_img
                self.replacement_panel.file_entry_str.set(self.replacement_panel.replacement_icon.path)
                self.replacement_panel.file_entry_field['state'] = 'readonly'
        elif not merge_project:
            self.replacement_panel.replacement_icon = None
            self.replacement_panel.replacement_img_label.config(image=self.img_blank)
            self.replacement_panel.replacement_img_label.image = self.img_blank
        save_img_bank()
        self.replacement_panel.refresh_img_bank()
        self.replacement_panel.update_buttons()

        if not c4is.driver_selected:
            restore_label_img()

        self.ask_to_save = False if not merge_project else True
        self.pending_load_save = False

    def do_recovery(self, recover_path: Path):
        if (driver_folder := recover_path / 'driver').is_dir():
            shutil.make_archive(str(driver_folder), 'zip', driver_folder)
            zip_path = driver_folder.with_suffix('.zip')
            zip_path.replace(recovery_c4z_path := self.instance_temp / 'recovery.c4z')
            self.c4z_panel.load_c4z(file_path=recovery_c4z_path, bypass_ask_save=True, new_thread=False)
            recovery_c4z_path.unlink()
        if (recovery_icons_path := recover_path / 'Replacement Icons').is_dir():
            for path in recovery_icons_path.iterdir():
                self.replacement_panel.process_image(file_path=path, new_thread=False)
                self.root.update()
        shutil.rmtree(recover_path)
        self.ask_to_save = True

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
        def cancel():
            result_var.set('cancel')
            self.ask_to_save = curr_ask_to_save
            save_dialog.destroy()

        def do_not_save():
            result_var.set('dont')
            save_dialog.destroy()

        def do_save():
            result_var.set('do')
            self.save_project()
            save_dialog.destroy()

        curr_ask_to_save = self.ask_to_save
        save_dialog = Toplevel(self.root)
        save_dialog.title('Save current project?')
        x_offset = self.root.winfo_rootx() + self.root.winfo_width() - 250 if on_exit else self.root.winfo_rootx()
        save_dialog.geometry(f'239x70+{x_offset}+{self.root.winfo_rooty()}')
        save_dialog.protocol('WM_DELETE_WINDOW', cancel)
        save_dialog.grab_set()
        save_dialog.focus()
        save_dialog.transient(self.root)
        save_dialog.resizable(False, False)

        confirm_label = Label(save_dialog, text='Would you like to save the current project?')
        confirm_label.place(relx=0.5, rely=0, y=5, anchor='n')

        yes_button = Button(save_dialog, text='Yes', width='10', command=do_save)
        yes_button.place(relx=0.5, rely=1, x=-5, y=-10, anchor='se')

        no_button = Button(save_dialog, text='No', width='10', command=do_not_save)
        no_button.place(relx=0.5, rely=1, x=5, y=-10, anchor='sw')

        self.ask_to_save = False

    def ask_to_merge_dialog(self, result_var):
        def cancel():
            result_var.set('cancel')
            merge_dialog.destroy()

        def do_not_merge():
            result_var.set('dont')
            if dont_ask_again.get():
                update_settings(False)
            merge_dialog.destroy()

        def do_merge():
            result_var.set('do')
            if dont_ask_again.get():
                update_settings(True)
            merge_dialog.destroy()

        def update_settings(val: bool):
            self.def_merge_on_load.set(val)
            print(f'Set {self.setting_names[id(self.def_merge_on_load)]} to: {val}')
            self.settings_file.write_text(json.dumps(self.settings, indent='\t'))

        merge_dialog = Toplevel(self.root)
        merge_dialog.title('Merge/Overwrite current project?')
        merge_dialog.geometry(f'255x111+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}')
        merge_dialog.protocol('WM_DELETE_WINDOW', cancel)
        merge_dialog.grab_set()
        merge_dialog.focus()
        merge_dialog.transient(self.root)
        merge_dialog.resizable(False, False)

        confirm_label = Label(merge_dialog, text='Would you like to merge the incoming project\n'
                                                 'with the current project?')
        confirm_label.place(relx=0.5, anchor='n')

        dont_ask_again = BooleanVar()
        dont_ask_again_check = Checkbutton(merge_dialog, text='Remember my choice', variable=dont_ask_again)
        dont_ask_again_check.place(relx=0.5, y=40, anchor='n')

        yes_button = Button(merge_dialog, text='Merge', width='10', command=do_merge)
        yes_button.place(relx=0.5, rely=1, x=-10, y=-10, anchor='se')

        no_button = Button(merge_dialog, text='Overwrite', width='10', command=do_not_merge)
        no_button.place(relx=0.5, rely=1, x=10, y=-10, anchor='sw')

    def end_program(self, *_):
        if self.ask_to_save:
            self.ask_to_save_dialog(save_dialog_result := StringVar())
            self.root.wait_variable(save_dialog_result)
            if save_dialog_result.get() not in ('do', 'dont'):
                return
        if self.recovery_dir.is_dir() and not any(self.recovery_dir.iterdir()):
            shutil.rmtree(self.recovery_dir)
            print('Removed Empty Recovery Folder')
        if not self.is_server:
            print('')
        if self.is_server and not self.client_dict and self.finished_server_init:
            shutil.rmtree(self.global_temp, ignore_errors=True)
            print('Removed Global Temp')
        else:
            shutil.rmtree(self.instance_temp, ignore_errors=True)
            print('Removed Instance Temp')

        self.root.destroy()

    def easter(self, *_, increment=True):
        if self.easter_counter < 0:
            self.easter_counter = 0
            return
        if self.easter_call_after_id:
            self.root.after_cancel(self.easter_call_after_id)
            self.easter_call_after_id = None
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
            self.easter_call_after_id = self.root.after(500, lambda: self.easter(increment=False))  # type: ignore

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
            user32.ShowWindow(self.debug_console, 0)  # Hide console
            return
        elif not self.debug_console:
            return

        # Toggle console visibility
        if user32.IsWindowVisible(self.debug_console):
            user32.ShowWindow(self.debug_console, 0)  # Hide
        else:
            user32.ShowWindow(self.debug_console, 5)  # Show


class SettingsWin:
    def __init__(self, main: C4IconSwapper):
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Settings')
        self.w, self.h = (255, 325)
        self.window.geometry(f'{self.w}x{self.h}+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        self.halt_trace_calls = False
        self.entry_mod_delay_dict = {}
        self.var_trace_dict = {}

        self.title = Label(self.window, text='Default Settings', font=(label_font, 12, 'bold'))
        self.title.place(relx=0.5, y=5, anchor='n')

        # noinspection PyTypeChecker
        trace = main.def_get_all_driver_imgs.trace_add('write',
                                                       lambda *_: self.update_setting(main.def_get_all_driver_imgs))
        self.var_trace_dict[id(main.def_get_all_driver_imgs)] = (main.def_get_all_driver_imgs, trace)
        self.get_all_driver_imgs_check = Checkbutton(self.window, text='Get ALL images from driver',
                                                     variable=main.def_get_all_driver_imgs)

        # noinspection PyTypeChecker
        trace = main.def_get_all_connections.trace_add('write',
                                                       lambda *_: self.update_setting(main.def_get_all_connections))
        self.var_trace_dict[id(main.def_get_all_connections)] = (main.def_get_all_connections, trace)
        self.get_all_connections_check = Checkbutton(self.window, text='Get ALL connections from driver',
                                                     variable=main.def_get_all_connections)

        # noinspection PyTypeChecker
        trace = main.def_use_original_xml.trace_add('write',
                                                       lambda *_: self.update_setting(main.def_use_original_xml))
        self.var_trace_dict[id(main.def_use_original_xml)] = (main.def_use_original_xml, trace)
        self.use_original_xml_check = Checkbutton(self.window, text='Use original driver XML',
                                                     variable=main.def_use_original_xml)

        self.merge_imgs_on_load_check = None
        if main.def_merge_on_load.get() != -1:
            # noinspection PyTypeChecker
            trace = main.def_merge_on_load.trace_add('write',
                                                     lambda *_: self.update_setting(main.def_merge_on_load))
            self.var_trace_dict[id(main.def_merge_on_load)] = (main.def_merge_on_load, trace)
            self.merge_imgs_on_load_check = Checkbutton(self.window, text='Merge new project with\n'
                                                                          'existing project during load',
                                                        variable=main.def_merge_on_load)

        # noinspection PyTypeChecker
        trace = main.def_include_backup_files.trace_add('write',
                                                        lambda *_: self.update_setting(main.def_include_backup_files))
        self.var_trace_dict[id(main.def_include_backup_files)] = (main.def_include_backup_files, trace)
        self.include_backup_files_check = Checkbutton(self.window, text='Include .bak files when exporting',
                                                      variable=main.def_include_backup_files)

        # noinspection PyTypeChecker
        trace = main.def_inc_driver_version.trace_add('write',
                                                      lambda *_: self.update_setting(main.def_inc_driver_version))
        self.var_trace_dict[id(main.def_inc_driver_version)] = (main.def_inc_driver_version, trace)
        self.inc_driver_ver_check = Checkbutton(self.window, text='Increment driver version on each export',
                                                variable=main.def_inc_driver_version)

        self.driver_manufac_label = Label(self.window, text='Driver Manufacturer:')
        self.driver_manufac_entry = Entry(self.window, width=19, textvariable=main.def_driver_manufacturer)
        # noinspection PyTypeChecker
        trace = main.def_driver_manufacturer.trace_add('write',
                                                       lambda *_: self.update_setting(main.def_driver_manufacturer,
                                                                                      entry=self.driver_manufac_entry))
        self.var_trace_dict[id(main.def_driver_manufacturer)] = (main.def_driver_manufacturer, trace)

        self.driver_creator_label = Label(self.window, text='Driver Creator:')
        self.driver_creator_entry = Entry(self.window, width=25, textvariable=main.def_driver_creator)
        # noinspection PyTypeChecker
        trace = main.def_driver_creator.trace_add('write',
                                                  lambda *_: self.update_setting(main.def_driver_creator,
                                                                                 entry=self.driver_creator_entry))
        self.var_trace_dict[id(main.def_driver_creator)] = (main.def_driver_creator, trace)

        def path_str_update():
            return ('Same Directory as Application'
                    if not (var_val := main.def_quick_export_dir.get())
                    else var_val)

        self.quick_export_label = Label(self.window, text='Quick Export Directory')
        self.quick_export_string = StringVar(value=path_str_update())
        self.quick_export_entry = Entry(self.window, width=27, textvariable=self.quick_export_string)
        if not main.def_quick_export_dir.get():
            self.quick_export_entry['state'] = DISABLED
        else:
            self.quick_export_entry['state'] = 'readonly'
        # noinspection PyTypeChecker
        trace = main.def_quick_export_dir.trace_add('write',
                                                    lambda *_: self.quick_export_string.set(path_str_update()))
        self.var_trace_dict[id(main.def_quick_export_dir)] = (main.def_quick_export_dir, trace)
        self.quick_export_button = Button(self.window, text='Browse...', width=8, command=self.select_quick_export_dir)

        self.restore_defaults_button = Button(self.window, text='Restore Defaults',
                                              width=15, command=self.restore_defaults)
        self.place_tk_objects()

    def place_tk_objects(self):
        self.window.geometry(f'{self.w}x{self.h}')
        y_val = 30
        self.get_all_driver_imgs_check.place(x=5, y=y_val, anchor='nw')
        y_val += 25
        self.get_all_connections_check.place(x=5, y=y_val, anchor='nw')
        y_val += 25
        self.use_original_xml_check.place(x=5, y=y_val, anchor='nw')
        y_val += 25
        if self.merge_imgs_on_load_check:
            self.window.geometry(f'{self.w}x{self.h + 42}')
            self.merge_imgs_on_load_check.place(x=5, y=y_val, anchor='nw')
            y_val += 42
        self.include_backup_files_check.place(x=5, y=y_val, anchor='nw')
        y_val += 25
        self.inc_driver_ver_check.place(x=5, y=y_val, anchor='nw')
        y_val += 30
        self.driver_manufac_label.place(x=5, y=y_val, anchor='nw')
        self.driver_manufac_entry.place(x=119, y=y_val + 2, anchor='nw')
        y_val += 30
        self.driver_creator_label.place(x=5, y=y_val, anchor='nw')
        self.driver_creator_entry.place(x=85, y=y_val + 2, anchor='nw')
        y_val += 32
        self.quick_export_label.place(relx=0.5, y=y_val, anchor='n')
        y_val += 25
        self.quick_export_entry.place(x=5, y=y_val, anchor='nw')
        self.quick_export_button.place(x=210, y=y_val - 3, anchor='n')
        y_val += 45
        self.restore_defaults_button.place(relx=0.5, y=y_val, anchor='n')

    def update_setting(self, setting_var, *_, entry=None):
        if self.halt_trace_calls:
            return
        setting_name = self.main.setting_names[id(setting_var)]
        if isinstance(setting_var, (IntVar, BooleanVar)):
            print(f'Set {setting_name} to: {bool(setting_var.get())}')
        elif isinstance(setting_var, StringVar):
            self.main.validate_man_and_creator(setting_var, entry)
            if existing_after_call := self.entry_mod_delay_dict.get(id(setting_var)):
                self.window.after_cancel(existing_after_call[0])
                self.entry_mod_delay_dict.pop(id(setting_var))
            after_call = self.window.after(2000, self.string_setting_update, *(setting_name, setting_var))
            self.entry_mod_delay_dict[id(setting_var)] = (after_call, setting_name, setting_var)
            return
        else:
            settings_str = ',\n\t'.join([f'{setting}: {val}' for setting, val in self.main.settings.items()])
            print(f'New settings: {{\n\t{settings_str}\n}}')
        self.main.settings_file.write_text(json.dumps(self.main.settings, indent='\t'))

    def string_setting_update(self, setting_name, setting_var):
        if self.halt_trace_calls:
            return
        print(f'Set {setting_name} to: {setting_var.get()}')
        self.main.settings_file.write_text(json.dumps(self.main.settings, indent='\t'))
        self.entry_mod_delay_dict.pop(id(setting_var))

    def select_quick_export_dir(self):
        folder_path = filedialog.askdirectory(title='Select Quick Export Directory', initialdir=Path.cwd())
        if folder_path:
            self.main.def_quick_export_dir.set(folder_path)
            self.quick_export_string.set(folder_path)
            self.quick_export_entry['state'] = 'readonly'
            self.main.settings_file.write_text(json.dumps(self.main.settings, indent='\t'))
            print(f'Set {self.main.setting_names[id(self.main.def_quick_export_dir)]} to: {folder_path}')
        self.window.focus()

    def restore_defaults(self):
        self.halt_trace_calls = True
        for value in list(self.entry_mod_delay_dict.values()):
            self.window.after_cancel(value[0])
        self.entry_mod_delay_dict.clear()
        if self.merge_imgs_on_load_check:
            self.merge_imgs_on_load_check.destroy()
            self.merge_imgs_on_load_check = None
        for setting_name in self.main.setting_names.values():
            getattr(self.main, setting_name).set(self.main.setting_defaults[setting_name])
        self.quick_export_entry['state'] = DISABLED
        self.place_tk_objects()
        self.halt_trace_calls = False
        self.main.settings_file.write_text(json.dumps(self.main.settings, indent='\t'))
        settings_str = ',\n\t'.join([f'{setting}: {val}' for setting, val in self.main.settings.items()])
        print(f'Restored default settings: {{\n\t{settings_str}\n}}')

    def close(self):
        for setting_var, trace in self.var_trace_dict.values():
            setting_var.trace_remove('write', trace)
        for value in list(self.entry_mod_delay_dict.values()):
            self.window.after_cancel(value[0])
            self.string_setting_update(value[1], value[2])
        self.window.destroy()
        self.main.settings_win = None


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
    def __init__(self, instance_id, img_path: Path, name: str, size: int | tuple[int, int], bak_path: Path = None):
        self.name = name
        # Full path to image file
        self.path = img_path
        # Relative path to icon from driver folder
        self.rel_path = Path(*(parts := img_path.parts)[parts.index(instance_id) + 2:])
        # Full path to bak file
        self.bak_path = bak_path
        # Relative path to bak file from driver folder
        self.rel_bak_path = None if not bak_path else Path(*(parts := bak_path.parts)[parts.index(instance_id) + 2:])
        if isinstance(size, int) and not isinstance(size, bool):
            self.size = (size, size)
        elif (isinstance(size, (tuple, list)) and len(size) == 2 and
              all(isinstance(n, int) and not isinstance(n, bool) for n in size)):
            self.size = tuple(size)
        else:
            raise ValueError(f'Expected int or tuple[int, int]. Received: {type(size).__name__}: {size}')

    def update_path(self, new_driver_dir: Path):
        self.path = new_driver_dir / self.rel_path
        if self.bak_path:
            self.bak_path = new_driver_dir / self.rel_bak_path


class C4Icon(Icon):
    def __init__(self, icons: list[C4SubIcon] | set[C4SubIcon], name=None, replacement_icon=None, extra=False):
        if isinstance(icons, set):
            icons = sorted(icons, key=lambda sub_icon: sub_icon.size[0], reverse=True)
        else:
            icons.sort(key=lambda sub_icon: sub_icon.size[0], reverse=True)
        self.display_icon = icons[0]
        super().__init__(path=self.display_icon.path)
        self.tk_icon_sm = None
        self.name = name or self.display_icon.name
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

    @property
    def tk_img(self):
        if self.replacement_icon:
            return self.replacement_icon.tk_icon_lg
        if self.restore_bak:
            return self.bak_tk_icon
        return self.tk_icon_lg

    def refresh_tk_img(self, bak=False):
        if bak and self.bak:
            icon = max(self.icons, key=lambda sub_icon: sub_icon.size[0] if sub_icon.bak_path else None)
            with Image.open(icon.bak_path) as img:
                self.bak_tk_icon = ImageTk.PhotoImage(img.resize((128, 128), Resampling.BICUBIC))
            return
        with Image.open(self.path) as img:
            self.tk_icon_lg = ImageTk.PhotoImage(img.resize((128, 128), Resampling.BICUBIC))

    def replace(self, icon: Icon):
        self.replacement_icon = icon

    def set_restore(self):
        if self.replacement_icon:
            self.replacement_icon = None
            return
        self.restore_bak = True if self.bak else False

    def update_path(self, new_driver_dir: Path):
        for icon in self.icons:
            icon.update_path(new_driver_dir)
        self.path = self.display_icon.path


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
        self.window.geometry(f'225x255+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        # Labels
        self.sub_icon_label = Label(window, image=main.img_blank)
        self.sub_icon_label.place(relx=0.5, y=10, anchor='n')
        self.sub_icon_label.image = main.img_blank
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
        self.name_label.config(text=curr_sub_icon.path.name)
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
        subprocess.Popen(f'explorer /select,"{self.icons[self.curr_index].path.resolve()}"')


class DriverInfoWin:
    def __init__(self, main: C4IconSwapper):
        ask_to_save = main.ask_to_save
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Edit Driver Info')
        self.window.geometry(f'255x215+{main.root.winfo_rootx() + main.export_panel.x}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)

        # Labels
        font_size = 10
        man_y = 20
        man_arrow = Label(self.window, text='\u2192', font=('', 15))
        man_arrow.place(x=115, y=man_y, anchor='nw')

        creator_y = man_y + 55
        creator_arrow = Label(self.window, text='\u2192', font=('', 15))
        creator_arrow.place(x=115, y=creator_y, anchor='nw')

        version_y = creator_y + 55
        version_arrow = Label(self.window, text='\u2192', font=('', 15))
        version_arrow.place(x=115, y=version_y, anchor='nw')

        driver_man_label = Label(self.window, text='Driver Manufacturer', font=(label_font, font_size))
        driver_man_label.place(relx=0.5, y=man_y - 15, anchor='n')

        driver_creator_label = Label(self.window, text='Driver Creator', font=(label_font, font_size))
        driver_creator_label.place(relx=0.5, y=creator_y - 15, anchor='n')

        driver_ver_label = Label(self.window, text='Driver Version', font=(label_font, font_size))
        driver_ver_label.place(relx=0.5, y=version_y - 15, anchor='n')

        driver_ver_orig_label = Label(self.window, text='Original Version', font=(label_font, 8))
        driver_ver_orig_label.place(relx=0.5, y=version_y + 65, anchor='n')

        # Entries
        entry_width = 17
        driver_man_entry = Entry(self.window, width=entry_width, textvariable=main.driver_manufac_var)
        driver_man_entry.place(x=10, y=man_y + 7, anchor='nw')
        driver_man_entry['state'] = DISABLED

        self.driver_man_new_entry = Entry(self.window, width=entry_width, textvariable=main.driver_manufac_new_var)
        self.driver_man_new_entry.place(x=140, y=man_y + 7, anchor='nw')
        main.driver_manufac_new_var.trace_add('write',
                                              lambda name, index, mode: self.main.validate_man_and_creator(
                                                  string_var=main.driver_manufac_new_var,
                                                  entry=self.driver_man_new_entry))

        driver_creator_entry = Entry(self.window, width=entry_width, textvariable=main.driver_creator_var)
        driver_creator_entry.place(x=10, y=creator_y + 7, anchor='nw')
        driver_creator_entry['state'] = DISABLED

        self.driver_creator_new_entry = Entry(self.window, width=entry_width, textvariable=main.driver_creator_new_var)
        self.driver_creator_new_entry.place(x=140, y=creator_y + 7, anchor='nw')
        main.driver_creator_new_var.trace_add('write',
                                              lambda name, index, mode: self.main.validate_man_and_creator(
                                                  string_var=main.driver_creator_new_var,
                                                  entry=self.driver_creator_new_entry))

        driver_ver_entry = Entry(self.window, width=entry_width, textvariable=main.driver_version_var)
        driver_ver_entry.place(x=10, y=version_y + 7, anchor='nw')
        driver_ver_entry['state'] = DISABLED

        self.driver_ver_new_entry = Entry(self.window, width=entry_width, textvariable=main.driver_version_new_var)
        self.driver_ver_new_entry.place(x=140, y=version_y + 7, anchor='nw')
        self.driver_ver_new_entry.bind('<FocusOut>', main.update_driver_version)
        main.driver_version_new_var.trace_add('write', main.validate_driver_ver)

        driver_ver_orig_entry = Entry(self.window, width=15, justify='center', textvariable=main.driver_ver_orig)
        driver_ver_orig_entry.place(relx=0.5, y=version_y + 45, anchor='n')
        driver_ver_orig_entry['state'] = DISABLED

        self.update_entries()
        main.ask_to_save = ask_to_save

    # noinspection PyTypeChecker
    def update_entries(self):
        main = self.main
        entry_state = DISABLED if (val := main.export_panel.use_orig_xml.get()) else NORMAL
        self.driver_man_new_entry.config(
            textvariable=(main.driver_manufac_var if val else main.driver_manufac_new_var), state=entry_state)
        self.driver_creator_new_entry.config(
            textvariable=(main.driver_creator_var if val else main.driver_creator_new_var), state=entry_state)
        self.driver_ver_new_entry.config(textvariable=(main.driver_ver_orig if val else main.driver_version_new_var),
                                         state=entry_state)

    def close(self):
        self.main.validate_man_and_creator(string_var=self.main.driver_manufac_new_var, entry=self.driver_man_new_entry)
        self.main.validate_man_and_creator(string_var=self.main.driver_creator_new_var,
                                           entry=self.driver_creator_new_entry)
        self.main.validate_driver_ver()
        self.window.destroy()
        self.main.driver_info_win = None


# TODO: Remove time traces
class ConnectionsWin:
    def __init__(self, main: C4IconSwapper):
        start = time.perf_counter()

        self.supress_trace = True
        # Initialize window
        ask_to_save = main.ask_to_save
        self.main = main
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Edit Driver Connections')
        self.size = w, h = (375, 250)
        self.window.geometry(f'{w}x{h}+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.bind('<Configure>', self.on_resize)
        self.resize_after_call_id = None
        self.threaded_refresh = threading.Event()
        self.threaded_refresh.set()

        self.canvas = Canvas(self.window, highlightthickness=0, borderwidth=0)
        self.scrollbar = Scrollbar(self.window, orient='vertical', command=self.canvas.yview)
        self.scrollbar.config(command='')
        self.scrollbar.pack(side='right', fill='y')
        self.scrollable_frame = Frame(self.canvas)
        self.canvas_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scroll_bound = False

        self.widget_x = 15
        self.widget_y_offset = 40
        self.y_pad = 25
        self.scroll_pad = 20
        num_conns = len(main.connections)
        self.connection_entries = [
            ConnectionEntry(self, main.connections[i], self.widget_x, i * self.widget_y_offset + self.y_pad)
            for i in range(num_conns)
        ]
        scroll_h = (num_conns * self.widget_y_offset) + self.scroll_pad
        self.scrollable_frame.config(width=w, height=scroll_h)
        self.canvas.configure(scrollregion=(0, 0, w, scroll_h))
        self.canvas.pack(side='left', fill='both', expand=True)
        if scroll_h > h + 20:
            self.scrollbar.config(command=self.canvas.yview)
            self.window.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))
            self.scroll_bound = True

        main.ask_to_save = ask_to_save
        self.supress_trace = False
        end = time.perf_counter()
        print(f'ConnectionsWin Init - {num_conns} Connections: {end - start:.6f} seconds')

    def on_resize(self, *_, called_after=False):
        if self.supress_trace or (new_size := (self.window.winfo_width(), self.window.winfo_height())) == self.size:
            return
        if not called_after:
            if self.resize_after_call_id:
                self.window.after_cancel(self.resize_after_call_id)
            self.resize_after_call_id = self.window.after(5, lambda: self.on_resize(called_after=True))  # type: ignore
            return
        self.size = new_size
        self.update_scroll_frame()
        if self.resize_after_call_id:
            self.resize_after_call_id = None

    def refresh(self, hard=False, threaded=False, _from_thread=False):
        if threaded:
            self.threaded_refresh.clear()
            threading.Thread(target=self.refresh, kwargs={'hard': hard, '_from_thread': True}, daemon=True).start()
            return
        if not self.threaded_refresh.is_set() and not _from_thread:
            return
        start = time.perf_counter()
        if hard:
            self.supress_trace = True
            self.canvas.itemconfig(self.canvas_window_id, window='')
            for conn_entry in self.connection_entries:
                conn_entry.destroy()
            end = time.perf_counter()
            print(f'ConnectionsWin frame destroy: {end - start:.6f} seconds')
            self.connection_entries = [
                ConnectionEntry(self, self.main.connections[i], self.widget_x, i * self.widget_y_offset + self.y_pad)
                for i in range(len(self.main.connections))
            ]
            self.update_scroll_frame()  # doing this after canvas config takes much longer, and it seems to work as is
            self.canvas.itemconfig(self.canvas_window_id, window=self.scrollable_frame)
            self.supress_trace = False
            self.threaded_refresh.set()

            end = time.perf_counter()
            print(f'ConnectionsWin refresh (hard): {end - start:.6f} seconds')
            return

        for conn_entry in self.connection_entries:
            conn_entry.refresh()
        self.update_scroll_frame()
        self.threaded_refresh.set()

        end = time.perf_counter()
        print(f'ConnectionsWin refresh (soft): {end - start:.6f} seconds')

    def update_scroll_frame(self):
        num_conns = len(self.main.connections)
        w, h = self.window.winfo_width(), self.window.winfo_height()
        scroll_h = (num_conns * self.widget_y_offset) + self.scroll_pad
        self.scrollable_frame.config(width=w, height=scroll_h)
        self.canvas.configure(scrollregion=(0, 0, w, scroll_h))
        if not self.scroll_bound and scroll_h > h + 20:
            self.scrollbar.config(command=self.canvas.yview)
            self.window.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))
            self.scroll_bound = True
        elif self.scroll_bound and scroll_h <= h + 20:
            self.scrollbar.config(command='')
            self.window.unbind('<MouseWheel>')
            self.scroll_bound = False

    def close(self):
        self.threaded_refresh.wait()
        self.window.destroy()
        self.main.connections_win = None


class Connection:
    def __init__(self, main: C4IconSwapper, cid=-1, cname='Connection Name...', ctype='HDMI IN', tag=None,
                 original=False, enabled=False, delete=False):
        self.main = main
        self.id = cid
        self.original, self.enabled, self.delete = original, enabled, delete
        self.tag = tag or XMLTag(xml_string=connection_tag_generic)
        self.tag.hide = True if not original else False
        if not original:
            self.name_entry_var = StringVar(value=cname)
            self.type_var = StringVar(value=ctype)
        else:
            self.name = cname
            self.type = ctype

    def update_id(self, *_):
        if self.original:
            return
        # Removes self from dict in case a lower id has opened up so that ids are used in ascending order
        if (conn_obj_in_dict := self.main.taken_conn_ids.get(self.id)) and self is conn_obj_in_dict:
            self.main.taken_conn_ids.pop(self.id)
        if not self.enabled:
            self.id = -1
            return
        new_type = self.type_var.get()
        new_id = conn_id_type[new_type][0]
        while new_id in self.main.taken_conn_ids:
            new_id += 1
        self.main.taken_conn_ids[new_id] = self
        self.id = new_id
        self.tag.get_tag('type').set_value(conn_id_type[new_type][1])
        self.tag.get_tag('id').set_value(str(self.id))


class ConnectionEntry:
    def __init__(self, parent: ConnectionsWin, conn_obj: Connection, x_pos: int, y_pos: int):
        # Initialize Connection UI Object
        self.main = parent.main
        self.parent = parent
        self.frame = parent.scrollable_frame
        self.conn_object = conn_obj
        self.x, self.y = x_pos, y_pos

        self.strike = None

        # Entry
        if conn_obj.original:
            self.name_entry = Entry(self.frame, width=28)
            self.name_entry.insert(0, conn_obj.name)
            self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
        else:
            self.name_entry_var = conn_obj.name_entry_var
            self.name_entry_var.trace_add('write', self.name_update)
            self.name_entry = Entry(self.frame, width=28, textvariable=self.name_entry_var)
            self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')

        # Dropdown
        if conn_obj.original:
            self.type_menu = Label(self.frame, text=conn_obj.type, relief='raised', padx=7, pady=4)
            self.type_menu.place(x=self.x + 212, y=self.y, anchor='w')
        else:
            self.type_var = conn_obj.type_var
            self.type_menu = OptionMenu(self.frame, self.type_var, *selectable_connections)
            self.type_menu.place(x=self.x + 210, y=self.y, anchor='w')
            self.type_var.trace_add('write', self.type_update)

        # Button
        button_state = DISABLED if self.main.export_panel.use_orig_xml.get() else NORMAL
        if conn_obj.original:
            if conn_obj.delete and conn_obj.original:
                self.strike = Frame(self.parent.scrollable_frame, bg='black', height=1)
                self.strike.place(in_=self.name_entry, relx=0, rely=0.5, relwidth=0.999)
                self.name_entry.config(readonlybackground='pink')
                text = 'Keep'
                width = 4
                x_offset = -6
            else:
                text = 'Del'
                width = 3
                x_offset = 0
        elif conn_obj.enabled:
            text = 'x'
            width = 1
            x_offset = 14
        else:
            text = 'Add'
            width = 3
            x_offset = 0
            if not self.main.driver_selected:
                button_state = DISABLED

        self.action_button = Button(self.frame, text=text, width=width, command=self.action, takefocus=0)
        self.action_button.place(x=self.x + x_offset, y=self.y, anchor='w')
        self.action_button['state'] = button_state
        self.type_menu['state'] = DISABLED if not conn_obj.enabled else button_state
        self.name_entry['state'] = 'readonly' if self.conn_object.original else button_state
        if not conn_obj.enabled:
            if not conn_obj.original:
                self.name_entry['state'] = DISABLED

    def refresh(self):
        if not (original := self.conn_object.original):
            self.name_entry_var.set(self.conn_object.name_entry_var.get())
            self.type_var.set(self.conn_object.type_var.get())
        self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
        self.type_menu.place(x=self.x + 210, y=self.y, anchor='w')
        state = DISABLED if self.main.export_panel.use_orig_xml.get() else NORMAL
        if self.conn_object.enabled:
            self.type_menu['state'] = state
            self.name_entry['state'] = state
        else:
            self.type_menu['state'] = DISABLED
            self.name_entry['state'] = 'readonly' if original else DISABLED

        if original:
            if self.conn_object.delete:
                self.action_button.config(text='Keep', width=4, state=state)  # type: ignore
                self.action_button.place(x=self.x - 6, y=self.y, anchor='w')
                self.name_entry['state'] = DISABLED
            else:
                self.action_button.config(text='Del', width=3, state=state)  # type: ignore
                self.action_button.place(x=self.x, y=self.y, anchor='w')
        elif self.conn_object.enabled:
            self.action_button.config(text='x', width=1, state=state)  # type: ignore
            self.action_button.place(x=self.x + 14, y=self.y, anchor='w')
        else:
            # noinspection PyTypeChecker
            self.action_button.config(text='Add', width=3, state=state if self.main.driver_selected else DISABLED)
            self.action_button.place(x=self.x, y=self.y, anchor='w')

    def action(self):
        match self.action_button['text']:
            case 'Add':
                self.conn_object.enabled = True
                self.conn_object.tag.hide = False
                self.conn_object.update_id()
                self.name_entry['state'] = NORMAL
                self.type_menu['state'] = NORMAL
                self.action_button.config(text='x', width=1)
                self.action_button.place(x=self.x + 14)
                self.name_entry['takefocus'] = 1
                self.main.connections.append(new_conn := Connection(self.main))
                self.main.driver_xml.get_tag('connections').add_element(new_conn.tag)
                self.parent.connection_entries.append(
                    ConnectionEntry(self.parent, new_conn, self.parent.widget_x,
                                    self.y + self.parent.widget_y_offset))
                self.parent.update_scroll_frame()
            case 'x':
                self.parent.connection_entries.pop(i := self.parent.connection_entries.index(self))
                self.main.connections.pop(i)
                self.main.driver_xml.get_tag('connections').remove_element(self.conn_object.tag)
                if (in_dict := self.main.taken_conn_ids.get(self.conn_object.id)) and self.conn_object is in_dict:
                    self.main.taken_conn_ids.pop(self.conn_object.id)
                self.destroy()
                for conn_entry in self.parent.connection_entries[i:]:
                    conn_entry.y -= self.parent.widget_y_offset
                    conn_entry.refresh()
                self.parent.update_scroll_frame()
            case 'Del':
                self.conn_object.delete = True
                self.conn_object.tag.hide = True
                if not self.strike:
                    self.strike = Frame(self.parent.scrollable_frame, bg='black', height=1)
                self.strike.place(in_=self.name_entry, relx=0, rely=0.5, relwidth=0.999)
                self.name_entry.config(readonlybackground='pink')
                self.action_button.config(text='Keep', width=4)
                self.action_button.place(x=self.x - 6)
            case 'Keep':
                self.conn_object.delete = False
                self.conn_object.tag.hide = False
                self.strike.place_forget()
                self.name_entry.config(readonlybackground=readonly_bg)
                self.action_button.config(text='Del', width=3)
                self.action_button.place(x=self.x)
        self.main.ask_to_save = True

    def name_update(self, *_):
        if self.parent.supress_trace:
            return
        self.main.ask_to_save = True

    def type_update(self, *_):
        if self.parent.supress_trace:
            return
        self.main.ask_to_save = True
        self.conn_object.update_id()

    def destroy(self):
        self.name_entry.destroy()
        self.type_menu.destroy()
        self.action_button.destroy()


class StatesWin:
    def __init__(self, main: C4IconSwapper):
        ask_to_save = main.ask_to_save
        self.main = main

        # Initialize window
        self.window = Toplevel(main.root)
        self.window.focus()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.title('Edit Driver States')
        self.window.geometry(f'385x287+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        self.window.resizable(False, False)
        self.trace_lockout = False

        self.state_entries = []
        x_spacing, y_spacing = 200, 34
        x_offset, y_offset = 10, 30
        self.state_entries.extend(StateEntry(self, main.states[i], int(i / 7) * x_spacing + x_offset,
                                             (i % 7) * y_spacing + y_offset, label=f'state{str(i + 1)}:')
                                  for i in range(13))
        main.ask_to_save = ask_to_save

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

    def close(self):
        self.refresh()
        self.window.destroy()
        self.main.states_win = None


class State:
    def __init__(self, name: str):
        self.original_name = name
        self.name_var = StringVar(value=name)
        self.bg_color = light_entry_bg

    @property
    def name(self):
        return self.name_var.get()


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
        self.name_entry_var = StringVar(value=state_obj.name)
        self.name_entry_var.trace_add('write', self.on_name_update)
        self.name_entry = Entry(self.window, width=20, textvariable=self.name_entry_var)
        self.name_entry.place(x=self.x + 35, y=self.y, anchor='w')
        self.name_entry['background'] = state_obj.bg_color
        if not self.main.multi_state_driver:
            self.name_entry['state'] = DISABLED

    def get(self):
        return self.name_entry_var.get()

    def refresh(self, bg_only=False):
        self.name_entry['background'] = self.state_object.bg_color
        if bg_only:
            return
        self.name_entry_var.set(self.state_object.name)

    def on_name_update(self, *_):
        if self.main.states_win:
            if self.main.states_win.trace_lockout:
                return
            self.main.states_win.validate_states()

    def update_state_name(self):
        name = self.name_entry_var.get()
        # Substitute non-alphanumeric chars with ''
        formatted_name = re.sub(r'[^a-zA-Z0-9]', '', name).capitalize()
        if not formatted_name:
            self.name_entry_var.set('')
            return
        if str_diff := len(name) - len(formatted_name):
            cursor_pos = self.name_entry.index(INSERT)
            self.name_entry.icursor(cursor_pos - str_diff)
        self.name_entry_var.set(formatted_name)
        self.state_object.name_var.set(formatted_name)


class RecoveryWin:
    def __init__(self, main: C4IconSwapper, *_):
        if not (recovery_dir := main.recovery_dir).is_dir():
            return
        # Delete any non-directories in Recovery folder (Just in case)
        for path in recovery_dir.iterdir():
            if path.is_dir():
                continue
            path.unlink()
            print(f'Deleted invalid item from Recovery folder {path.name}')
        if not (num_of_rec_folders := len(os.listdir(recovery_dir))):
            shutil.rmtree(recovery_dir)
            if not main.is_server:
                print('')
            print('Deleted empty Recovery folder')
            return
        self.window = window = Toplevel(main.root)
        self.main = main
        self.recovery_dir = recovery_dir
        window.grab_set()
        window.focus()
        window.transient(main.root)
        window.title('Project Recovery')
        window.geometry(f'355x287+{main.root.winfo_rootx()}+{main.root.winfo_rooty()}')
        window.resizable(False, False)
        window.protocol('WM_DELETE_WINDOW', self.close_dialog)

        self.recoverable_projects = [rec_obj for path in recovery_dir.iterdir() if (rec_obj := RecoveryObject(path))]

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
            self.recoverable_projects[-1].recover.set(True)
        for check in self.checkboxes:
            check.pack(anchor='w')
            if do_scroll:
                check.bind('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

        recover_button = Button(window, text='Recover', width=10, command=self.do_recovery)
        recover_button.place(relx=0.5, x=-4, rely=1, y=-3, anchor='se')

        delete_button = Button(window, text='Delete' if num_of_rec_folders == 1 else 'Delete All',
                               width=10, command=self.close_dialog)
        delete_button.place(relx=0.5, x=4, rely=1, y=-3, anchor='sw')

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
        warning_dialog.geometry(f'260x85+{self.window.winfo_rootx()}+{self.window.winfo_rooty()}')
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
        def start_new_instance(args):
            # Start debug console hidden
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            print('Launching new application to open recovered project')
            subprocess.Popen(args, startupinfo=startupinfo, creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)

        selected = [rec_obj for rec_obj in self.recoverable_projects if rec_obj.recover.get()]
        if not selected:
            return

        # Warn that unselected projects will be deleted
        if len(selected) != len(self.recoverable_projects):
            self.warning_dialog(abort_recovery := BooleanVar())
            self.window.wait_variable(abort_recovery)
            if abort_recovery.get():
                return

        own_project = None
        if self.main.running_as_exe:
            args_template = [sys.executable]
        else:
            # Path to exe, path to python script, recovery path variable
            args_template = [sys.executable, Path(__file__).resolve()]

        # Delete projects which were not selected
        for recovery_obj in [rec_obj for rec_obj in self.recoverable_projects if rec_obj not in selected]:
            shutil.rmtree(recovery_obj.path)

        # Flag first project to open in self and start new programs to open any remaining projects
        for recovery_obj in selected:
            if not own_project:
                own_project = recovery_obj.path
                continue
            start_new_instance([*args_template, recovery_obj.path])

        # Open recovery project
        if own_project:
            print('Opening recovered project')
            self.main.do_recovery(own_project)

        self.window.destroy()
        self.main.root.deiconify()
        self.main.root.focus()

    def close_dialog(self):
        def exit_close_dialog():
            close_dialog.destroy()
            self.window.deiconify()
            self.window.focus()

        def do_delete():
            shutil.rmtree(self.recovery_dir)
            close_dialog.destroy()
            self.window.destroy()
            self.main.root.deiconify()
            self.main.root.focus()

        close_dialog = Toplevel(self.window)
        close_dialog.title('Are you sure?')
        close_dialog.geometry(f'239x70+{self.window.winfo_rootx()}+{self.window.winfo_rooty()}')
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


class RecoveryObject:
    def __init__(self, instance_path: Path):
        self.init_success = False
        if not instance_path.is_dir():
            return
        self.name = ''
        self.path = instance_path
        self.has_driver = (xml_path := instance_path / 'driver' / 'driver.xml').is_file()
        self.num_images = 0
        self.mtime = datetime.fromtimestamp(instance_path.stat().st_mtime).strftime("%m/%d %H:%M:%S")
        self.recover = BooleanVar()

        replacement_path = instance_path / 'Replacement Icons'
        if self.has_driver and (tag := XMLTag(xml_path=xml_path, sub_tag='name')) and (name := tag.value):
            self.name = name
        if replacement_path.is_dir():
            self.num_images = len(os.listdir(replacement_path))

        if not self.name:
            if not self.num_images:
                return
            self.name = 'MsgNotFound' if xml_path.parent.exists() else 'No Driver'
        self.init_success = True

    def __bool__(self):
        return self.init_success


class C4zPanel:
    def __init__(self, main: C4IconSwapper):
        # Initialize C4z Panel
        self.main = main
        self.x, self.y = 5, 20
        self.current_icon, self.extra_icons = 0, 0
        self.icons = []

        self.sub_icon_win = None

        # Labels
        self.panel_label = Label(main.root, text='Driver Selection', font=(label_font, 15))
        self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')

        self.c4_icon_label = Label(main.root, image=main.img_blank)
        self.c4_icon_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.c4_icon_label.image = main.img_blank
        self.c4_icon_label.drop_target_register(DND_FILES)
        self.c4_icon_label.dnd_bind('<<Drop>>', self.drop_in_c4z)
        self.c4_icon_label.bind('<Button-3>', self.right_click_menu)

        self.icon_num_label = Label(main.root, text='0 of 0', font=(label_font, 10))
        self.icon_num_label.place(x=108 + self.x, y=180 + self.y, anchor='n')

        self.icon_name_label = Label(main.root, text='icon name', font=(label_font, 10, 'bold'), wraplength=220)
        self.icon_name_label.place(x=108 + self.x, y=197 + self.y, anchor='n')

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.load_c4z, takefocus=0)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.restore_button = Button(main.root, text='Restore\nOriginal Icon', command=self.restore, takefocus=0)
        self.restore_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.restore_button['state'] = DISABLED

        self.restore_all_button = Button(
            main.root, text='Restore All', command=lambda: self.restore(do_all=True), takefocus=0)
        self.restore_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.restore_all_button['state'] = DISABLED

        self.prev_icon_button = Button(
            main.root, text='Prev', command=lambda: self.inc_icon(inc=-1), width=5, takefocus=0)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = Button(main.root, text='Next', command=self.inc_icon, width=5, takefocus=0)
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)
        self.next_icon_button['state'] = DISABLED

        # Entry
        self.file_entry_str = StringVar(value='Select .c4z file...')
        self.file_entry_field = Entry(main.root, width=25, textvariable=self.file_entry_str, takefocus=0)
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field.drop_target_register(DND_FILES)
        self.file_entry_field.dnd_bind('<<Drop>>', self.drop_in_c4z)
        self.file_entry_field['state'] = DISABLED

        # Checkboxes
        self.show_extra_icons = BooleanVar()
        self.show_extra_icons.trace_add('write', self.toggle_extra_icons)
        self.show_extra_icons_check = Checkbutton(main.root, text='show extra icons',
                                                  variable=self.show_extra_icons, takefocus=0)
        self.show_extra_icons_check.place(x=177 + self.x, y=176 + self.y, anchor='nw')
        self.show_extra_icons_check.config(state='disabled')

    def load_gen_driver(self, multi=False):
        if self.main.pending_load_save:
            return
        main = self.main
        if main.ask_to_save:
            main.ask_to_save_dialog(save_dialog_result := StringVar(), on_exit=False)
            main.root.wait_variable(save_dialog_result)
            if save_dialog_result.get() not in ('do', 'dont'):
                return

        def gen_driver_unpack():
            self.main.pending_load_save = True
            device_icon_dir = main.instance_temp / 'driver' / 'www' / 'icons' / 'device'
            instance_driver_path = main.instance_temp / 'driver'
            with Image.open(assets_path / 'loading_img.png') as loading_img:
                icon = ImageTk.PhotoImage(loading_img)
                self.c4_icon_label.configure(image=icon)
                self.c4_icon_label.image = icon
            gen_driver_path = assets_path / ('multi_generic.c4z' if multi else 'generic.c4z')
            shutil.rmtree(instance_driver_path, ignore_errors=True)
            shutil.unpack_archive(gen_driver_path, instance_driver_path, 'zip')
            sizes = [70, 90, 300, 512]
            root_size = '1024'
            unpacking_dir = main.instance_temp / 'temp_unpacking'
            unpacking_dir.mkdir()
            for path in device_icon_dir.iterdir():
                with Image.open(path) as img:
                    for size in sizes:
                        resized_img = img.resize((size, size), Resampling.LANCZOS)
                        resized_img.save(unpacking_dir / path.name.replace(root_size, str(size)))
            for img_path in unpacking_dir.iterdir():
                img_path.replace(device_icon_dir / img_path.name)

            shutil.make_archive(str(unpacking_dir / 'driver'), 'zip', instance_driver_path)
            self.load_c4z(file_path=unpacking_dir / 'driver.zip', generic=True, bypass_ask_save=True,
                          new_thread=False, force=True)
            shutil.rmtree(unpacking_dir)

            main.export_panel.driver_name_var.set('New Driver')
            main.ask_to_save = False
            self.main.pending_load_save = False

        threading.Thread(target=gen_driver_unpack, daemon=True).start()

    def _load_c4z(self, file_path=None, generic=False, c4is=None):
        main = self.main

        abort = False
        driver_path = main.instance_temp / 'driver'
        new_driver_path = main.instance_temp / 'new_driver'
        new_icon_dir = new_driver_path / 'www' / 'icons'
        new_images_dir = new_driver_path / 'www' / 'images'

        # File select dialog
        if file_path is None:
            file_path = filedialog.askopenfilename(filetypes=[('Control4 Drivers', '*.c4z *.zip'),
                                                              ('All Files', '*.*')])
            if not file_path:  # If no file selected
                return

        # Unpack selected driver; Delete temp folder if it exists
        shutil.rmtree(new_driver_path, ignore_errors=True)
        shutil.unpack_archive(file_path, new_driver_path, 'zip')

        # Read XML
        driver_xml_bak = main.driver_xml
        if c4is:
            main.driver_xml = c4is.driver_xml
        elif new_driver := XMLObject(new_driver_path / 'driver.xml'):
            main.driver_xml = new_driver
        else:
            shutil.rmtree(new_driver_path, ignore_errors=True)
            abort = True  # TODO: Give option to load driver even if XML parsing fails

        # Get icons
        if not abort:
            # noinspection PyShadowingNames
            def get_icons(root_directory):
                if not root_directory:
                    return []
                directories = set()
                if isinstance(root_directory, (list, tuple)):
                    for path in root_directory:
                        if not path.is_dir():
                            continue
                        directories.update(list_all_sub_directories(path, include_root_dir=True))
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
                icon_groups = defaultdict(set)
                both_scheme = []
                all_sub_icons = set()
                all_paths = [path for directory in directories for path in directory.iterdir()]
                bak_pattern = re.compile(r'\.bak[^.]*$')
                bak_files = {
                    Path(path.parent, bak_pattern.sub('', path.name)): Path(path.parent, path.name)
                    for path in all_paths if bak_pattern.search(path.name)
                }
                for path in all_paths:
                    if not path.is_file() or path.suffix not in valid_img_types:
                        continue
                    try:
                        with Image.open(path) as img:
                            actual_size = img.size[0]
                    except Image.DecompressionBombError:
                        warnings.warn(f'Skipping potential decompression bomb: {path}', RuntimeWarning)
                        continue
                    except (UnidentifiedImageError, OSError):
                        print(f'Issue with item in get_icons: {path}')
                        continue
                    bak_path = bak_files.get(path.with_suffix(''))
                    img_info = re.search(r'^(?:(\d+)_)?(.+?)(?:_(\d+))?$', path.stem).groups()
                    l_label, img_name, r_label = img_info[0], img_info[1], img_info[2]
                    if not img_name:
                        img_name = path.stem

                    def matches_size(val):
                        return val and val.isdigit() and int(val) == actual_size
                    # Assume if name matches size that path.stem is formatted: #name-only-digits#_#size#
                    if matches_size(img_name):
                        img_name, r_label = (l_label or r_label), (r_label and img_name)
                    l_match, r_match = matches_size(l_label), matches_size(r_label)
                    if l_label and r_label and (l_match ^ r_match):
                        img_name = f'{img_name}_{r_label}' if l_match else f'{l_label}_{img_name}'
                    sub_icon = C4SubIcon(main.instance_id, path, img_name, actual_size, bak_path=bak_path)
                    if l_match and r_match:
                        both_scheme.append(sub_icon)
                    else:
                        icon_groups[img_name].add(sub_icon)
                    all_sub_icons.add(sub_icon)

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
                        icon_groups[icon_name].add(sub_icon)
                    elif found == 'r':
                        icon_name = f'{sub_icon.size[0]}_{sub_icon.name}'
                        sub_icon.name = icon_name
                        icon_groups[icon_name].add(sub_icon)
                    elif found == 'l':
                        icon_name = f'{sub_icon.name}_{sub_icon.size[0]}'
                        sub_icon.name = icon_name
                        icon_groups[icon_name].add(sub_icon)
                    else:
                        warnings.warn(f'Failed to parse icon data: {sub_icon.path}', RuntimeWarning)

                # Use XML data to form icon groups
                extras = set()
                standard_icons = set()
                group_dict: dict[tuple[str, XMLTag], set[Path]]
                group_dict = get_icon_groups()
                device_group = defaultdict(set)
                split_match = {'icons', 'images'}
                device_names = {'device_sm', 'device_lg'}
                for (group_name, _), group in group_dict.items():
                    group_set = set()
                    for sub_icon in list(all_sub_icons):
                        parts = sub_icon.rel_path.parts
                        split_point = next((idx for idx, part in enumerate(parts) if part in split_match), -1)
                        if Path(*parts[split_point:]) in group:
                            if sub_icon.path.stem in device_names:
                                all_sub_icons.remove(sub_icon)
                                device_group[group_name].add(sub_icon)
                                continue
                            all_sub_icons.remove(sub_icon)
                            group_set.add(sub_icon)
                    if not group_set:
                        continue
                    standard_icons.add(C4Icon(group_set, name=group_name))

                # Separate any remaining 'device' icons from list
                for sub_icon in list(all_sub_icons):
                    if sub_icon.name not in device_names:
                        continue
                    if (parent_dir := sub_icon.path.parent) == new_icon_dir:
                        all_sub_icons.remove(sub_icon)
                        device_group['device'].add(sub_icon)
                    else:
                        all_sub_icons.remove(sub_icon)
                        device_group[str(parent_dir.stem)].add(sub_icon)
                device_icons = [C4Icon(group, name=f'{group_name}\n(device icon)')
                                for group_name, group in device_group.items()]

                # Divide icons into 'standard' and 'extra'
                for key in icon_groups:
                    extra_flag = True
                    if not (group_set := [subicon for subicon in icon_groups[key] if subicon in all_sub_icons]):
                        continue
                    for sub_icon in group_set:
                        if extra_flag and sub_icon.path.parent.name == 'device':
                            extra_flag = False
                    if extra_flag:
                        new_icon = C4Icon(group_set)
                        new_icon.extra = True
                        extras.add(new_icon)
                        continue
                    standard_icons.add(C4Icon(group_set))

                # Mark extra icons as standard if no standard icons found
                if not standard_icons and not device_group and extras:
                    self.extra_icons = 0
                    for icon in extras:
                        icon.extra = False

                output.extend(sorted(standard_icons, key=lambda c4icon: natural_key(c4icon.name)))
                output.extend(sorted(device_icons, key=lambda c4icon: natural_key(c4icon.name)))
                output.extend(sorted(extras, key=lambda c4icon: natural_key(c4icon.name)))
                self.extra_icons = sum(icon.extra for icon in output)
                return output

            def get_icon_groups():
                icon_groups = defaultdict(set)
                proxy_binding_id_dict = defaultdict(str)
                for tag in main.driver_xml.get_tags('proxy'):
                    tag_name = tag.attributes.get('name')
                    if proxybindingid := tag.attributes.get('proxybindingid'):
                        proxy_binding_id_dict[proxybindingid] = tag_name
                    if sm_img_path := tag.attributes.get('small_image'):
                        rel_path = Path(sm_img_path)
                        icon_groups[(tag_name or 'Device Icon', tag.parent)].add(rel_path)
                    if lg_img_path := tag.attributes.get('large_image'):
                        rel_path = Path(lg_img_path)
                        icon_groups[(tag_name or 'Device Icon', tag.parent)].add(rel_path)
                for tag in main.driver_xml.get_tags('Icon'):
                    if 'controller://' not in (tag_value := tag.value):
                        print(f'Could not parse Icon tag value in XML: {tag_value}')
                        continue
                    group_name = tag.parent.attributes.get('id')
                    if not group_name and (parent_tag := tag.get_parent('navigator_display_option')):
                        if proxybindingid := parent_tag.attributes.get('proxybindingid'):
                            if new_group_name := proxy_binding_id_dict.get(proxybindingid):
                                group_name = new_group_name

                    rel_path = tag_value.split('controller://')[1]
                    if 'icons' in rel_path:
                        rel_path = Path('icons', rel_path.split('icons')[1].lstrip('/\\'))
                    elif 'images' in rel_path:
                        rel_path = Path('images', rel_path.split('images')[1].lstrip('/\\'))
                    else:
                        rel_path = Path(rel_path)
                    icon_groups[(group_name or tag.parent.name, tag.parent)].add(rel_path)

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

            img_paths = new_driver_path if main.def_get_all_driver_imgs.get() else (new_icon_dir, new_images_dir)
            if new_icons := get_icons(img_paths):
                self.icons = new_icons
            else:
                abort = True

        # Abort if no valid driver XML or no icons found
        if abort:
            main.root.after(0, self.load_c4z_abort_dialog)  # type: ignore
            shutil.rmtree(new_driver_path, ignore_errors=True)
            main.driver_xml = driver_xml_bak
            return

        # Delete driver folder and replace with new driver
        shutil.rmtree(driver_path, ignore_errors=True)
        new_driver_path.replace(driver_path)
        for c4icon in self.icons:
            c4icon.update_path(driver_path)
        main.undo_history.clear()
        self.current_icon = 0
        self.update_icon()

        # Update C4zPanel entry with driver file path
        self.file_entry_str.set(file_path)
        if not main.driver_selected:  # For first driver loaded
            self.file_entry_field['state'] = 'readonly'
            main.export_panel.export_button['state'] = NORMAL
            main.export_panel.export_as_button['state'] = NORMAL
        main.driver_selected = True

        # Update ExportPanel entry with output filename
        orig_file_path = Path(file_path)
        if not generic:
            main.export_panel.driver_name_var.set(orig_file_path.stem)
        if not main.export_panel.driver_name_var.get():
            main.export_panel.driver_name_var.set('New Driver')

        # Update show extra icons checkbox
        self.show_extra_icons.set(False)
        extra_icon_text = 'show extra icons' if not self.extra_icons else f'show extra ({self.extra_icons})'
        self.show_extra_icons_check.config(text=extra_icon_text)
        self.show_extra_icons_check.config(state='disabled' if not self.extra_icons else 'normal')

        # Update XML variables
        if man_tag := main.driver_xml.get_tag('manufacturer'):
            main.driver_manufac_var.set(man_tag.value)
        if creator_tag := main.driver_xml.get_tag('creator'):
            main.driver_creator_var.set(creator_tag.value)
        if version_tag := main.driver_xml.get_tag('version'):
            main.driver_ver_orig.set(version_tag.value)
            ver_num = re.search(r'\d*', version_tag.value)[0]
            if ver_num:
                main.driver_version_var.set(ver_num)
                ver_num = str(int(ver_num) + 1) if main.export_panel.inc_driver_version.get() else ver_num
                main.driver_version_new_var.set(ver_num)
            else:
                main.driver_version_var.set('0')
                main.driver_version_new_var.set('1')
        if id_tags := main.driver_xml.get_tags('id'):
            main.original_conn_ids = set()
            for id_tag in id_tags:
                with contextlib.suppress(ValueError):
                    if int(id_tag.value) not in main.original_conn_ids:
                        main.original_conn_ids.add(int(id_tag.value))

        # Check Lua file for multi-state
        if not c4is:  # Because load_project handles these updates
            main.multi_state_driver = False
            main.edit.entryconfig(main.states_pos, state=DISABLED)
            if (lua_path := main.instance_temp / 'driver' / 'driver.lua').is_file():
                with open(lua_path, errors='replace', encoding='utf-8') as driver_lua_file:
                    driver_lua = driver_lua_file.read()
                    if main.get_states(driver_lua):
                        main.multi_state_driver = True
                    else:
                        main.multi_state_driver = False
            if main.multi_state_driver:
                main.edit.entryconfig(main.states_pos, state=NORMAL)
            else:
                main.edit.entryconfig(main.states_pos, state=DISABLED)
                if main.states_win:
                    main.states_win.close()

        # Update driver prev/next buttons
        visible_icons = len(self.icons) - (self.extra_icons if not self.show_extra_icons.get() else 0)
        prev_next_button_state = NORMAL if visible_icons > 1 else DISABLED
        self.prev_icon_button['state'] = prev_next_button_state
        self.next_icon_button['state'] = prev_next_button_state
        # Update replacement prev/next buttons
        prev_next_button_state = NORMAL if main.replacement_panel.replacement_icon else DISABLED
        main.replacement_panel.replace_button['state'] = prev_next_button_state
        main.replacement_panel.replace_all_button['state'] = prev_next_button_state
        # Update 'Restore All' button in driver panel
        done = False
        self.restore_all_button['state'] = DISABLED
        for path in list_all_sub_directories(driver_path):
            for item in path.glob('*.bak*'):
                # If any item is not '.xml' and ends with '.bak' + any chars other than '.'
                if not item.name.endswith('.xml.bak') and '.' not in item.name.split('.bak')[-1]:
                    self.restore_all_button['state'] = NORMAL
                    done = True
                    break
            if done:
                break
        self.update_icon()

        # Update connections panel
        if not c4is:  # Because load_project handles these updates
            self.get_connections()
            if main.connections_win:
                main.connections_win.refresh(hard=True, threaded=True)
            if main.states_win:
                main.states_win.refresh()
        if self.sub_icon_win:
            self.sub_icon_win.update_icon()
        main.ask_to_save = False

    def load_c4z(self, file_path=None, generic=False, c4is=None, bypass_ask_save=False, new_thread=True, force=False):
        if not force and self.main.pending_load_save:
            return
        if not bypass_ask_save and self.main.ask_to_save:
            self.main.ask_to_save_dialog(save_dialog_result := StringVar(), on_exit=False)
            self.main.root.wait_variable(save_dialog_result)
            if save_dialog_result.get() not in ('do', 'dont'):
                return
        self.main.pending_load_save = True
        if new_thread:
            threading.Thread(target=self.load_c4z, kwargs={'file_path': file_path, 'generic': generic, 'c4is': c4is,
                                                           'bypass_ask_save': True, 'new_thread': False, 'force': True},
                             daemon=True).start()
            return
        self._load_c4z(file_path=file_path, generic=generic, c4is=c4is)
        self.main.pending_load_save = False

    def drop_in_c4z(self, event):
        if self.main.pending_load_save:
            return
        paths = parse_drop_event(event)
        c4z_path = next((path for path in paths if path.suffix == '.c4z' and path.is_file()), None)
        if c4z_path:
            self.load_c4z(file_path=c4z_path)
        self.main.replacement_panel.process_image(file_path=paths)

    def restore(self, do_all=False):
        if self.main.pending_load_save:
            return
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
        if self.main.pending_load_save:
            return
        self.main.update_undo_history()
        if do_all:
            for icon in self.icons:
                if not icon.replacement_icon and (icon.restore_bak and icon.bak):
                    icon.restore_bak = False
        else:
            self.icons[self.current_icon].restore_bak = False
        self.update_icon()
        self.main.ask_to_save = True

    def toggle_extra_icons(self, *_):
        if not self.main.driver_selected or self.main.pending_load_save:
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

    def inc_icon(self, inc=1, validate=True):
        if not self.main.driver_selected or not inc or self.main.pending_load_save:
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

    def update_icon(self):
        if not (icons := self.icons):
            return
        if self.current_icon < 0:
            raise ValueError('Expected positive icon index')
        if self.current_icon >= len(icons):
            self.current_icon = self.current_icon % len(icons)

        icon_image = icons[self.current_icon].tk_img
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

    def get_connections(self):
        main = self.main

        # Get connections from XML object and update connection entries
        get_all_conn = self.main.def_get_all_connections.get()
        main.connections = [
            Connection(main, cid=int(tag.connection_dict['id'].value),
                       cname=tag.connection_dict['connectionname'].value,
                       ctype=tag.connection_dict['classname'].value, tag=tag, original=True)
            for tag in main.driver_xml.get_tags('connection')
            if tag.connection_dict
            if get_all_conn or tag.connection_dict['classname'].value in valid_connections
        ]
        main.taken_conn_ids = {conn.id: conn.tag for conn in main.connections}
        main.taken_conn_ids |= {id_val: None
                                for tag in main.driver_xml.get_tags('id') if tag.value.isdigit()
                                if (id_val := int(tag.value)) not in main.taken_conn_ids}

        main.connections.append(Connection(main))
        if not (parent_tag := main.driver_xml.get_tag('connections')):
            main.driver_xml.get_tag('devicedata').add_element(
                parent_tag := XMLTag(xml_string='<connections></connections>'))
        parent_tag.add_element(main.connections[-1].tag)

    def right_click_menu(self, event):
        context_menu = Menu(self.main.root, tearoff=0)
        context_menu.add_command(label='View Sub Icons', command=self.toggle_sub_icon_win)
        menu_state = NORMAL if self.icons and not self.main.pending_load_save else DISABLED
        context_menu.entryconfig(0, state=menu_state)
        context_menu.tk_popup(event.x_root, event.y_root)
        context_menu.grab_release()

    def load_c4z_abort_dialog(self):
        def cancel():
            abort_dialog.destroy()

        abort_dialog = Toplevel(self.main.root)
        abort_dialog.title('Failed to load driver')
        abort_dialog.geometry(f'239x70+{self.main.root.winfo_rootx()}+{self.main.root.winfo_rooty()}')
        abort_dialog.protocol('WM_DELETE_WINDOW', cancel)
        abort_dialog.grab_set()
        abort_dialog.focus()
        abort_dialog.transient(self.main.root)
        abort_dialog.resizable(False, False)

        label = Label(abort_dialog, text='The driver failed to load for reasons')
        label.place(relx=0.5, rely=0, y=5, anchor='n')

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
        self.img_bank_lockout_dict = {}
        self.threading_event = threading.Event()
        self.threading_event.set()

        # Labels
        self.panel_label = Label(main.root, text='Replacement Icons', font=(label_font, 15))
        self.panel_label.place(x=150 + self.x, y=-20 + self.y, anchor='n')

        self.replacement_img_label = Label(main.root, image=main.img_blank)
        self.replacement_img_label.place(x=108 + self.x, y=42 + self.y, anchor='n')
        self.replacement_img_label.image = main.img_blank
        self.replacement_img_label.drop_target_register(DND_FILES)
        self.replacement_img_label.dnd_bind('<<Drop>>', self.drag_and_drop_image)
        self.replacement_img_label.bind('<Button-3>', self.right_click_menu)

        x_offset = 61
        for i in range(main.img_bank_size):
            bank_label = Label(main.root, image=main.img_bank_blank)
            bank_label.place(x=31 + self.x + x_offset * i, y=176 + self.y, anchor='nw')
            bank_label.image = main.img_bank_blank
            bank_label.drop_target_register(DND_FILES)
            bank_label.dnd_bind('<<Drop>>', lambda e, bn=i: self.drag_and_drop_image(e, bn))
            bank_label.bind('<Button-1>', lambda e, bn=i: self.select_img_bank(e, bn))
            bank_label.bind('<Button-3>', self.right_click_menu)
            self.img_bank_tk_labels.append(bank_label)

        # Buttons
        self.open_file_button = Button(main.root, text='Open', width=10, command=self.process_image, takefocus=0)
        self.open_file_button.place(x=187 + self.x, y=30 + self.y, anchor='w')

        self.replace_all_button = Button(main.root, text='Replace All', command=self.replace_all, takefocus=0)
        self.replace_all_button.place(x=228 + self.x, y=58 + self.y, anchor='n')
        self.replace_all_button['state'] = DISABLED

        self.replace_button = Button(main.root, text='Replace\nCurrent Icon', command=self.replace_icon, takefocus=0)
        self.replace_button.place(x=228 + self.x, y=91 + self.y, anchor='n')
        self.replace_button['state'] = DISABLED

        self.prev_icon_button = Button(main.root, text='Prev', command=lambda: self.inc_img_bank(inc=0),
                                       width=5, takefocus=0)
        self.prev_icon_button.place(x=180 + self.x, y=146 + self.y)
        self.prev_icon_button['state'] = DISABLED

        self.next_icon_button = Button(main.root, text='Next', command=self.inc_img_bank, width=5, takefocus=0)
        self.next_icon_button['state'] = DISABLED
        self.next_icon_button.place(x=230 + self.x, y=146 + self.y)

        # Entry
        self.file_entry_str = StringVar(value='Select image file...')
        self.file_entry_field = Entry(main.root, width=25, textvariable=self.file_entry_str, takefocus=0)
        self.file_entry_field.place(x=108 + self.x, y=21 + self.y, anchor='n')
        self.file_entry_field.drop_target_register(DND_FILES)
        self.file_entry_field.dnd_bind('<<Drop>>', self.drag_and_drop_image)
        self.file_entry_field['state'] = DISABLED

    def _process_image(self, file_path: Path | str | list | tuple = None, bank_index=None, threaded=False):
        if not threaded and not self.threading_event.is_set():
            return
        if not file_path:
            if bank_index is None:
                for path in filedialog.askopenfilenames(filetypes=[('Image', ' '.join(valid_img_types))]):
                    self._process_image(file_path=path, threaded=threaded)
                return
        elif isinstance(file_path, str):
            file_path = Path(file_path)
        elif isinstance(file_path, tuple) or isinstance(file_path, list):
            for path in file_path:
                if path.is_file():
                    self._process_image(file_path=path, bank_index=bank_index, threaded=threaded)
                    continue
                for directory in list_all_sub_directories(path, include_root_dir=True):
                    for file in directory.iterdir():
                        if file.is_file():
                            self._process_image(file_path=file, bank_index=bank_index, threaded=threaded)
            return
        if file_path and (not file_path.is_file() or file_path.suffix not in valid_img_types):
            print(f'Issue in load_replacement with file_path: {file_path}')
            return

        main = self.main
        existing_replacement = bool(self.replacement_icon)

        # Process image and check if it is already in replacement images folder
        if file_path:
            new_path = main.replacement_icons_dir / file_path.name
            next_num = itertools.count(1)
            while new_path.is_file():
                new_path = main.replacement_icons_dir / f'{file_path.stem}{next(next_num)}{file_path.suffix}'

            try:
                Image.MAX_IMAGE_PIXELS = None  # Temporarily allow very large images to be processed; Trusting user
                with (Image.open(file_path) as img):
                    Image.MAX_IMAGE_PIXELS = max_image_pixels
                    img.draft('RGB', (1024, 1024))
                    img.thumbnail((1024, 1024), Resampling.LANCZOS)
                    img.save(new_path)
                    new_file_size = new_path.stat().st_size
                    # Check if image already in replacement icons directory
                    for cmp_path in main.replacement_icons_dir.iterdir():
                        if cmp_path.stat().st_size != new_file_size:
                            continue
                        if cmp_path == new_path or not filecmp.cmp(cmp_path, new_path):
                            continue
                        # If image already in directory
                        new_path.unlink()
                        # If image is dropped on bank
                        if bank_index is not None:
                            # Set bank index to last image if it is set outside current bank size
                            drop_on_blank = False
                            if bank_index > (cur_bank_size := len(self.img_bank) - 1):
                                drop_on_blank = True
                                bank_index = cur_bank_size
                            # If existing replacement image is dropped onto img_bank
                            if bank_index == -1 or (existing_replacement and self.replacement_icon.path == cmp_path):
                                if not drop_on_blank and bank_index >= 0:
                                    rp_icon = self.replacement_icon
                                    self.replacement_icon = self.img_bank[bank_index]
                                    self.img_bank[bank_index] = rp_icon
                                    self.replacement_img_label.configure(image=self.replacement_icon.tk_icon_lg)
                                    self.replacement_img_label.image = self.replacement_icon.tk_icon_lg
                                else:
                                    self.img_bank.append(self.replacement_icon)
                                    self.replacement_icon = None
                                    self.replacement_img_label.config(image=main.img_blank)
                                    self.replacement_img_label.image = main.img_blank
                                    self.replace_button['state'] = DISABLED
                                    self.replace_all_button['state'] = DISABLED
                                    self.file_entry_str.set('Select image file...')
                                    self.file_entry_field['state'] = DISABLED
                                self.refresh_img_bank()
                                return
                            # If existing image is dropped onto itself
                            if self.img_bank[bank_index].path == cmp_path:
                                return
                            # If existing image is dropped onto another image in img_bank
                            existing_icon = next((icon for icon in self.img_bank if icon.path == cmp_path))
                            existing_index = self.img_bank.index(existing_icon)
                            swap_icon = self.img_bank[bank_index]
                            self.img_bank[bank_index] = existing_icon
                            self.img_bank[existing_index] = swap_icon
                            self.refresh_img_bank()
                            return
                        else:  # If image is dropped on replacement
                            if existing_replacement and self.replacement_icon.path == cmp_path:
                                return
                            existing_icon = next((icon for icon in self.img_bank if icon.path == cmp_path))
                            bank_index = self.img_bank.index(existing_icon)
                            if existing_replacement:
                                rp_icon = self.replacement_icon
                                self.replacement_icon = existing_icon
                                self.img_bank[bank_index] = rp_icon
                            else:  # If dropped on blank replacement
                                self.replacement_icon = self.img_bank.pop(bank_index)
                                self.img_bank_tk_labels[bank_index].configure(image=main.img_bank_blank)
                                self.img_bank_tk_labels[bank_index].image = main.img_bank_blank
                                self.update_buttons()
                            self.replacement_img_label.configure(image=self.replacement_icon.tk_icon_lg)
                            self.replacement_img_label.image = self.replacement_icon.tk_icon_lg
                            self.refresh_img_bank()
                            return

                    new_icon = Icon(new_path, img=img)
            finally:
                Image.MAX_IMAGE_PIXELS = max_image_pixels

            if bank_index is not None:
                self.add_to_img_bank(new_icon, bank_index)
                return

        # If image not found in existing images
        if existing_replacement:
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
            if label_index := len(self.img_bank) < main.img_bank_size:
                self.img_bank_tk_labels[label_index].configure(image=main.img_bank_blank)
                self.img_bank_tk_labels[label_index].image = main.img_bank_blank
            self.refresh_img_bank()

        if file_path:
            self.replacement_icon = new_icon
        else:
            file_path = self.replacement_icon.path

        self.file_entry_str.set(file_path)
        if not existing_replacement:
            self.file_entry_field['state'] = 'readonly'
        self.update_buttons()

        self.replacement_img_label.configure(image=self.replacement_icon.tk_icon_lg)
        self.replacement_img_label.image = self.replacement_icon.tk_icon_lg

        main.replacement_selected = True
        if main.driver_selected:
            main.ask_to_save = True

    def process_image(self, file_path: Path | str | list | tuple = None, bank_index=None, new_thread=True):
        if self.open_file_button.config('relief')[-1] == 'sunken':
            return
        if new_thread:
            threading.Thread(target=self.process_image,
                             kwargs={'file_path': file_path, 'bank_index': bank_index, 'new_thread': False},
                             daemon=True).start()
            return

        if not self.threading_event.is_set():
            self.open_file_button.config(relief='sunken')
        with self.main.thread_lock:
            self.open_file_button.config(relief='raised')
            self.threading_event.clear()
            self._process_image(file_path=file_path, bank_index=bank_index, threaded=True)
            self.threading_event.set()

    def drag_and_drop_image(self, event, bank_num: int | None = None):
        paths = parse_drop_event(event)
        if not paths:
            return
        self.process_image(file_path=paths, bank_index=bank_num)

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

    def select_img_bank(self, event, bank_num: int):
        if not self.threading_event.is_set():
            return
        if not self.img_bank or len(self.img_bank) <= bank_num or not event:
            return
        # Debounce stack selection
        debounce_val = 0.25
        bank_key = f'bank{bank_num}'
        if (last_time := self.img_bank_lockout_dict.get(bank_key)) and time.time() - last_time < debounce_val:
            return
        self.img_bank_lockout_dict[bank_key] = time.time()
        self._process_image(bank_index=bank_num)

    def refresh_img_bank(self):
        for i, img in zip(range(self.main.img_bank_size), self.img_bank):
            self.img_bank_tk_labels[i].configure(image=img.tk_icon_sm)
            self.img_bank_tk_labels[i].image = img.tk_icon_sm

    def inc_img_bank(self, inc=-1):
        if not self.threading_event.is_set():
            return
        if len(self.img_bank) <= self.main.img_bank_size:
            return
        temp = self.img_bank[inc]
        self.img_bank.pop(inc)
        if inc == -1:
            self.img_bank.insert(0, temp)
        else:
            self.img_bank.append(temp)
        self.refresh_img_bank()

    def replace_icon(self, update_undo_history=True, c4_icn_index=None):
        if not self.threading_event.is_set():
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
        if not self.threading_event.is_set():
            return
        self.main.update_undo_history()
        show_extra = self.main.c4z_panel.show_extra_icons.get()
        for i, icon in enumerate(self.main.c4z_panel.icons):
            if icon.extra and not show_extra:
                continue
            self.replace_icon(update_undo_history=False, c4_icn_index=i)

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
        context_menu.entryconfig(0, state=menu_state)
        context_menu.tk_popup(event.x_root, event.y_root)
        context_menu.grab_release()

    def delete_image(self, img_index: int):
        if not -1 <= img_index < self.main.img_bank_size:
            return
        if img_index == -1:
            self.replacement_icon.path.unlink()
            self.replacement_icon = None
            self.replacement_img_label.config(image=self.main.img_blank)
            self.replacement_img_label.image = self.main.img_blank
            self.replace_button['state'] = DISABLED
            self.replace_all_button['state'] = DISABLED
            self.file_entry_str.set('Select image file...')
            self.file_entry_field['state'] = DISABLED
            return

        # Added this because of a bug that I could not reproduce, but seemed to happen from clicking the bank after
        # selecting delete, but before the delete was finished.. which doesn't seem possible, but whatever
        bank_key = f'bank{img_index}'
        if (last_time := self.img_bank_lockout_dict.get(bank_key)) and time.time() - last_time < 0.25:
            return
        self.img_bank_lockout_dict[bank_key] = time.time()

        self.img_bank[img_index].path.unlink()
        self.img_bank.pop(img_index)
        if (label_index := len(self.img_bank)) <= self.main.img_bank_size:
            self.prev_icon_button['state'] = DISABLED
            self.next_icon_button['state'] = DISABLED
        if label_index < self.main.img_bank_size:
            self.img_bank_tk_labels[label_index].configure(image=self.main.img_bank_blank)
            self.img_bank_tk_labels[label_index].image = self.main.img_bank_blank
        self.refresh_img_bank()

    def update_buttons(self):
        replace_button_state = NORMAL if self.main.driver_selected and self.replacement_icon else DISABLED
        next_button_state = NORMAL if len(self.img_bank) > self.main.img_bank_size else DISABLED
        self.replace_button['state'] = replace_button_state
        self.replace_all_button['state'] = replace_button_state
        self.next_icon_button['state'] = next_button_state
        self.prev_icon_button['state'] = next_button_state


class ExportPanel:
    def __init__(self, main: C4IconSwapper):
        # Initialize Export Panel
        self.main = main
        self.x, self.y = (615, -50)
        self.abort = False

        # Labels
        self.panel_label = Label(main.root, text='Export', font=(label_font, 15))
        self.panel_label.place(x=145 + self.x, y=70 + self.y, anchor='n')

        self.driver_name_label = Label(main.root, text='Driver Name:')
        self.driver_name_label.place(x=65 + self.x, y=200 + self.y, anchor='w')

        # Buttons
        self.export_as_button = Button(main.root, text='Export As...', width=20, command=self.do_export, takefocus=0)
        self.export_as_button.place(x=145 + self.x, y=270 + self.y, anchor='n')
        self.export_as_button['state'] = DISABLED

        self.export_button = Button(main.root, text='Quick Export', width=20, command=self.quick_export, takefocus=0)
        self.export_button.place(x=145 + self.x, y=240 + self.y, anchor='n')
        self.export_button['state'] = DISABLED

        # Entry
        self.driver_name_var = StringVar(value='New Driver')
        self.driver_name_var.trace_add('write', self.validate_driver_name)
        self.driver_name_entry = Entry(main.root, width=25, textvariable=self.driver_name_var)
        self.driver_name_entry.place(x=145 + self.x, y=210 + self.y, anchor='n')

        # Checkboxes
        self.use_orig_xml = BooleanVar(value=main.def_use_original_xml.get())
        self.use_orig_xml.trace_add('write', main.toggle_use_original_xml)
        self.use_orig_xml_check = Checkbutton(main.root, text='Use original driver XML',
                                              variable=self.use_orig_xml, takefocus=0)
        self.use_orig_xml_check.place(x=63 + self.x, y=130 + self.y, anchor='w')

        self.include_backups = BooleanVar(value=main.def_include_backup_files.get())
        self.include_backups_check = Checkbutton(main.root, text='Include backup files',
                                                 variable=self.include_backups, takefocus=0)
        self.include_backups_check.place(x=63 + self.x, y=150 + self.y, anchor='w')

        self.inc_driver_version = BooleanVar(value=main.def_inc_driver_version.get())
        self.inc_driver_version.trace_add('write', self.main.update_driver_version)
        self.inc_driver_check = Checkbutton(main.root, text='Increment driver version',
                                            variable=self.inc_driver_version, takefocus=0)
        self.inc_driver_check.place(x=63 + self.x, y=170 + self.y, anchor='w')

    def quick_export(self):
        if self.main.pending_load_save:
            print('TODO: schedule for update after pending_load_save')
            return
        # Check for empty driver info variables
        if self.missing_driver_info_check():
            return
        overwrite_dialog = None
        # Overwrite dialog if file already exists
        file_path = Path(self.main.def_quick_export_dir.get(blank_gives_cwd=True)) / f'{self.driver_name_var.get()}.c4z'
        if file_path.is_file():
            def confirm_overwrite():
                self.abort = False
                file_path.unlink()
                overwrite_dialog.destroy()

            def abort():
                self.abort = True
                overwrite_dialog.destroy()
            overwrite_dialog = Toplevel(self.main.root)
            overwrite_dialog.title('Overwrite')
            overwrite_dialog.geometry(f'239x70+{self.main.root.winfo_rootx() + self.x}+{self.main.root.winfo_rooty()}')
            overwrite_dialog.protocol('WM_DELETE_WINDOW', abort)
            overwrite_dialog.grab_set()
            overwrite_dialog.focus()
            overwrite_dialog.transient(self.main.root)
            overwrite_dialog.resizable(False, False)

            confirm_label = Label(overwrite_dialog, text='Would you like to overwrite the existing file?')
            confirm_label.grid(row=0, column=0, columnspan=2, pady=5)

            yes_button = Button(overwrite_dialog, text='Yes', width='10', command=confirm_overwrite)
            yes_button.grid(row=2, column=0, sticky='e', padx=5)

            no_button = Button(overwrite_dialog, text='No', width='10', command=abort)
            no_button.grid(row=2, column=1, sticky='w', padx=5)
        self.do_export(quick_export=file_path, overwrite_dialog=overwrite_dialog)

    def do_export(self, quick_export=None, overwrite_dialog=None):
        if self.main.pending_load_save:
            print('TODO: schedule for update after pending_load_save')
            return
        # Wait for confirm overwrite dialog
        if overwrite_dialog and isinstance(overwrite_dialog, Toplevel):
            self.main.root.wait_window(overwrite_dialog)
        if self.abort:
            self.abort = False
            return

        main = self.main
        driver_xml = main.driver_xml

        # Validate driver name
        driver_name = re_valid_chars.sub('', self.driver_name_var.get())
        main.export_panel.driver_name_var.set(driver_name)
        if not driver_name:
            self.driver_name_entry['background'] = 'pink'
            main.counter = 7
            main.root.after(150, main.blink_driver_name_entry)  # type: ignore
            return

        # Check for empty driver info variables
        if self.missing_driver_info_check():
            return

        # Backup driver files
        driver_bak_folder = main.instance_temp / 'driver_bak'
        shutil.rmtree(driver_bak_folder, ignore_errors=True)
        shutil.copytree(main.instance_temp / 'driver', driver_bak_folder)

        # Update XML with user data
        if not self.use_orig_xml.get():
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
                    invalid_states_dialog = Toplevel(main.root)
                    if single_invalid_state:
                        invalid_states_dialog.title('Invalid State Found')
                        label_text = 'Cannot Export: Invalid state label'
                    else:
                        invalid_states_dialog.title('Invalid States Found')
                        label_text = 'Cannot Export: Invalid state labels'
                    invalid_states_dialog.geometry(
                        f'239x70+{main.root.winfo_rootx() + self.x}+{main.root.winfo_rooty()}')
                    invalid_states_dialog.grab_set()
                    invalid_states_dialog.focus()
                    invalid_states_dialog.transient(main.root)
                    invalid_states_dialog.resizable(False, False)
                    confirm_label = Label(invalid_states_dialog, text=label_text, justify='center')
                    confirm_label.pack()
                    exit_button = Button(invalid_states_dialog, text='Cancel', width='10',
                                         command=invalid_states_dialog.destroy, justify='center')
                    exit_button.pack(pady=10)
                if self.abort:
                    self.abort = False
                    return

                # Update state names in Lua file
                state_name_changes = {}
                if (lua_path := main.instance_temp / 'driver' / 'driver.lua').is_file():
                    for state in main.states:
                        if state.original_name != state.name:
                            state_name_changes[state.original_name] = state.name

                    # Read Lua file
                    modified_lua_lines = []
                    with open(lua_path, errors='replace', encoding='utf-8') as driver_lua_file:
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
                    lua_path.replace(lua_path.with_suffix('.bak'))
                    with open(lua_path, 'w', errors='replace', encoding='utf-8') as driver_lua_file:
                        driver_lua_file.writelines(modified_lua_lines)

                # Do multi-state related changes in XML
                if state_name_changes:
                    for orig_name in state_name_changes:
                        orig_lower = orig_name.lower()
                        new_name = state_name_changes[orig_name]
                        new_lower = new_name.lower()
                        for item_tag in driver_xml.get_tags('item'):
                            if orig_name == item_tag.value:
                                item_tag.set_value(new_name)
                                break
                            if orig_lower == item_tag.value:
                                item_tag.set_value(new_lower)
                                break
                        for name_tag in driver_xml.get_tags('name'):
                            if orig_name == name_tag.value or name_tag.value.endswith(orig_name):
                                name_tag.set_value(name_tag.value.replace(orig_name, new_name))
                                break
                            if orig_lower == name_tag.value or name_tag.value.endswith(orig_lower):
                                name_tag.set_value(name_tag.value.replace(orig_lower, new_lower))
                                break
                        for description_tag in driver_xml.get_tags('description'):
                            if f'{orig_name} ' in description_tag.value:
                                description_tag.set_value(description_tag.value.replace(orig_name, new_name))
                                break
                            if f'{orig_lower} ' in description_tag.value:
                                description_tag.set_value(description_tag.value.replace(orig_lower, new_lower))
                                break
                        for state_tag in driver_xml.get_tags('state'):
                            if state_tag.attributes['id']:
                                if state_tag.attributes['id'] == orig_name:
                                    state_tag.attributes['id'] = new_name
                                    break
                                if state_tag.attributes['id'] == orig_lower:
                                    state_tag.attributes['id'] = new_lower
                                    break

            # XML Changes
            driver_xml.get_tag('name').set_value(driver_name)
            modified_datestamp = str(datetime.now().strftime('%m/%d/%Y %H:%M'))
            driver_xml.get_tag('version').set_value(new_ver := main.driver_version_new_var.get())
            main.driver_version_var.set(new_ver)
            driver_xml.get_tag('modified').set_value(modified_datestamp)
            driver_xml.get_tag('creator').set_value(main.driver_creator_new_var.get())
            driver_xml.get_tag('manufacturer').set_value(main.driver_manufac_new_var.get())
            for attribute in driver_xml.get_tag('proxy').attributes:
                if attribute[0] == 'name':
                    attribute[1] = driver_name
            for icon_tag in driver_xml.get_tags('Icon'):
                # Not OS specific; related to controller directories
                if result := re.search('driver/(.*)/icons', icon_tag.value):
                    result = result[1]
                    icon_tag.set_value(icon_tag.value.replace(result, driver_name))

            # Update connections XML data
            for conn in main.connections:
                if conn.original:
                    continue
                conn.tag.get_tag('connectionname').set_value(conn.name_entry_var.get())
                conn.tag.get_tag('classname').set_value(conn_type := conn.type_var.get())
                if 'IN' in conn_type:
                    conn.tag.get_tag('consumer').set_value('True')
                else:
                    conn.tag.get_tag('consumer').set_value('False')
                if conn_type == 'IR_OUT':
                    conn.tag.add_element(XMLTag(xml_string='<facing>6</facing>'), index=2)
                    conn.tag.add_element(XMLTag(xml_string='<audiosource>False</audiosource>'), index=-3)
                    conn.tag.add_element(XMLTag(xml_string='<videosource>False</videosource>'), index=-3)

            # Backup XML file and write new XML
            xml_path = main.instance_temp / 'driver' / 'driver.xml'
            xml_path.replace(xml_path.with_suffix('.bak'))
            with open(xml_path, 'w', errors='replace', encoding='utf-8') as out_file:
                out_file.writelines(driver_xml.get_lines())

            # Removed the added XML tags from IR_OUT connections
            for conn in main.connections:
                if not conn.original and conn.type_var.get() == 'IR_OUT':
                    conn.tag.remove_element('facing')
                    conn.tag.remove_element('audiosource')
                    conn.tag.remove_element('videosource')

        # Make icon changes
        bak_folder = main.instance_temp / 'bak_files'
        shutil.rmtree(bak_folder, ignore_errors=True)
        bak_folder.mkdir()
        include_bak = self.include_backups.get()
        for icon in main.c4z_panel.icons:
            if icon.replacement_icon:
                with Image.open(icon.replacement_icon.path) as rp_icon:
                    for sub_icon in icon.icons:
                        if include_bak:
                            sub_icon.bak_path = sub_icon.path.with_suffix('.bak')
                            shutil.copy(sub_icon.path, sub_icon.bak_path)
                        out_icon = rp_icon.resize(sub_icon.size, Resampling.LANCZOS)
                        out_icon.save(sub_icon.path)
            elif icon.restore_bak and icon.bak:
                for sub_icon in icon.icons:
                    if not sub_icon.bak_path:
                        continue
                    if include_bak:
                        temp_bak_path = bak_folder / sub_icon.name
                        sub_icon.path.replace(temp_bak_path)
                        sub_icon.bak_path.replace(sub_icon.path)
                        temp_bak_path.replace(sub_icon.bak_path)
                    else:
                        sub_icon.bak_path.replace(sub_icon.path)
        shutil.rmtree(bak_folder)

        # Save As Dialog and export file
        out_file_path = None
        if quick_export:
            out_file_path = quick_export
        else:
            out_file_str = filedialog.asksaveasfilename(initialfile=f'{driver_name}.c4z',
                                                        filetypes=[('Control4 Drivers', '*.c4z'), ('All Files', '*.*')],
                                                        defaultextension='.c4z')
            if out_file_str:
                out_file_path = Path(out_file_str)
                out_file_path.unlink(missing_ok=True)

        if not out_file_path:
            return

        driver_folder = self.main.instance_temp / 'driver'
        # Delete all .bak files if not included
        if not self.include_backups.get():
            for directory in list_all_sub_directories(driver_folder, include_root_dir=True):
                for path in directory.iterdir():
                    if re.search(r'\.bak[^.]*$', path.name) and path.is_file():
                        path.unlink()

        # Create .c4z file
        shutil.make_archive(str(driver_folder), 'zip', driver_folder)
        zip_path = driver_folder.with_suffix('.zip')
        zip_path.replace(out_file_path)

        # Increment driver version if applicable
        if self.inc_driver_version.get() and not self.use_orig_xml.get():
            main.driver_version_new_var.set(str(int(main.driver_version_new_var.get()) + 1))

        # Restore original driver folder
        shutil.rmtree(main.instance_temp / 'driver')
        driver_bak_folder.replace(main.instance_temp / 'driver')

    def validate_driver_name(self, *_):
        driver_name_cmp = re_valid_chars.sub('', driver_name := self.driver_name_var.get())

        if str_diff := len(driver_name) - len(driver_name_cmp):
            cursor_pos = self.driver_name_entry.index(INSERT)
            self.driver_name_entry.icursor(cursor_pos - str_diff)
            self.driver_name_var.set(driver_name_cmp)
            return

        self.main.ask_to_save = True

    def missing_driver_info_check(self):
        def open_driver_info():
            missing_driver_info_dialog.destroy()
            main.open_edit_win(main.driver_info_win, 'driver')
        main = self.main
        if not all([main.driver_version_new_var.get(), main.driver_manufac_new_var.get(),
                    main.driver_creator_new_var.get()]):
            missing_driver_info_dialog = Toplevel(main.root)
            missing_driver_info_dialog.title('Missing Driver Information')
            label_text = 'Cannot Export: Missing driver info'
            missing_driver_info_dialog.geometry(f'239x70+{main.root.winfo_rootx() + self.x}+{main.root.winfo_rooty()}')
            missing_driver_info_dialog.grab_set()
            missing_driver_info_dialog.focus()
            missing_driver_info_dialog.transient(main.root)
            missing_driver_info_dialog.resizable(False, False)
            confirm_label = Label(missing_driver_info_dialog, text=label_text, justify='center')
            confirm_label.pack()
            exit_button = Button(missing_driver_info_dialog, text='Cancel', width='10',
                                 command=open_driver_info, justify='center')
            exit_button.pack(pady=10)
            return True
        return False


class C4IS:
    version = 2

    def __init__(self, main: C4IconSwapper):
        if not isinstance(main, C4IconSwapper):
            raise TypeError(f'Expected type: {C4IconSwapper.__name__}')
        # Root class
        self.version = 2
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
        self.states = [{'original_name': state.original_name, 'name_var': state.name}
                       for state in main.states]

        # Connection Panel
        self.connections = [{'id': conn.id, 'original': conn.original, 'delete': conn.delete, 'tag': conn.tag,
                             'type': conn.type_var.get(), 'name': conn.name_entry_var.get(), 'state': conn.enabled}
                            for conn in main.connections]

        # Export Panel
        self.driver_name_var = main.export_panel.driver_name_var.get()
        self.inc_driver_version = main.export_panel.inc_driver_version.get()
        self.include_backups = main.export_panel.include_backups.get()

        # C4z Panel
        if main.driver_selected:
            driver_path = main.instance_temp / 'driver.zip'
            shutil.make_archive(str(driver_path.with_suffix('')), 'zip', driver_path.with_suffix(''))
            with open(driver_path, 'rb') as driver_zip:
                self.driver_zip = driver_zip.read()
            driver_path.unlink()

        # Replacement Panel
        if main.replacement_panel.replacement_icon:
            with open(main.replacement_panel.replacement_icon.path, 'rb') as img:
                self.replacement = img.read()
        else:
            self.replacement = None
        self.img_bank = [open(img.path, 'rb').read() for img in main.replacement_panel.img_bank]

    def __setstate__(self, state):
        if 'version' not in state:
            state['version'] = 1
            for conn in state.get('connections', []):
                if 'tags' in conn:
                    conn['tag'] = conn.pop('tags')[0]
            if state['replacement']:
                state['replacement'].save((buf := io.BytesIO()), format='png')
                state['replacement'] = buf.getvalue()
            state['img_bank'] = [
                (buf := io.BytesIO(), img.save(buf, format='png'), img.close(), buf.getvalue())[3]
                for img in state.pop('img_stack')
            ]
        self.__dict__.update(state)


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
