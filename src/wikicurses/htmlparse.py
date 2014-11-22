import re

from collections import OrderedDict
from html.parser import HTMLParser

from wikicurses import formats

class UrwidMarkupHandler:
    def __init__(self):
        self._list = []

    def add(self, text, attribute):
        if self and self[-1][0] == attribute:
            self[-1][1] += text
        else:
            self._list.append([attribute, text])

    def __iter__(self):
        return map(tuple, self._list)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, key):
        return self._list[key]

def parseExtract(html):
    parser = _ExtractHTMLParser()
    html = re.sub('\n+', '\n', html).replace('\t', ' ')
    parser.feed(html)
    for i in parser.sections:
        if not parser.sections[i]:
            del parser.sections[i]
    parser.sections.pop("External links", '')
    parser.sections.pop("References", '')
    parser.sections.pop("Contents", '')
    return parser.sections

def parseFeature(html):
    parser = _FeatureHTMLParser()
    parser.feed(html)
    return parser.text

def parseDisambig(html):
    parser = _DisambigHTMLParser()
    parser.feed(html)
    if not parser.sections['']:
        parser.sections.pop('', '')
    parser.sections.pop('Contents', '')
    parser.sections.pop('See also', '')
    return parser.sections

class _ExtractHTMLParser(HTMLParser):
    cursection = ''
    inh = 0
    insidebar = False
    format = 0

    def __init__(self):
        self.sections = OrderedDict({'':UrwidMarkupHandler()})
        self.sec = self.sections['']
        super().__init__(self)

    def add_text(self, text, tformat=None):
        self.sec.add(text, tformat or self.format)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split(' ')
        if tag == 'h2':
            #Remove extra trailing newlines from last section
            if self.sec:
                self.sec[-1][1] = self.sec[-1][1].rstrip() + '\n'
        if re.fullmatch("h[2-6]", tag):
            self.inh = int(tag[1:])
            self.cursection = ''
        elif tag == 'table' \
                and ('wiki-sidebar' in classes or 'infobox' in classes):
            self.insidebar = True
        elif tag == 'p' and self.format&formats.blockquote:
            self.add_text('> ')
        elif tag == 'br':
            self.add_text('\n')
        elif tag == 'li':
            self.add_text("- ")
        elif tag in (i.name for i in formats):
            self.format|=formats[tag]

    def handle_endtag(self, tag):
        if re.fullmatch("h[2-6]", tag):
            self.cursection = self.cursection.strip()
            self.cursection = self.cursection.partition('[edit]')[0]
            self.cursection = self.cursection.partition('[Edit]')[0]
            if tag == 'h2':
                self.sections[self.cursection] = UrwidMarkupHandler()
                self.sec = self.sections[self.cursection]
            else:
                self.add_text(self.cursection)
            self.inh = 0
            self.add_text('\n')
        elif tag == 'table':
            self.insidebar = False
        elif tag == 'p' and not self.format&formats.blockquote:
            self.add_text('\n')
        elif tag in (i.name for i in formats):
            self.format&=~formats[tag]

    def handle_data(self, data):
        if self.insidebar:
            pass
        elif self.inh:
            self.cursection += data
        else:
            tformat = 'h' if (self.inh > 2) else self.format
            if not self.sec:
                data = data.lstrip()
            self.add_text(data, tformat)


class _FeatureHTMLParser(HTMLParser):
    text = ''
    def handle_data(self, data):
        self.text += data

class _DisambigHTMLParser(HTMLParser):
    cursection = ''
    inh2 = False
    ina = False
    inli = False
    format = 0
    li = ''
    a = ''

    def __init__(self):
        self.sections = OrderedDict({'':[]})
        super().__init__(self)

    def add_link(self):
        if self.li:
            self.sections[self.cursection].append((self.a, self.li.strip()))
            self.li = ''
            self.a = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.cursection = ''
            self.inh2 = True
        elif tag == 'li':
            if self.inli:
                self.add_link()
            self.inli = True
        elif tag == 'a' and self.inli:
            self.ina = True

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.inh2 = False
            self.sections[self.cursection] = []
        elif tag == 'li':
            self.add_link()
            self.inli = False
        elif tag == 'a' and self.ina:
            self.ina = False

    def handle_data(self, data):
        if self.inh2 and data not in ('[', ']', 'edit', 'Edit'):
            self.cursection += data
        if self.ina:
            self.a += data
        if self.inli:
            self.li += data
