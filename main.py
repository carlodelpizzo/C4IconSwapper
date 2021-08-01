import tkinter as tk
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import os
import shutil

root = tk.Tk()
root.geometry("290x390")
root.title("Control4 Icon Swapper")
root.resizable(False, False)

entry_font = 'Helvetica'

global icon_objects
global current_icon
global replacement_image

driver_selected = False
replacement_selected = False


class Icon:
    def __init__(self, index: int, icon_family: str, icon_names: list, icon_paths: list):
        self.index = index
        self.icon_family = icon_family
        self.icon_sizes = []
        self.icon_names = icon_names
        self.icon_paths = icon_paths

        for name in icon_names:
            temp_size = ''
            for l in range(len(name)):
                if name[l] == '.':
                    break
                elif name[l] == '_':
                    temp_size += name[l + 1]
                elif temp_size != '' and name[l - 1] != '_':
                    temp_size += name[l]
            self.icon_sizes.append(int(temp_size))

    def show_icon(self):
        global current_icon
        global icon_objects

        if os.path.isfile(self.icon_paths[0] + '.orig'):
            restore_button['state'] = ACTIVE
        else:
            restore_button['state'] = DISABLED
        icon_image = Image.open(self.icon_paths[0])

        icon = icon_image.resize((70, 70), Image.ANTIALIAS)
        icon = ImageTk.PhotoImage(icon)

        icon_image_label2 = tk.Label(image=icon)
        icon_image_label2.image = icon
        icon_image_label2.grid(row=2, column=1)

        if len(icon_objects) == 1:
            prev_icon_button['state'] = DISABLED
            next_icon_button['state'] = DISABLED
        else:
            prev_icon_button['state'] = ACTIVE
            next_icon_button['state'] = ACTIVE


def upload_c4z():
    global icon_objects
    global current_icon
    global driver_selected
    global replacement_selected

    icon_objects = []
    filename = filedialog.askopenfilename(filetypes=[("Control4 Drivers", "*.c4z")])
    icon_dir = temp_dir + '/driver/www/icons/device'

    file_entry_field['state'] = NORMAL
    file_entry_field.delete(0, 'end')

    if os.path.isdir(temp_dir + '/driver'):
        shutil.rmtree(temp_dir + '/driver')

    shutil.unpack_archive(filename, temp_dir + '/driver', 'zip')

    if os.path.isdir(icon_dir):
        icons_list = os.listdir(icon_dir)
        icon_string = ''
        icon_families = []
        icon_indexes = []
        for i in range(len(icons_list)):
            for letter in icons_list[i]:
                if letter != '_':
                    icon_string += letter
                else:
                    if icon_string not in icon_families:
                        icon_families.append(icon_string)
                        icon_indexes.append(i)
                    icon_string = ''
                    break
        icon_indexes.append(len(icons_list) + 1)
        for i in range(len(icon_families)):
            children_names = []
            children_paths = []
            for j in range(icon_indexes[i], icon_indexes[i + 1] - 1):
                children_names.append(icons_list[j])
                children_paths.append(icon_dir + '/' + icons_list[j])

            icon_objects.append(Icon(i, icon_families[i], children_names, children_paths))
        file_entry_field.insert(0, filename)

        icon_objects[0].show_icon()
        current_icon = 1
        icon_label.config(text='icon: ' + str(current_icon) + ' of ' + str(len(icon_objects)))
        icon_name_label.config(text='icon name: ' + icon_objects[current_icon - 1].icon_names[0])

        driver_selected = True
    else:
        file_entry_field.insert(0, 'no valid icons found')
        driver_selected = False

        temp_button2 = Button(root, text='', width=9, height=4, bg='white')
        temp_button2.grid(row=2, column=1)
        temp_button2['state'] = DISABLED

        # driver_icon2 = ImageTk.PhotoImage(Image.open('white_70.png'))
        # driver_icon_label2 = tk.Label(image=driver_icon2)
        # driver_icon_label2.image = driver_icon2
        # driver_icon_label2.grid(row=2, column=1)

    file_entry_field['state'] = DISABLED
    if driver_selected:
        if replacement_selected:
            replace_icon_button['state'] = ACTIVE
        export_button['state'] = ACTIVE


