import copy
from collections import deque


def parse_xml(xml_path: str = None, xml_string: str = None):
    if not xml_path and not xml_string:
        return []
    if xml_path:
        with open(xml_path, errors='ignore') as xml_file:
            xml_string = xml_file.read()

    tags = []
    comments = []
    tag_stack = deque()
    tag_start = None
    tag_end = None
    attributes = {}

    # Begin Parsing
    for i in (i for i, char in enumerate(xml_string) if char in ('<', '>')):
        if xml_string[i] == '<':
            if tag_start:
                continue  # Continue if '<' found inside comment
            tag_start = i
            continue
        data = xml_string[tag_start + 1:i]

        # Identify comment
        if data.startswith('!--'):
            if not data.endswith('--'):
                continue
            comments.append(XMLTag(name=data[3:-2], is_comment=True))
            tag_start = None
            continue

        # Identify prolog
        if data.startswith('?') and data.endswith('?'):
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=data[1:-1], parent=tag_stack[-1], indent=len(tag_stack),
                                                     is_prolog=True, comments=comments))
            else:
                tags.append(XMLTag(name=data[1:-1], is_prolog=True, comments=comments))
            comments = []
            tag_start = None
            continue

        # Parse tag attributes
        if ' ' in data:
            read_att = False
            read_val = False
            att = ''
            val_i = None
            for di, char in enumerate(data):
                if read_val:
                    if char == '"':
                        if not val_i:
                            val_i = di + 1
                            continue
                        attributes[att] = data[val_i:di]
                        val_i = None
                        att = ''
                        read_val = False
                    continue
                if char == ' ':
                    read_att = True
                    continue
                if read_att:
                    if char == '=':
                        read_val = True
                        continue
                    att += char

        # Handle self-closing tags
        if data.endswith('/'):
            if ' ' in data:
                data = data[:data.index(' ')]
            else:
                data = data[:-1]
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=data, attributes=attributes, is_self_closing=True,
                                                     indent=len(tag_stack), parent=tag_stack[-1],
                                                     comments=comments))
                attributes = {}
            else:
                tags.append(XMLTag(name=data, attributes=attributes, is_self_closing=True, comments=comments))
            comments = []
            tag_start = None
            continue

        if ' ' in data:
            data = data[:data.index(' ')]

        # Handle closing tag, Pull off stack
        if tag_stack and tag_stack[-1].name == data[1:]:
            # Add closing tag to XMLTag
            if tag_end:
                tag_stack[-1].elements.append(xml_string[tag_end:tag_start].lstrip().rstrip())
                tag_end = None

            # Add comments to XMLTag
            if comments:
                pop_list = []
                for element in tag_stack[-1].elements:
                    for comment in comments:
                        if type(element) is str and comment.get_lines().rstrip().lstrip() in element:
                            pop_list.append(comments.index(comment))
                for x in sorted(pop_list, reverse=True):
                    comments.pop(x)
                if comments:
                    tag_stack[-1].closing_comments = comments
                    comments = []

            # Append XMLTag to parent or to XMLObject
            temp_tag = tag_stack.pop()
            if tag_stack:
                temp_tag.parent = tag_stack[-1]
                tag_stack[-1].elements.append(temp_tag)
            else:
                tags.append(temp_tag)
            tag_start = None
            continue

        # Push tag on stack to wait for closing tag
        tag_stack.append(XMLTag(name=data, attributes=attributes, comments=comments, indent=len(tag_stack)))
        tag_end = i + 1
        attributes = {}
        comments = []
        tag_start = None

    return tags


