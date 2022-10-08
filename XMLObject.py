def get_xml_data(xml_path=None, xml_string=None, tag_indexes=None):
    if xml_path:
        with open(xml_path, errors='ignore') as xml_file:
            xml_lines = xml_file.readlines()
        xml_string = ''.join(xml_lines)
        xml_string = xml_string.replace('\t', '')
        tag_indexes = [i for i in range(len(xml_string)) if xml_string[i] == '<' or xml_string[i] == '>']
        if len(tag_indexes) % 2 != 0:
            print('Error: Invalid xml file')
            return

    name, value, attributes, children, children_indexes, grandchildren, output = '', '', '', [], [], [], []
    child, child_attributes, child_value = '', '', ''
    check_for_value, check_child_value = False, False
    duplicate_name_count, duplicate_child_count = 0, 0
    comment_start = None
    for i, tag_index in enumerate(tag_indexes):
        if comment_start:
            if not xml_string[comment_start:tag_index + 1].endswith('-->'):
                continue
            comment = xml_string[comment_start + 1: tag_index]
            if child == '':
                children.append([comment, '', '', []])
            else:
                grandchildren.append([comment, '', '', []])
            comment_start = None
        if i % 2 != 0:
            continue
        tag_name = xml_string[tag_index + 1:tag_indexes[i + 1]]
        if tag_name.startswith('!--'):
            comment_start = tag_index
            continue
        if check_for_value:
            check_for_value = False
            if tag_name == '/' + name:
                value = xml_string[tag_indexes[i - 1] + 1:tag_index]
                output.append([name, value, attributes, children])
                name, value, attributes, children = '', '', '', []
                continue
        if name != '' and tag_name == name:
            duplicate_name_count += 1
        if child != '' and tag_name == child:
            duplicate_child_count += 1
        if name == '':
            if tag_name.startswith('?'):
                continue
            if tag_name.endswith('/'):
                output.append([tag_name, '', '', []])
                continue
            name = tag_name
            if ' ' in name:
                attributes = name[name.index(' '):]
                name = name[:name.index(' ')]
            check_for_value = True
        elif tag_name != '/' + name:
            if check_child_value:
                check_child_value = False
                if tag_name == '/' + child:
                    child_value = xml_string[tag_indexes[i - 1] + 1:tag_index]
                    children.append([child, child_value, child_attributes, []])
                    child, child_value, child_attributes = '', '', ''
                    continue
            if child == '':
                if tag_name.endswith('/'):
                    children.append([tag_name, '', '', []])
                    continue
                child = tag_name
                if ' ' in child:
                    child_attributes = child[child.index(' '):]
                    child = child[:child.index(' ')]
                check_child_value = True
            elif tag_name == '/' + child:
                if duplicate_child_count > 0:
                    duplicate_child_count -= 1
                    continue
                grandchildren.extend(get_xml_data(xml_string=xml_string, tag_indexes=children_indexes))
                children_indexes = []
                children.append([child, child_value, child_attributes, grandchildren])
                child, child_value, child_attributes, grandchildren = '', '', '', []
            else:
                children_indexes.extend([tag_index, tag_indexes[i + 1]])
        elif tag_name == '/' + name:
            if duplicate_name_count > 0:
                duplicate_name_count -= 1
                continue
            output.append([name, value, attributes, children])
            name, value, attributes, children = '', '', '', []

    return output


# xml_data = ['name', 'value', 'attributes', [children]]; Initialize with path to xml file
class XMLObject:
    def __init__(self, xml_path=None, xml_data=None, parents=None):
        if xml_path:
            xml_data = get_xml_data(xml_path)
        if not xml_data:
            raise ValueError
        if type(xml_data) is not list:
            raise TypeError
        self.top_level = False
        self.children = []
        self.name, self.value = '', ''
        if len(xml_data) == 4 and type(xml_data[0]) is str and type(xml_data[1]) is str and \
                type(xml_data[2]) is str and type(xml_data[3]) is list:
            self.name = xml_data[0]
            self.value = xml_data[1]
        elif len(xml_data) > 1:
            self.top_level = True
            for tag in xml_data:
                self.children.append(XMLObject(xml_data=tag))
        elif len(xml_data) == 1 and type(xml_data[0]) is list:
            xml_data = xml_data[0]
            self.name = xml_data[0]
            self.value = xml_data[1]
        while self.value.endswith('\n'):
            self.value = self.value[:-1]
        self.parents = []
        parents_for_children = []
        if parents:
            self.parents.extend(parents)
            parents_for_children.extend(parents)
        if xml_data[3]:
            parents_for_children.append(self)
        self.parameters = []  # [[param_name, param_value], ...]
        self.restore_data = []  # [name, value, parameters, parents, children, self_closed, top_level, delete]
        self.self_closed, self.comment, self.delete = False, False, False
        if self.top_level:
            return
        if self.name != '' and self.name.startswith('!'):
            self.comment = True
            return
        if self.name.endswith('/'):
            self.name = self.name[:-1]
            self.self_closed = True

        # Parse parameters (attributes)
        if type(xml_data[2]) is str and xml_data[2] != '':
            if xml_data[2].endswith('/'):
                self.self_closed = True
            param_name, param_value, get_name, get_value, inside_attribute = '', '', False, False, False
            for char in xml_data[2]:
                if char == ' ' and not inside_attribute:
                    continue
                if get_value:
                    if char == '"' or char == "'":
                        if param_value == '':
                            inside_attribute = True
                            continue
                        inside_attribute = False
                        self.parameters.append([param_name, param_value])
                        param_name, param_value, get_value = '', '', False
                        continue
                    param_value += char
                    continue
                if get_name:
                    if char == '=':
                        get_value, get_name = True, False
                        continue
                    param_name += char
                    continue
                if char != ' ':
                    get_name = True
                    param_name += char

        # Make children
        for child in xml_data[3]:
            self.children.append(XMLObject(xml_data=child, parents=parents_for_children))

    def get_lines(self, layer=0, first_call=True):
        if self.delete:
            return []
        lines = []
        if self.top_level:
            for child in self.children:
                lines.extend(child.get_lines(first_call=False))
            return lines
        tabs = ''
        for _ in range(layer):
            tabs += '\t'
        self.name = self.name.replace('\n', ''.join(['\n', tabs]))
        line = ''.join([tabs, '<', self.name])
        if self.comment:
            return [''.join([line, '>\n'])]

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

        if not line.endswith('\n'):
            line = ''.join([line, '\n'])
        lines.append(line)

        for child in self.children:
            lines.extend(child.get_lines(layer=layer+1, first_call=False))

        if not self.self_closed:
            lines.append(tabs + '</' + self.name + '>\n')
        if first_call:
            if lines[-1].endswith('\n'):
                lines[-1] = lines[-1][:-1]
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
            matching_tags.extend(child_tags)
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
            matching_tags.extend(child_tags)
        if not matching_tags:
            return None
        return matching_tags

    def set_restore_point(self):
        self.restore_data = [self.name, self.value, self.parameters, self.parents,
                             self.children, self.self_closed, self.top_level, self.delete]
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
        self.top_level = self.restore_data[6]
        self.delete = self.restore_data[7]
        self.restore_data = []
        for child in self.children:
            child.restore()
