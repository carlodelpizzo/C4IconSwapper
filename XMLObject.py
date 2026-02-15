from __future__ import annotations
import re
import warnings
from pathlib import Path
from collections import defaultdict, deque

char_escapes = {'<': '&lt;', '>': '&gt;', '&': '&amp;'}
re_attributes = re.compile(r'([\w:]+)\s*=\s*([\'"])(.*?)\2')


# sub_tag will ignore all tags until it finds a tag with that name, then make that tag the root
def parse_xml(xml_path: str | Path = None, xml_string='', sub_tag='') -> list[XMLTag]:
    if not xml_path and not xml_string:
        return []
    if xml_path:
        with open(xml_path, errors='replace', encoding='utf-8') as xml_file:
            xml_string = xml_file.read()

    tags = []
    tag_stack = deque()
    tag_start = None
    string_tag = ''
    attributes = {}
    last_pos = -1
    nested_comments = 0
    nested_cdata = 0
    nested_skip = False
    sub_tag_found = False
    data = ''

    def add_append_tag(new_tag):
        nonlocal attributes
        nonlocal tag_start
        nonlocal string_tag
        if isinstance(new_tag, str):
            if not string_tag:
                return
            new_tag = XMLTag(name=string_tag, is_string=True)
            string_tag = ''
        else:
            attributes = {}
            tag_start = None
        if tag_stack:
            tag_stack[-1].add_element(new_tag)
        else:
            tags.append(new_tag)

    def sub_tag_root_search():
        nonlocal attributes
        nonlocal data
        nonlocal tag_start
        nonlocal sub_tag_found
        nonlocal data_no_attr

        self_closing = False
        attributes = {}
        if ' ' in data:
            if data[:data.index(' ')] != sub_tag:
                tag_start = None
                return None
            if data.endswith('/'):
                self_closing = True
            data_no_attr = re_attributes.sub('', data)
            if '=' in data_no_attr:  # In case '>' is in attributes
                tag_start = None
                return None
            attributes = {k: (v, q) for k, q, v in re_attributes.findall(data)}
            data = data[:data.index(' ')]
        elif data.endswith('/'):
            if (data := data[:-1]) != sub_tag:
                tag_start = None
                return None
            if '<' in data or '>' in data:
                warnings.warn('< or > found in self-closing tag', SyntaxWarning)
                return []
            self_closing = True
        elif data != sub_tag:
            tag_start = None
            return None
        if self_closing:
            return [XMLTag(name=data, attributes=attributes, is_self_closing=True)]
        tag_stack.append(XMLTag(name=data, attributes=attributes))
        attributes = {}
        sub_tag_found = True
        tag_start = None
        return None

    # Begin Parsing
    for i in (char_index for char_index, char in enumerate(xml_string) if char in ('<', '>')):
        if xml_string[i] == '<':
            if tag_start:
                continue  # Continue if '<' found inside comment or attribute
            if not nested_comments and not nested_cdata:
                string_tag = xml_string[last_pos + 1:i].strip()
            tag_start = i
            continue
        if nested_comments:
            nested_comments -= 1
            if nested_comments:
                continue
        if tag_start is None:
            continue
        last_pos = i

        try:
            data = xml_string[tag_start + 1:i]
        except TypeError:
            warnings.warn('Generic issue with XML syntax', SyntaxWarning)
            return []

        # Handle sub_tag search
        if sub_tag and not sub_tag_found:
            if self_closing_sub_tag := sub_tag_root_search():
                return self_closing_sub_tag
            continue

        # Handle CDATA tags
        if data.startswith('![CDATA['):
            if not data.endswith(']]'):
                if not nested_cdata:
                    nested_cdata += 1
                continue
            if data.count('<![CDATA[') + 1 != nested_cdata:
                nested_cdata += 1
                continue
            add_append_tag(string_tag)
            add_append_tag(XMLTag(name=f'<{data}>', is_cdata=True))
            nested_cdata = 0
            continue

        # Handle comments
        if data.startswith('!--'):
            if not nested_skip:
                if nested_comments := data.count('!--') - 1:
                    nested_skip = True
                    continue
            elif data.count('!--') - 1 != data.count('-->'):
                warnings.warn('Issue with nested comments', SyntaxWarning)
                return []
            nested_skip = False
            if not data.endswith('--'):
                continue
            add_append_tag(string_tag)
            add_append_tag(XMLTag(name=data[3:-2], is_comment=True))
            continue

        # Parse tag attributes
        if ' ' in data:
            data_no_attr = re_attributes.sub('', data)
            if '=' in data_no_attr:  # In case '>' is in attributes
                continue
            attributes = {k: (v, q) for k, q, v in re_attributes.findall(data)}

        # Handle prolog
        if data.startswith('?'):
            if not data.endswith('?'):
                continue
            add_append_tag(string_tag)
            add_append_tag(XMLTag(name=data[1:-1], attributes=attributes, is_prolog=True))
            continue

        # Handle self-closing tags
        if data.endswith('/'):
            data = data[:-1] if ' ' not in data else data[:data.index(' ')]
            if '<' in data or '>' in data:
                warnings.warn('< or > found in self-closing tag', SyntaxWarning)
                return []
            add_append_tag(string_tag)
            add_append_tag(XMLTag(name=data, attributes=attributes, is_self_closing=True))
            continue

        stripped_data = data[:data.index(' ')] if ' ' in data else data

        # Handle closing tag; Pull off stack
        if tag_stack and data.startswith('/') and tag_stack[-1].name == stripped_data[1:]:
            add_append_tag(string_tag)
            if len(tag_stack) > 1:
                tag_stack[-2].add_element(tag_stack.pop())
            else:
                tags.append(tag_stack.pop())
                if sub_tag and sub_tag_found and tags[-1].name == sub_tag:
                    return tags
            tag_start = None
            continue

        # Push tag on stack to wait for closing tag
        add_append_tag(string_tag)
        tag_stack.append(XMLTag(name=stripped_data, attributes=attributes))
        attributes = {}
        tag_start = None

    if tag_stack:
        warnings.warn('Could not find pair for each tag', SyntaxWarning)
        return []
    return tags


