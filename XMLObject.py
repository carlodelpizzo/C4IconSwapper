

def get_xml_data(xml_path=None, xml_string=None):
    new_line_string = '**NL**'
    if xml_path:
        with open(xml_path, errors='ignore') as xml_file:
            xml_lines = xml_file.readlines()

        xml_string = ''
        for line in xml_lines:
            new_line = line.replace('\n', new_line_string)
            new_line = new_line.replace('\t', '')
            xml_string += new_line

    name = ''
    parameters = ''
    value = ''
    children = []
    write_name = False
    check_for_close = False
    hold_tag = False
    get_params = False
    get_value = False
    comment = False
    update_no_param = True
    running_string = ''
    held_tag = ''
    held_tag_no_param = ''
    ignore_subs = []
    for char in xml_string:
        running_string += char
        if comment:
            if char == '>':
                comment = False
            continue
        if get_value:
            if char == '<':
                get_value = False
                hold_tag = True
                continue
            value += char
            continue
        if get_params:
            if char == '>':
                if parameters[-1] == '/':
                    break
                get_params = False
                get_value = True
                continue
            parameters += char
            continue
        if check_for_close:
            if hold_tag:
                if char == '!' or char == '?':
                    comment = True
                    hold_tag = False
                    update_no_param = True
                    continue
                if char == '>' or char == ' ':
                    if '/' in held_tag and held_tag.replace('/', '') == name:
                        break
                    if len(ignore_subs) != 0:
                        if '/' in held_tag_no_param and ignore_subs[-1] == held_tag_no_param.replace('/', ''):
                            ignore_subs.pop(-1)
                            held_tag = ''
                            held_tag_no_param = ''
                            hold_tag = False
                            update_no_param = True
                            continue
                if char == '>':
                    if ('/' not in held_tag_no_param or held_tag[-1] == '/') and len(ignore_subs) == 0:
                        if '/' not in held_tag:
                            ignore_subs.append(held_tag_no_param)
                        temp = get_xml_data(xml_string='<' + held_tag + '>' + xml_string.replace(running_string, ''))
                        children.append(temp)
                    held_tag = ''
                    held_tag_no_param = ''
                    hold_tag = False
                    update_no_param = True
                    continue
                if char == ' ':
                    update_no_param = False
                if update_no_param:
                    held_tag_no_param += char
                held_tag += char
                continue
            if char == '<':
                hold_tag = True
                continue
            continue
        if write_name:
            if char == '!':
                comment = True
                write_name = False
                continue
            if char == '>' or char == ' ':
                if name[-1] == '/':
                    break
                get_value = True
                write_name = False
                check_for_close = True
                if char == ' ':
                    get_params = True
                    get_value = False
                continue
            name += char
            continue
        if char == '<':
            write_name = True
            continue
    name = name.replace(new_line_string, '')
    parameters = parameters.replace(new_line_string, '')
    value = value.replace(new_line_string, '\n')
    if value == '\n':
        value = ''
    if value.endswith('\n'):
        value = value[:-2]

    return [name, value, parameters, children]


# xml_data = ['tag_name', 'tag_value', [tag_attributes], [children]]; Initialize with path to xml file
class XMLObject:
    def __init__(self, xml_path=None, xml_data=None, parents=None):
        if xml_path:
            xml_data = get_xml_data(xml_path)

        self.parents = []
        new_parents = []
        if parents:
            self.parents = parents
            for parent in parents:
                new_parents.append(parent)
        new_parents.append(self)
        self.children = []
        self.name = xml_data[0]
        self.value = xml_data[1]
        self.parameters = []  # [[param_name, param_value], ...]
        self.self_closed = False
        self.delete = False
        self.restore_data = []  # [name, value, parameters, parents, children, self_closed, delete]
        if '/' in self.name:
            self.name = self.name[:-1]
            self.self_closed = True

        param_name = ''
        param_value = ''
        get_name = False
        get_value = False
        # Parse parameters (attributes)
        for char in xml_data[2]:
            if char == ' ':
                continue
            if get_value:
                if char == '"' or char == "'":
                    if param_value == '':
                        continue
                    get_value = False
                    self.parameters.append([param_name, param_value])
                    param_name = ''
                    param_value = ''
                    continue
                param_value += char
                continue
            if get_name:
                if char == '=':
                    get_value = True
                    get_name = False
                    continue
                param_name += char
                continue
            if char != ' ':
                get_name = True
                param_name += char
        if len(xml_data[2]) != 0 and xml_data[2][-1] == '/':
            self.self_closed = True

        # Make children
        for child in xml_data[3]:
            self.children.append(XMLObject(xml_data=child, parents=new_parents))

    def get_lines(self, layer=0):
        if self.delete:
            return []
        lines = []
        line = ''
        tabs = ''
        for _ in range(layer):
            tabs += '\t'
        line += tabs + '<' + self.name

        if len(self.parameters) != 0:
            line += ' '
            for param in self.parameters[:-1]:
                line += param[0] + '="' + param[1] + '" '
            line += self.parameters[-1][0] + '="' + self.parameters[-1][1] + '"'

        if self.self_closed:
            line += '/'
        line += '>' + self.value

        if len(self.children) == 0:
            if self.self_closed or '\n' in self.value:
                line += '\n'
            lines.append(line)
            if not self.self_closed:
                if '\n' not in self.value:
                    line = '</' + self.name + '>\n'
                else:
                    line = tabs + '</' + self.name + '>\n'
                lines.append(line)
            return lines

        lines.append(line + '\n')

        for child in self.children:
            child_lines = child.get_lines(layer=layer+1)
            for line in child_lines:
                lines.append(line)

        if not self.self_closed:
            lines.append(tabs + '</' + self.name + '>\n')
        return lines

    def get_tag(self, tag_name: str):
        matching_tags = []
        for child in self.children:
            if tag_name in child.name:
                matching_tags.append(child)
        for child in self.children:
            child_tags = child.get_tag(tag_name)
            if child_tags is None:
                continue
            for child_tag in child_tags:
                matching_tags.append(child_tag)
        if not matching_tags:
            return None
        return matching_tags

    def get_tag_by_value(self, value: str):
        matching_tags = []
        for child in self.children:
            if value in child.value:
                matching_tags.append(child)
        for child in self.children:
            child_tags = child.get_tag_by_value(value)
            if child_tags is None:
                continue
            for child_tag in child_tags:
                matching_tags.append(child_tag)
        if not matching_tags:
            return None
        return matching_tags

    def set_restore_point(self):
        self.restore_data = [self.name, self.value, self.parameters, self.parents,
                             self.children, self.self_closed, self.delete]
        for child in self.children:
            child.set_restore_point()

    def restore(self):
        if not self.restore_data:
            return
        self.name = self.restore_data[0]
        self.value = self.restore_data[1]
        self.parameters = self.restore_data[2]
        self.parents = self.restore_data[3]
        self.children = self.restore_data[4]
        self.self_closed = self.restore_data[5]
        self.delete = self.restore_data[6]
        self.restore_data = []
        for child in self.children:
            child.restore()