def upload_replacement():
    global icon_objects
    global current_icon
    global replacement_image
    global replacement_selected

    replacement_entry_field['state'] = NORMAL
    replacement_entry_field.delete(0, 'end')
    filename = filedialog.askopenfilename(filetypes=[("Image", "*.png"), ("Image", "*.jpg"), ("Image", "*.gif"),
                                                     ("Image", "*.jpeg"), ("Image", "*.tiff"), ("Image", "*.bmp")])
    replacement_entry_field.insert(0, filename)
    replacement_entry_field['state'] = DISABLED

    replacement_image = Image.open(filename)

    new_image = replacement_image.resize((70, 70))
    new_image = ImageTk.PhotoImage(new_image)

    icon_image_label2 = tk.Label(image=new_image)
    icon_image_label2.image = new_image
    icon_image_label2.grid(row=8, column=1)

    if driver_selected:
        replace_icon_button['state'] = ACTIVE
    replacement_selected = True


def replace_icon():
    global icon_objects
    global current_icon
    global temp_dir

    replacement_dir = temp_dir + '/replacement_icon'
    if not os.path.isdir(replacement_dir):
        os.mkdir(replacement_dir)

    replacement_icon2 = Image.open(replacement_entry_field.get())
    for i in range(len(icon_objects[current_icon - 1].icon_sizes)):
        new_icon = replacement_icon2.resize((icon_objects[current_icon - 1].icon_sizes[i],
                                            icon_objects[current_icon - 1].icon_sizes[i]))
        new_path = replacement_dir + '/' + icon_objects[current_icon - 1].icon_family + '_' + \
            str(icon_objects[current_icon - 1].icon_sizes[i]) + '.png'
        new_icon.save(new_path)

    replacement_dir = temp_dir + '/replacement_icon/'
    icon_dir = temp_dir + '/driver/www/icons/device/'

    for icon in os.listdir(replacement_dir):
        if not os.path.isfile(icon_dir + icon + '.orig'):
            os.rename(icon_dir + icon, icon_dir + icon + '.orig')
        shutil.copy(replacement_dir + icon, icon_dir)
        os.remove(replacement_dir + icon)

    icon_objects[current_icon - 1].show_icon()

    restore_button['state'] = ACTIVE


def restore_icon():
    global icon_objects
    global current_icon

    if os.path.isfile(icon_objects[current_icon - 1].icon_paths[0] + '.orig'):
        for i in range(len(icon_objects[current_icon - 1].icon_paths)):
            shutil.copy(icon_objects[current_icon - 1].icon_paths[i] + '.orig',
                        icon_objects[current_icon - 1].icon_paths[i])
            os.remove(icon_objects[current_icon - 1].icon_paths[i] + '.orig')

    icon_objects[current_icon - 1].show_icon()
    restore_button['state'] = DISABLED


def next_icon():
    global current_icon
    global icon_objects

    if current_icon + 1 <= len(icon_objects):
        icon_objects[current_icon].show_icon()
        current_icon += 1
    else:
        icon_objects[0].show_icon()
        current_icon = 1

    icon_label.config(text='icon: ' + str(current_icon) + ' of ' + str(len(icon_objects)))
    icon_name_label.config(text='icon name: ' + icon_objects[current_icon - 1].icon_names[0])


def prev_icon():
    global current_icon
    global icon_objects

    if current_icon - 1 >= 1:
        current_icon -= 1
        icon_objects[current_icon - 1].show_icon()
    else:
        icon_objects[len(icon_objects) - 1].show_icon()
        current_icon = len(icon_objects)

    icon_label.config(text='icon: ' + str(current_icon) + ' of ' + str(len(icon_objects)))
    icon_name_label.config(text='icon name: ' + icon_objects[current_icon - 1].icon_names[0])


