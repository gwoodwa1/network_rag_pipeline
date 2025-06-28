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

    def new_section(self, title: str, level: int):
        if self.current and self.buffer:
            self.current['content'] = '\n\n'.join(self.buffer).strip()
            self.sections.append(self.current)
        self.buffer = []
        self.count += 1
        sid = f"{slugify(self.filename)}-sec-{self.count}-{slugify(title)}"
        self.current = {'@type': 'Section', '@id': sid, 'title': title, 'level': level, 'content': ''}
        logger.debug(f"New section: {title}")

    def add_text(self, txt: str):
        txt = txt.strip()
        if txt:
            self.buffer.append(txt)
            logger.debug(f"Buffer: {txt[:30]}...")

    def build(self) -> Dict[str, Any]:
        if self.current and self.buffer:
            self.current['content'] = '\n\n'.join(self.buffer).strip()
            self.sections.append(self.current)
        doc: Dict[str, Any] = {
            '@context': {'@vocab': 'https://schema.org/', 'sections': {'@container': '@list'}},
            '@type': 'Document',
            '@id': self.meta.get('id', slugify(self.filename)),
            'filename': self.filename,
            'title': self.meta.get('title', self.filename),
            'description': self.meta.get('description', ''),
            'dateCreated': self.meta.get('date', ''),
            'author': self.meta.get('author', ''),
            'sections': self.sections
        }
        logger.info(f"Built JSON-LD for {self.filename}")
        return {'@context': doc['@context'], '@graph': [doc]}


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
    if isinstance(elem, pf.Header):
        title = pf.stringify(elem)
        lvl = elem.level
        if lvl <= 2:
            md.new_section(title, lvl)
        else:
            md.add_text('#'*lvl + ' ' + title)
    elif isinstance(elem, pf.Para): md.add_text(pf.stringify(elem))
    elif isinstance(elem, pf.CodeBlock): md.add_text(f"```{elem.classes[0] if elem.classes else ''}\n{elem.text}\n```")
    elif isinstance(elem, pf.Table): md.add_text(pf.stringify(elem))
    elif isinstance(elem, pf.Image): md.add_text(f"![{pf.stringify(elem)}]({elem.url})")
    elif isinstance(elem, (pf.BulletList, pf.OrderedList)): md.add_text(pf.stringify(elem))
    elif isinstance(elem, pf.BlockQuote): txt=pf.stringify(elem); md.add_text('\n'.join(f"> {l}" for l in txt.split('\n')))
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
