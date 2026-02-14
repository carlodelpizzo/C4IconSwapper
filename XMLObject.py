from __future__ import annotations
import re
import warnings
from pathlib import Path
from collections import deque


# TODO: handle strings on outside of tags e.g. <tag1>string1<tag2></tag2>string2</tag1>
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
    comments = []
    tag_stack = deque()
    tag_start = None
    tag_end = None
    check_comment_in_value = None
    attributes = {}
    nested_comments = 0
    nested_skip = False
    special_tag = False
    sub_tag_found = False

    # Begin Parsing
    for i in (char_i for char_i, char in enumerate(xml_string) if char in ('<', '>')):
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
            if sub_tag and not sub_tag_found:
                self_closing = False
                attributes = {}
                if ' ' in data:
                    if data[:data.index(' ')] != sub_tag:
                        tag_start = None
                        tag_end = i + 1
                        continue
                    if data.endswith('/'):
                        self_closing = True
                    data_no_attr = re_attributes.sub('', data)
                    if '=' in data_no_attr:
                        tag_start = None
                        tag_end = i + 1
                        continue
                    attributes = {k: (v, q) for k, q, v in re_attributes.findall(data)}
                    data = data[:data.index(' ')]
                elif data.endswith('/'):
                    if (data := data[:-1]) != sub_tag:
                        tag_start = None
                        tag_end = i + 1
                        continue
                    if '<' in data or '>' in data:
                        warnings.warn('< or > found in self-closing tag', SyntaxWarning)
                        return []
                    self_closing = True
                elif data != sub_tag:
                    tag_start = None
                    tag_end = i + 1
                    continue
                if self_closing:
                    return [XMLTag(name=data, attributes=attributes, is_self_closing=True)]
                tag_stack.append(XMLTag(name=data, attributes=attributes, leading_comments=comments))
                sub_tag_found = True
                attributes = {}
                comments = []
                tag_start = None
                tag_end = i + 1
                continue
        except TypeError:
            warnings.warn('Generic issue with XML syntax', SyntaxWarning)
            return []

        if special_tag and (special_data := xml_string[special_tag:tag_start].rstrip()).endswith(']>'):
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=special_data, parent=tag_stack[-1], leading_comments=comments,
                                                     is_cdata=True))
            else:
                tags.append(XMLTag(name=special_data, leading_comments=comments, is_cdata=True))
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
                warnings.warn('Issue with nested comments', SyntaxWarning)
                return []
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
            data_no_attr = re_attributes.sub('', data)
            if '=' in data_no_attr:
                continue
            attributes = {k: (v, q) for k, q, v in re_attributes.findall(data)}
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=data[1:-1], parent=tag_stack[-1], attributes=attributes,
                                                     is_prolog=True, leading_comments=comments))
            else:
                tags.append(XMLTag(name=data[1:-1], attributes=attributes, is_prolog=True, leading_comments=comments))
            comments = []
            attributes = {}
            tag_start = None
            tag_end = None
            continue

        # Parse tag attributes
        if ' ' in data:
            data_no_attr = re_attributes.sub('', data)
            if '=' in data_no_attr:
                continue
            attributes = {k: (v, q) for k, q, v in re_attributes.findall(data)}

        # Handle self-closing tags
        if data.endswith('/'):
            if ' ' in data:
                data = data[:data.index(' ')]
            else:
                data = data[:-1]
            if '<' in data or '>' in data:
                warnings.warn('< or > found in self-closing tag', SyntaxWarning)
                return []
            if tag_stack:
                tag_stack[-1].elements.append(XMLTag(name=data, attributes=attributes, is_self_closing=True,
                                                     parent=tag_stack[-1],
                                                     leading_comments=comments))
                attributes = {}
            else:
                tags.append(XMLTag(name=data, attributes=attributes, is_self_closing=True, leading_comments=comments))
            comments = []
            tag_start = None
            tag_end = None
            continue

        stripped_data = data[:data.index(' ')] if ' ' in data else data

        # Handle closing tag, Pull off stack
        if tag_stack and stripped_data.startswith('/') and tag_stack[-1].name == stripped_data[1:]:
            # Add comments as string element if inside a tag which has no tag elements
            if check_comment_in_value and comments:
                str_element = xml_string[check_comment_in_value:tag_start]
                if str_element.strip():
                    tag_stack[-1].elements.append(str_element)
                comments = []
                check_comment_in_value = None
            # Add string element
            elif tag_end:
                str_element = xml_string[tag_end:tag_start]
                if str_element.strip():
                    tag_stack[-1].elements.append(str_element)

            # Add comments to XMLTag
            if comments:
                pop_list = []
                for element in tag_stack[-1].elements:
                    for comment in comments:
                        if isinstance(element, str) and f'<!--{comment.name}-->' in element:
                            pop_list.append(comments.index(comment))
                for x in sorted(pop_list, reverse=True):
                    comments.pop(x)
                if comments:
                    tag_stack[-1].trailing_comments = comments
                    comments = []

            # Append XMLTag to parent or to XMLObject
            temp_tag = tag_stack.pop()
            if tag_stack:
                temp_tag.parent = tag_stack[-1]
                tag_stack[-1].elements.append(temp_tag)
            else:
                tags.append(temp_tag)
                if sub_tag and sub_tag_found and tags[-1].name == sub_tag:
                    return tags
            tag_start = None
            tag_end = None
            continue

        # If closing tag for last tag on stack
        if tag_end and data.endswith(f'/{tag_stack[-1].name}'):
            str_element = f'{xml_string[tag_end:tag_start]}<{data[:data.rfind("<")]}'
            if str_element:
                tag_stack[-1].elements.append(str_element)
            temp_tag = tag_stack.pop()
            if tag_stack:
                temp_tag.parent = tag_stack[-1]
                tag_stack[-1].elements.append(temp_tag)
            else:
                tags.append(temp_tag)  # Would this ever happen?
            tag_start = None
            tag_end = None
            if sub_tag and data == f'/{sub_tag}':
                return tags
            continue
        # What is this check for?
        if tag_end and xml_string[tag_end:tag_start].strip():
            continue

        # Push tag on stack to wait for closing tag
        tag_stack.append(XMLTag(name=stripped_data, attributes=attributes, leading_comments=comments))
        attributes = {}
        comments = []
        tag_start = None
        tag_end = i + 1

    if tag_stack:
        warnings.warn('Could not find pair for each tag', SyntaxWarning)
        return []
    return tags


