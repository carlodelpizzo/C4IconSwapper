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

    name, value, parameters, children, children_indexes, output, comment_start = '', '', '', [], [], [], None
    duplicate_name_counter = 0
    for i, tag_index in enumerate(tag_indexes):
        if comment_start:
            if not xml_string[comment_start:tag_index + 1].endswith('-->'):
                continue
            children_indexes.extend([comment_start, tag_index])
            comment_start = None
        if i % 2 != 0:
            continue
        tag = xml_string[tag_index:tag_indexes[i + 1] + 1]
        tag_name = xml_string[tag_index + 1:tag_indexes[i + 1]]
        if name == '':
            if tag_name.startswith('?'):
                continue
            if tag_name.endswith('/'):
                output.append([tag_name, '', '', []])
                continue
            if tag.startswith('<!--'):
                if not tag.endswith('-->'):
                    comment_start = tag_index
                else:
                    output.append([tag_name, '', '', []])
                continue
            name = tag_name
            if ' ' in name:
                parameters = name[name.index(' '):]
                name = name[:name.index(' ')]
        elif name != tag_name and '/' + name != tag_name:
            children_indexes.extend([tag_index, tag_indexes[i + 1]])
        elif name == tag_name:
            duplicate_name_counter += 1
            children_indexes.extend([tag_index, tag_indexes[i + 1]])
        elif '/' + name == tag_name:
            if duplicate_name_counter > 0:
                duplicate_name_counter -= 1
                children_indexes.extend([tag_index, tag_indexes[i + 1]])
                continue
            if len(children_indexes) == 0:
                value = xml_string[tag_indexes[i - 1] + 1:tag_index]
            else:
                children = get_xml_data(tag_indexes=children_indexes, xml_string=xml_string)
            output.append([name, value, parameters, children])
            name, value, parameters, children = '', '', '', []
            children_indexes = []
        else:
            print(''.join(['skipped: ', tag, '||', name, '||', tag_name]))

    if name == '' and children_indexes:
        for i, tag_index in enumerate(children_indexes):
            if i % 2 != 0:
                continue
            name = xml_string[tag_index + 1:children_indexes[i + 1]]
            output.append([name, value, parameters, children])

    return output


# xml_data = ['tag_name', 'tag_value', 'tag_attributes', [children]]; Initialize with path to xml file
class XMLObject:
    def __init__(self, xml_path=None, xml_data=None, parents=None):
        if xml_path:
            xml_data = get_xml_data(xml_path)
        if not xml_data:
            print('Error: No xml data', xml_data)
            return
        self.top_level = False
        self.children = []
        self.name, self.value = '', ''
        if type(xml_data) is list:
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
        else:
            print('Error: Invalid xml data type')
            return
        while self.value.endswith('\n'):
            self.value = self.value[:-1]
        self.parents = []
        parents_for_children = []
        if parents:
            self.parents, parents_for_children = parents, parents
        parents_for_children.append(self)
        self.parameters = []  # [[param_name, param_value], ...]
        self.restore_data = []  # [name, value, parameters, parents, children, self_closed, top_level, delete]
        self.self_closed, self.comment, self.delete = False, False, False
        if self.top_level:
            return
        if self.name != '' and self.name[0] == '!':
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
