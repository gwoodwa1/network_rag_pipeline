# md2jsonld.py
#!/usr/bin/env python3
"""
Panflute filter to convert Markdown to JSON-LD with embedded content chunks.
"""
import panflute as pf
import re
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    t = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', t).strip('-')


class MarkdownToJSONLD:
    def __init__(self):
        self.reset()
        self.filename = 'unknown'

    def reset(self):
        self.meta: Dict[str, Any] = {}
        self.sections: list = []
        self.current: Dict[str, Any] = {}
        self.buffer: list = []
        self.count: int = 0

    def set_filename(self, fname: str):
        self.filename = fname

    def process_frontmatter(self, meta: pf.MetaMap):
        for k, v in meta.items(): self.meta[k] = pf.stringify(v)
        logger.debug(f"Frontmatter: {self.meta}")

    def new_section(self, title: str, level: int, primary: bool = False):
        if self.current and self.buffer:
            self.current['content'] = '\n\n'.join(self.buffer).strip()
            self.sections.append(self.current)
        self.buffer = []
        self.count += 1
        sid = f"{slugify(self.filename)}-sec-{self.count}-{slugify(title)}"
        self.current = {'@type': 'Section', '@id': sid, 'title': title, 'level': level, 'content': ''}
        self.current = {
            '@type':   'Section',
            '@id':     sid,
            'title':   title,
            'level':   level,
            'content': '',
            'primary': primary
        }
        logger.debug(f"New section: {title}")

    def add_text(self, txt: str):
        txt = txt.strip()
        if txt:
            self.buffer.append(txt)
            logger.debug(f"Buffer: {txt[:30]}...")

    def build(self) -> Dict[str, Any]:
        # 1) Flush the last section buffer into self.sections
        if self.current and self.buffer:
            self.current['content'] = '\n\n'.join(self.buffer).strip()
            self.sections.append(self.current)

        # 2) Construct the Document node (without mainEntity yet)
        doc_node: Dict[str, Any] = {
            '@type':       'Document',
            '@id':         self.meta.get('id', slugify(self.filename)),
            'filename':    self.filename,
            'title':       self.meta.get('title', self.filename),
            'description': self.meta.get('description', ''),
            'dateCreated': self.meta.get('date', ''),
            'author':      self.meta.get('author', ''),
            'sections':    self.sections[:]   # inline full section objects
        }

        # ←───────────────────────────────────────────────────────────────────────────
        # ADD THESE 3 LINES to pick the primary section as mainEntity:
        for sec in self.sections:
            if sec.get('primary'):                # assumes your action() set 'primary'=True
                doc_node['mainEntity'] = sec['@id']
                break
        # ────────────────────────────────────────────────────────────────────────────

        # 3) Build the JSON-LD context
        context = {
            '@vocab':     'https://schema.org/',
            'sections':   {'@container': '@list'},
            'mainEntity': {'@id': 'schema:mainEntity', '@type': '@id'}
        }

        # 4) Return the full JSON-LD graph
        return {
            '@context': context,
            '@graph':   [doc_node] + self.sections
        }




def prepare(doc):
    md = MarkdownToJSONLD()
    doc.md2jsonld = md
    fname = getattr(doc, 'filename', None)
    if fname:
        md.set_filename(fname)
    else:
        md.set_filename('unknown')
    if doc.metadata:
        md.process_frontmatter(doc.metadata)
    md.new_section('Document Introduction', 1)
    return doc


def action(elem, doc):
    md = doc.md2jsonld

    # Handle headers (start new sections)
    if isinstance(elem, pf.Header):
        title = pf.stringify(elem)
        lvl   = elem.level

        # Detect primary="true" attribute on the header
        is_primary = elem.attributes.get('primary', 'false').lower() == 'true'

        if lvl <= 2:
            # Pass the primary flag into new_section
            md.new_section(title, lvl, primary=is_primary)
        else:
            # For deeper headers, just record them as text
            md.add_text('#' * lvl + ' ' + title)

    # Paragraphs
    elif isinstance(elem, pf.Para):
        md.add_text(pf.stringify(elem))

    # Code blocks
    elif isinstance(elem, pf.CodeBlock):
        lang = elem.classes[0] if elem.classes else ''
        md.add_text(f"```{lang}\n{elem.text}\n```")

    # Tables
    elif isinstance(elem, pf.Table):
        md.add_text(pf.stringify(elem))

    # Images
    elif isinstance(elem, pf.Image):
        alt = pf.stringify(elem)
        md.add_text(f"![{alt}]({elem.url})")

    # Lists
    elif isinstance(elem, (pf.BulletList, pf.OrderedList)):
        md.add_text(pf.stringify(elem))

    # Block quotes
    elif isinstance(elem, pf.BlockQuote):
        quote_lines = pf.stringify(elem).splitlines()
        md.add_text('\n'.join(f"> {line}" for line in quote_lines))

    return None



def finalize(doc):
    out = doc.md2jsonld.build()
    doc.content = [pf.RawBlock(json.dumps(out, indent=2), format='json')]
    return doc


def main(doc=None):
    logger.info('Running filter')
    return pf.run_filter(action, prepare=prepare, finalize=finalize, doc=doc)

if __name__ == '__main__':
    main()
