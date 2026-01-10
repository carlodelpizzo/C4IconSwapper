import copy
import re
from collections import deque


char_escapes = {'<': '&lt;', '>': '&gt;', '&': '&amp;'}


def parse_xml(xml_path: str = '', xml_string: str = ''):
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
    check_comment_in_value = None
    attributes = {}
    nested_comments = 0
    nested_skip = False
    special_tag = False

    # Begin Parsing
    for i in (x for x, char in enumerate(xml_string) if char in ('<', '>')):
        if xml_string[i] == '<':
            if tag_start:
                continue  # Continue if '<' found inside comment or attribute
            tag_start = i
            continue
        if nested_comments:
            nested_comments -= 1
            if nested_comments:
                continue
        if tag_start is None:
            continue

        try:
            data = xml_string[tag_start + 1:i]
        except TypeError:
            raise SyntaxError('Generic issue with XML syntax')

        if special_tag and (special_data := xml_string[special_tag:tag_start].rstrip()).endswith(']>'):
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=special_data, parent=tag_stack[-1], comments=comments,
                                                     is_special=True))
            else:
                tags.append(XMLTag(name=special_data, comments=comments, is_special=True))
            comments = []
            special_tag = None
            tag_end = None

        # Identify comment
        if data.startswith('!--'):
            if tag_end and '4in' in data:
                pass
            if not nested_skip:
                if nested_comments := data.count('!--') - 1:
                    nested_skip = True
                    continue
            elif data.count('!--') - 1 != data.count('-->'):
                raise SyntaxError('Issue with nested comments')
            nested_skip = False
            if not data.endswith('--'):
                continue
            comments.append(XMLTag(name=data[3:-2], is_comment=True))
            if tag_end:
                check_comment_in_value = tag_end
            tag_start = None
            tag_end = None
            continue

        # Identify special tags
        if data.startswith('!'):
            special_tag = tag_start
            tag_start = None
            continue

        # Identify prolog
        if data.startswith('?'):
            if not data.endswith('?'):
                continue
            attr_pairs = re.findall(r'([\w:]+)="([^"]*)"', data)
            if len(attr_pairs) != len(re.findall(r'(\w+)="([^"]*)', data)):
                continue
            attributes = {k: v for k, v in attr_pairs}
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=data[1:-1], parent=tag_stack[-1], attributes=attributes,
                                                     is_prolog=True, comments=comments))
            else:
                tags.append(XMLTag(name=data[1:-1], attributes=attributes, is_prolog=True, comments=comments))
            comments = []
            attributes = {}
            tag_start = None
            tag_end = None
            continue

        # Parse tag attributes
        if ' ' in data:
            attr_pairs = re.findall(r'([\w:]+)="([^"]*)"', data)
            if len(attr_pairs) != len(re.findall(r'(\w+)="([^"]*)', data)):
                continue
            attributes = {k: v for k, v in attr_pairs}

        # Handle self-closing tags
        if data.endswith('/'):
            if ' ' in data:
                data = data[:data.index(' ')]
            else:
                data = data[:-1]
            if '<' in data or '>' in data:
                raise SyntaxError('< or > found in self-closing tag')
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=data, attributes=attributes, is_self_closing=True,
                                                     parent=tag_stack[-1],
                                                     comments=comments))
                attributes = {}
            else:
                tags.append(XMLTag(name=data, attributes=attributes, is_self_closing=True, comments=comments))
            comments = []
            tag_start = None
            tag_end = None
            continue

        stripped_data = data[:data.index(' ')] if ' ' in data else data

        # Handle closing tag, Pull off stack
        if tag_stack and stripped_data.startswith('/') and tag_stack[-1].name == stripped_data[1:]:
            # Add comments as string element if inside a tag which has no tag elements
            if check_comment_in_value and comments:
                str_element = xml_string[check_comment_in_value:tag_start].strip()
                if str_element:
                    tag_stack[-1].elements.append(str_element)
                comments = []
                check_comment_in_value = None
            # Add string element
            elif tag_end:
                str_element = xml_string[tag_end:tag_start].strip()
                if str_element:
                    tag_stack[-1].elements.append(str_element)

            # Add comments to XMLTag
            if comments:
                pop_list = []
                for element in tag_stack[-1].elements:
                    for comment in comments:
                        if type(element) is str and f'<!--{comment.name}-->' in element:
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
            tag_end = None
            continue

        if tag_end and data.endswith(f'/{tag_stack[-1].name}'):
            str_element = f'{xml_string[tag_end:tag_start]}<{data[:data.rfind("<")]}'
            if str_element:
                tag_stack[-1].elements.append(str_element)
            temp_tag = tag_stack.pop()
            if tag_stack:
                temp_tag.parent = tag_stack[-1]
                tag_stack[-1].elements.append(temp_tag)
            else:
                tags.append(temp_tag)
            tag_start = None
            tag_end = None
            continue
        if tag_end and xml_string[tag_end:tag_start].strip():
            continue

        # Push tag on stack to wait for closing tag
        tag_stack.append(XMLTag(name=stripped_data, attributes=attributes, comments=comments))
        attributes = {}
        comments = []
        tag_start = None
        tag_end = i + 1

    if tag_stack:
        raise SyntaxError('Could not find pair for each tag')
    return tags