# Can only have one root tag
class XMLTag:
    # noinspection PyUnresolvedReferences
    def __init__(self, name: str = None, elements: list = None, attributes: dict = None, parent=None,
                 leading_comments: list = None, trailing_comments: list = None, xml_path: str | Path = None,
                 xml_string: str = None, is_comment=False, is_self_closing=False, is_prolog=False, is_cdata=False,
                 sub_tag=''):
        self.init_success = True
        # Constructs an XMLTag object based on the first tag in data if XML path/data is passed in
        if xml_path or xml_string:
            first_tag = parse_xml(xml_path=xml_path, xml_string=xml_string, sub_tag=sub_tag)
            if not first_tag:
                warnings.warn(f'Excepted {self.__class__.__name__} in list; Received Empty list',
                              RuntimeWarning)
                self.init_success = False
                return
            first_tag = first_tag[0]
            if not isinstance(first_tag, XMLTag):
                warnings.warn(f'Expected type: {self.__class__.__name__}; '
                              f'Received type: {first_tag.__class__.__name__}', RuntimeWarning)
                self.init_success = False
                return
            self.name = first_tag.name
            self.parent = first_tag.parent
            self.attributes = first_tag.attributes
            self.elements = first_tag.elements
            self.leading_comments = first_tag.leading_comments
            self.trailing_comments = first_tag.trailing_comments
            self.is_prolog = first_tag.is_prolog
            self.is_comment = first_tag.is_comment
            self.is_CDATA = first_tag.is_CDATA
            self.is_self_closing = first_tag.is_self_closing
            self.hide = first_tag.hide
            return
        self.name = name
        self.parent = parent
        self.attributes = {}
        self.attr_q = {}
        if attributes:
            for k, (v, q) in attributes.items():
                self.attributes[k] = v
                self.attr_q[k] = q
        self.elements = [] if not elements else elements
        self.leading_comments = [] if not leading_comments else leading_comments
        self.trailing_comments = [] if not trailing_comments else trailing_comments
        self.is_prolog = is_prolog
        self.is_comment = is_comment
        self.is_CDATA = is_cdata
        self.is_self_closing = is_self_closing
        self.hide = False

    @property
    def value(self):
        return '' if not self.init_success else next((el for el in self.elements if isinstance(el, str)), '')

    @property
    def children(self) -> list[XMLTag]:
        # noinspection PyTypeChecker
        return [element for element in self.elements if not isinstance(element, str)]

    def get_value(self) -> str:
        return self.value

    def set_value(self, new_value: str):
        for i, element in enumerate(self.elements):
            if isinstance(element, str):
                self.elements[i] = new_value
                break

    def add_element(self, element, index=None):
        if not isinstance(element, (str, XMLTag)):
            raise TypeError
        if index:
            self.elements.insert(index, element)
        else:
            self.elements.append(element)

    def get_lines(self, indent='', use_esc_chars=True, as_string=False) -> list[str] | str:
        if not self.init_success:
            return '' if as_string else []
        if self.hide:
            return '' if as_string else []
        if self.is_comment:
            comment = f'<!--{self.name}-->'
            return comment if as_string else [comment]
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
        if self.leading_comments:
            for comment in self.leading_comments:
                output.extend([f'{indent}{line}\n' for line in comment.get_lines(use_esc_chars=use_esc_chars)])
        if self.is_CDATA:
            output.append(f'{indent}{self.name}')
            return ''.join(output) if as_string else output
        if self.is_self_closing:
            if attributes:
                output.append(f'{indent}<{self.name} {attributes} />')
            else:
                output.append(f'{indent}<{self.name} />')
            return ''.join(output) if as_string else output
        else:
            output.append(f'{indent}<{self.name} {attributes}'.rstrip())
            if not self.elements or isinstance(self.elements[0], str):
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
        if self.trailing_comments:
            for comment in self.trailing_comments:
                output.append(f'{indent}<!--{comment.name}-->\n')

        if not self.elements or isinstance(self.elements[0], str):
            output.append(f'</{self.name}>')
        else:
            output.append(f'{indent}</{self.name}>')
        return ''.join(output) if as_string else output

    def get_tags(self, name: str) -> list[XMLTag]:
        if not self.init_success:
            return []
        output = [self] if name == self.name else []
        for element in self.elements:
            if isinstance(element, XMLTag) and (tag_list := element.get_tags(name)):
                output.extend(tag_list)
        return output

    def get_tags_dict(self, name_set: set[str]) -> dict[str, XMLTag]:
        if not self.init_success:
            return {}
        output_dict = {}
        for element in self.elements:
            if isinstance(element, str):
                continue
            if element.name in name_set:
                name_set.remove(element.name)
                output_dict[element.name] = element
            if element_tag_dict := element.get_tags_dict(name_set):
                name_set.difference_update(element_tag_dict)
                output_dict |= element_tag_dict
            if not name_set:
                break
        return output_dict

    def get_tag(self, name: str, include_self=True) -> XMLTag | None:
        if not self.init_success:
            return None
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

    def get_lines(self, use_esc_chars=True, as_string=False) -> list[str] | str:
        output = []
        if len(self.tags) == 1:
            return self.tags[0].get_lines(use_esc_chars=use_esc_chars)
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