class XMLTag:
    def __init__(self, name: str = None, elements: list = None, attributes: dict = None, parent=None, indent=0,
                 comments: list = None, closing_comments: list = None, xml_path: str = None, xml_string: str = None,
                 is_comment=False, is_self_closing=False, is_prolog=False):
        # Constructs an XMLTag object based on the first tag in data if XML path/data is passed in
        if xml_path or xml_string:
            first_tag = parse_xml(xml_path=xml_path, xml_string=xml_string)[0]
            if not first_tag:
                raise ValueError
            if type(first_tag) is not type(self):
                raise TypeError
            self.name = first_tag.name
            self.elements = first_tag.elements
            self.attributes = first_tag.attributes
            self.parent = first_tag.parent  # should always be None
            self.indent = first_tag.indent
            self.comments = first_tag.comments
            self.closing_comments = first_tag.closing_comments
            self.is_comment = first_tag.is_comment
            self.is_self_closing = first_tag.is_self_closing
            self.is_prolog = first_tag.is_prolog
            self.delete = first_tag.delete
            del first_tag
            return
        self.name = name
        self.elements = [] if not elements else elements
        self.attributes = {} if not attributes else attributes
        self.parent = parent
        self.indent = indent
        self.comments = comments if comments else []
        self.closing_comments = closing_comments if closing_comments else []
        self.is_comment = is_comment
        self.is_self_closing = is_self_closing
        self.is_prolog = is_prolog
        self.delete = False

    def get_lines(self):
        if self.delete:
            return ''
        if self.is_comment:
            return f'<!--{self.name}-->\n'
        if self.is_prolog:
            return f'<?{self.name}?>\n'

        attributes = ''

        for attribute in self.attributes:
            attributes += f'{attribute}="{self.attributes[attribute]}" '

        indent = '\t' * self.indent
        output = ''

        if self.comments:
            for comment in self.comments:
                output += f'{indent}{comment.get_lines().rstrip()}\n'
        if self.is_self_closing:
            output += f'{indent}<{self.name} {attributes}'
            return f'{output[:-1]}/>\n'
        else:
            output += f'{indent}<{self.name} {attributes}'
            output = output[:-1]
            if len(self.elements) <= 1 and type(self.elements[0]) is str and '\n' not in self.elements[0]:
                output += '>'
            else:
                output += f'>\n'
        for element in self.elements:
            if type(element) is str:
                if len(self.elements) == 1:
                    output += element
                    continue
                if element:
                    output += f'{indent}\t{element}\n'
                continue
            if element.delete:
                continue
            output += f'{element.get_lines().rstrip()}\n'
        if self.closing_comments:
            for comment in self.closing_comments:
                output += f'{indent}{comment.get_lines().rstrip()}\n'

        if len(self.elements) <= 1 and type(self.elements[0]) is str:
            if '\n' in self.elements[0]:
                output += f'\n{indent}</{self.name}>'
            else:
                output += f'</{self.name}>'
        else:
            output += f'{indent}</{self.name}>\n'
        return output

    def get(self, name: str):
        output = []
        if name == self.name:
            output.append(self)
        for element in self.elements:
            if type(element) is XMLTag:
                if element.get(name):
                    output.extend(element.get(name))
        return output

    def value(self):
        for element in self.elements:
            if type(element) is str:
                return element
        return ''

    def set_value(self, new_value: str):
        for i, element in enumerate(self.elements):
            if type(element) is str:
                self.elements[i] = new_value
                break

    def add_element(self, element, index=None):
        if type(element) is type(self):
            element.update_indent(self.indent + 1)
        elif type(element) is not str:
            raise TypeError
        if index:
            self.elements.insert(index, element)
        else:
            self.elements.append(element)

    def update_indent(self, new_indent: int):
        self.indent = new_indent
        for tag in self.elements:
            if type(tag) is type(self):
                tag.update_indent(self.indent + 1)

    def get_parents(self, parents=None):
        if not self.parent:
            return [] if not parents else parents
        if not parents:
            parents = []
        parents.append(self.parent)
        return self.parent.get_parents(parents)


class XMLObject:
    def __init__(self, xml_path: str = None, xml_string: str = None):
        self.restore_point = None
        self.tags = parse_xml(xml_path=xml_path, xml_string=xml_string)

    def get_lines(self):
        return ''.join([s.get_lines() for s in self.tags]).rstrip()

    def get_tags(self, name: str):
        output = []
        for tag in self.tags:
            if tag.get(name):
                output.extend(tag.get(name))
        return output

    def set_restore_point(self):
        self.restore_point = copy.deepcopy(self)

    def restore(self):
        if not self.restore:
            return
        self.tags = self.restore_point.tags