# Can only have one root tag
class XMLTag:
    name: str | None
    parent: XMLTag | None
    attributes: dict[str, str]
    attr_q: dict[str, str]
    elements: list[XMLTag]
    is_prolog: bool
    is_comment: bool
    is_CDATA: bool
    is_string: bool
    is_self_closing: bool
    hide: bool

    def __init__(self, name: str = None, elements: list = None, attributes: dict = None, parent: XMLTag = None,
                 xml_path: str | Path = None, xml_string: str = None, is_comment=False, is_self_closing=False,
                 is_prolog=False, is_cdata=False, is_string=False, sub_tag=''):
        self.init_success = False
        first_tag = None
        # Constructs an XMLTag object based on the first tag in data if XML path/data is passed in
        if xml_path or xml_string:
            tag_list = parse_xml(xml_path=xml_path, xml_string=xml_string, sub_tag=sub_tag)
            if not tag_list:
                warnings.warn(f'Excepted {self.__class__.__name__} in list; Received Empty list',
                              RuntimeWarning)
                return
            first_tag = tag_list[0]
            if not isinstance(first_tag, XMLTag):
                warnings.warn(f'Expected type: {self.__class__.__name__}; '
                              f'Received type: {first_tag.__class__.__name__}', RuntimeWarning)
                return

        self.name = name if not first_tag else first_tag.name
        self.parent = parent if not first_tag else first_tag.parent
        if attributes:
            self.attributes = {}
            self.attr_q = {}
            for k, (v, q) in attributes.items():
                self.attributes[k] = v
                self.attr_q[k] = q
        else:
            self.attributes = {} if not first_tag else first_tag.attributes.copy()
            self.attr_q = {} if not first_tag else first_tag.attr_q.copy()
        self.elements = (elements or []) if not first_tag else first_tag.elements
        self.is_prolog = is_prolog if not first_tag else first_tag.is_prolog
        self.is_comment = is_comment if not first_tag else first_tag.is_comment
        self.is_CDATA = is_cdata if not first_tag else first_tag.is_CDATA
        self.is_string = is_string if not first_tag else first_tag.is_string
        self.is_self_closing = is_self_closing if not first_tag else first_tag.is_self_closing
        self.hide = False if not first_tag else first_tag.hide
        self.init_success = True

    @property
    def value(self) -> str:
        if self.is_string:
            return self.name
        return '' if not self.init_success else next((el.value for el in self.elements if el.is_string), '')

    @property
    def children(self) -> list[XMLTag]:
        return [element for element in self.elements if not element.is_string]

    @property
    def descendants(self) -> list[XMLTag]:
        output = []
        for child in self.elements:
            if child.is_string:
                continue
            output.append(child)
            output.extend(child.descendants)
        return output

    def get_value(self) -> str:
        return self.value

    def set_value(self, new_value: str):
        if self.is_string:
            self.name = new_value
            return
        value_set = False
        for tag in self.elements:
            if tag.is_string:
                tag.name = new_value
                value_set = True
                break
        if not value_set:
            self.elements.append(XMLTag(name=new_value, is_string=True, parent=self))

    def add_element(self, element, index=None):
        if not isinstance(element, XMLTag):
            raise TypeError(f'Expected type: {XMLTag.__name__}, Received type: {type(element).__name__}')
        if index:
            self.elements.insert(index, element)
        else:
            self.elements.append(element)
        element.parent = self

    def get_lines(self, indent='', use_esc_chars=False, as_string=False) -> list[str] | str:
        if not self.init_success or self.hide:
            return '' if as_string else []
        if self.is_comment:
            comment = f'{indent}<!--{self.name}-->'
            return comment if as_string else [comment]
        if self.is_CDATA:
            output = f'{indent}{self.name}'
            return output if as_string else [output]
        if self.is_string:
            output = f'{indent}{self.name}'
            if use_esc_chars:
                output = f'{indent}{re.sub(r"[<>&]", lambda m: char_escapes[m.group(0)], self.name)}'
            return output if as_string else [output]
        if self.is_prolog:
            prolog = f'{indent}<?{self.name}?>'
            return prolog if as_string else [prolog]

        if use_esc_chars:
            attributes = ' '.join([
                f'{k}={self.attr_q[k]}{re.sub(r"[<>&]", lambda m: char_escapes[m.group(0)], v)}{self.attr_q[k]}'
                for k, v in self.attributes.items()
            ])
        else:
            attributes = ' '.join([f'{k}={self.attr_q[k]}{v}{self.attr_q[k]}' for k, v in self.attributes.items()])

        output = []
        if self.is_self_closing:
            if attributes:
                output.append(f'{indent}<{self.name} {attributes} />')
            else:
                output.append(f'{indent}<{self.name} />')
            return ''.join(output) if as_string else output
        else:
            output.append(f'{indent}<{self.name} {attributes}'.rstrip())
            if not self.elements:
                output[-1] += '>'
            else:
                output[-1] += f'>\n'
        for element in self.elements:
            if isinstance(element, str):
                if len(self.elements) == 1:
                    if use_esc_chars:
                        output.append(re.sub(r"[<>&]", lambda m: char_escapes[m.group(0)], element))
                    else:
                        output.append(element)
                    continue
                if element:
                    if use_esc_chars:
                        output.append(
                            f'{indent}\t{re.sub(r"[<>&]", lambda m: char_escapes[m.group(0)], element)}\n')
                    else:
                        output.append(f'{indent}\t{element}\n')
                continue
            if element.hide:
                continue
            output.extend(element.get_lines(indent=f'\t{indent}', use_esc_chars=use_esc_chars))
            output[-1] += '\n'

        if not self.elements:
            output.append(f'</{self.name}>')
        else:
            output.append(f'{indent}</{self.name}>')
        return ''.join(output) if as_string else output

    def get_tags(self, name: str) -> list[XMLTag]:
        if not self.init_success or self.is_string:
            return []
        output = [self] if name == self.name else []
        for element in self.elements:
            output.extend(element.get_tags(name))
        return output

    def get_tags_dict(self, name_set: set[str]) -> dict[str, list[XMLTag]]:
        if not self.init_success:
            return {}
        output_dict = defaultdict(list)
        for element in self.elements:
            if element.is_string:
                continue
            if element.name in name_set:
                name_set.remove(element.name)
                output_dict[element.name].append(element)
            if element_tag_dict := element.get_tags_dict(name_set):
                name_set.difference_update(element_tag_dict)
                for key, tags in element_tag_dict.items():
                    output_dict[key].extend(tags)
            if not name_set:
                break
        return output_dict

    def get_tag(self, name: str, include_self=True) -> XMLTag | None:
        if not self.init_success or self.is_string:
            return None
        if include_self and name == self.name:
            return self

        for element in self.elements:
            if element.name == name:
                return element

        # Check deeper if not found in children
        for element in self.elements:
            if matching_tag := element.get_tag(name, include_self=False):
                return matching_tag
        return None

    def get_parents(self, parents=None) -> list[XMLTag]:
        if not self.parent:
            return [] if not parents else parents
        if not parents:
            parents = []
        parents.append(self.parent)
        return self.parent.get_parents(parents)

    def get_parent(self, parent_name: str) -> XMLTag | None:
        if not self.parent:
            return None
        if self.parent.name == parent_name:
            return self.parent
        return self.parent.get_parent(parent_name)

    def __bool__(self):
        return self.init_success


# Allows multiple root tags
class XMLObject:
    def __init__(self, xml_path: str | Path = None, xml_string=''):
        self.tags = parse_xml(xml_path=xml_path, xml_string=xml_string)
        self.root = next((tag for tag in self.tags if not (tag.is_prolog or tag.is_comment or tag.is_CDATA)), None)

    def get_lines(self, use_esc_chars=False, as_string=False) -> list[str] | str:
        output = []
        if len(self.tags) == 1:
            output = self.tags[0].get_lines(use_esc_chars=use_esc_chars)
            return ''.join(output) if as_string else output
        for i, tag in enumerate(self.tags):
            output.extend(tag.get_lines(use_esc_chars=use_esc_chars))
            if i != len(self.tags) - 1:
                output[-1] += '\n'
        return ''.join(output) if as_string else output

    def get_tags(self, name: str) -> list[XMLTag]:
        output = []
        for tag in self.tags:
            output.extend(tag.get_tags(name))
        return output

    def get_tag(self, name: str) -> XMLTag | None:
        for tag in self.tags:
            if output := tag.get_tag(name):
                return output
        return None

    def __bool__(self):
        return bool(self.tags)