# noinspection PyGlobalUndefined
def export_driver():
    global pop

    def confirm_write():
        if os.path.isfile(cur_dir + '/new_driver.c4z'):
            os.remove(cur_dir + '/new_driver.c4z')
        if os.path.isfile(cur_dir + '/new_driver.zip'):
            os.remove(cur_dir + '/new_driver.zip')
        shutil.make_archive('new_driver', 'zip', temp_dir + '/driver')
        base_path = os.path.splitext(cur_dir + '/new_driver.zip')[0]
        os.rename(cur_dir + '/new_driver.zip', base_path + '.c4z')

        pop.destroy()

    if os.path.isfile(cur_dir + '/new_driver.c4z') or os.path.isfile(cur_dir + '/new_driver.zip'):
        pop = Toplevel(root)
        pop.title('Overwrite')
        pop.geometry('239x50')

        confirm_label = Label(pop, text='Would you like to overwrite the existing file?')
        confirm_label.grid(row=0, column=0, columnspan=2)

        no_button = tk.Button(pop, text='No', width='10', command=pop.destroy)
        no_button.grid(row=1, column=0)

        yes_button = tk.Button(pop, text='Yes', width='10', command=confirm_write)
        yes_button.grid(row=1, column=1)
    else:
        shutil.make_archive('new_driver', 'zip', temp_dir + '/driver')
        base = os.path.splitext(cur_dir + '/new_driver.zip')[0]
        os.rename(cur_dir + '/new_driver.zip', base + '.c4z')


cur_dir = os.getcwd()
temp_dir = os.getcwd() + '/temp'

if not os.path.isdir(temp_dir):
    os.mkdir(temp_dir)


temp_button = Button(root, text='', width=9, height=4, bg='white')
temp_button.grid(row=2, column=1)
temp_button['state'] = DISABLED

temp_button3 = Button(root, text='', width=9, height=4, bg='white')
temp_button3.grid(row=8, column=1)
temp_button3['state'] = DISABLED

file_entry_title = tk.Label(root, text='Select C4 Driver:')
file_entry_title.grid(row=0, column=1)

file_entry_field = tk.Entry(root, text='', width=30)
file_entry_field.grid(row=1, column=0, columnspan=2, sticky='E')
file_entry_field['state'] = DISABLED

open_file_button = tk.Button(root, text='Open', command=upload_c4z)
open_file_button.grid(row=1, column=2, sticky='W')

restore_button = tk.Button(root, text='Restore Original Icon', command=restore_icon)
restore_button.grid(row=2, column=1, columnspan=2, sticky='E', padx=5)
restore_button['state'] = DISABLED

prev_icon_button = tk.Button(root, text='Prev', command=prev_icon)
prev_icon_button.grid(row=3, column=1, sticky='W')
prev_icon_button['state'] = DISABLED

icon_label = tk.Label(root, text='icon: 0 of 0')
icon_label.grid(row=3, column=1)

icon_name_label = tk.Label(root, text='icon name:')
icon_name_label.grid(row=4, column=1, columnspan=3, sticky='W')

next_icon_button = tk.Button(root, text='Next', command=next_icon)
next_icon_button.grid(row=3, column=1, sticky='E')
next_icon_button['state'] = DISABLED

divider_label = tk.Label(root, text='---------------------------------------------------------')
divider_label.grid(row=5, column=0, columnspan=3, sticky='E')

replacement_entry_title = tk.Label(root, text='Select Replacement Image:')
replacement_entry_title.grid(row=6, column=1)

replacement_entry_field = tk.Entry(root, text='', width=30)
replacement_entry_field.grid(row=7, column=0, columnspan=2, sticky='E')
replacement_entry_field['state'] = DISABLED

open_file2_button = tk.Button(root, text='Open', command=upload_replacement)
open_file2_button.grid(row=7, column=2, sticky='W')

replace_icon_button = tk.Button(root, text='Replace current icon', command=replace_icon)
replace_icon_button.grid(row=9, column=1)
replace_icon_button['state'] = DISABLED

divider_label2 = tk.Label(root, text='---------------------------------------------------------')
divider_label2.grid(row=10, column=0, columnspan=3, sticky='E')

export_button = tk.Button(root, text='Export Control4 Driver', width=35, command=export_driver)
export_button.grid(row=11, column=0, columnspan=3, padx=5)
export_button['state'] = DISABLED

root.mainloop()

shutil.rmtree(temp_dir)