class XMLTag:
    def __init__(self, name: str = None, elements: list = None, attributes: dict = None, parent=None,
                 comments: list = None, closing_comments: list = None, xml_path: str = None, xml_string: str = None,
                 is_comment=False, is_self_closing=False, is_prolog=False, is_special=False):
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
            self.parent = first_tag.parent
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
        self.comments = comments if comments else []
        self.closing_comments = closing_comments if closing_comments else []
        self.is_comment = is_comment
        self.is_self_closing = is_self_closing
        self.is_prolog = is_prolog
        self.is_special = is_special
        self.delete = False

    # Returns list of lines
    def get_lines(self, indent='', use_esc_chars=True):
        if self.delete:
            return []
        if self.is_comment:
            return [f'<!--{self.name}-->']
        if self.is_prolog:
            return [f'{indent}<?{self.name}?>']

        if use_esc_chars:
            attributes = ' '.join([f'{attribute}="{re.sub(r"[<>&]", lambda m: char_escapes[m.group(0)], value)}"'
                                   for attribute, value in self.attributes.items()])
        else:
            attributes = ' '.join([f'{attribute}="{value}"' for attribute, value in self.attributes.items()])

        output = []
        if self.comments:
            for comment in self.comments:
                output.extend([f'{indent}{line}\n' for line in comment.get_lines(use_esc_chars=use_esc_chars)])
        if self.is_special:
            output.append(f'{indent}{self.name}')
            return output
        if self.is_self_closing:
            if attributes:
                output.append(f'{indent}<{self.name} {attributes}/>')
            else:
                output.append(f'{indent}<{self.name}/>')
            return output
        else:
            output.append(f'{indent}<{self.name} {attributes}'.rstrip())
            if not self.elements:
                output[-1] += '>'
            elif len(self.elements) <= 1 and type(self.elements[0]) is str and '\n' not in self.elements[0]:
                output[-1] += '>'
            else:
                output[-1] += f'>\n'
        for element in self.elements:
            if type(element) is str:
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
            if element.delete:
                continue
            output.extend(element.get_lines(indent=f'\t{indent}', use_esc_chars=use_esc_chars))
            output[-1] += '\n'
        if self.closing_comments:
            for comment in self.closing_comments:
                output.append(f'{indent}<!--{comment.name}-->\n')

        if not self.elements:
            output.append(f'</{self.name}>')
        elif len(self.elements) <= 1 and type(self.elements[0]) is str:
            if '\n' in self.elements[0]:
                output.append(f'\n{indent}</{self.name}>')
            else:
                output.append(f'</{self.name}>')
        else:
            output.append(f'{indent}</{self.name}>')
        return output

    def get_tags(self, name: str):
        output = [self] if name == self.name else []
        for element in self.elements:
            if type(element) is XMLTag and (tag_list := element.get_tags(name)):
                output.extend(tag_list)
        return output

    def get_tag(self, name: str, include_self=True):
        if include_self and name == self.name:
            return self

        for element in self.elements:
            if isinstance(element, XMLTag) and element.name == name:
                return element

        # Check deeper if not found in children
        for element in self.elements:
            if isinstance(element, XMLTag):
                if matching_tag := element.get_tag(name, include_self=False):
                    return matching_tag
        return None

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
        if type(element) is not str and not isinstance(element, XMLTag):
            raise TypeError
        if index:
            self.elements.insert(index, element)
        else:
            self.elements.append(element)

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

    def get_lines(self, use_esc_chars=True):
        output = []
        if len(self.tags) == 1:
            return self.tags[0].get_lines(use_esc_chars=use_esc_chars)
        for i, tag in enumerate(self.tags):
            output.extend(tag.get_lines(use_esc_chars=use_esc_chars))
            if i != len(self.tags) - 1:
                output[-1] += '\n'
        return output

    def get_tags(self, name: str):
        output = []
        for tag in self.tags:
            output.extend(tag.get_tags(name))
        return output

    def get_tag(self, name: str):
        for tag in self.tags:
            if output := tag.get_tag(name):
                return output
        return None

    def set_restore_point(self):
        self.restore_point = copy.deepcopy(self)

    def restore(self, keep_restore_point=False):
        if not self.restore_point:
            return
        self.tags = self.restore_point.tags
        if keep_restore_point:
            return
        self.restore_point = None
