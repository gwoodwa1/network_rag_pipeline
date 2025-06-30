#!/usr/bin/env python3
"""
Panflute filter to convert Markdown to JSON-LD with embedded content chunks.
"""
import panflute as pf
import re
import json
import logging
from typing import Dict, Any, List

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

    def to_camel(self, s: str) -> str:
        parts = s.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

    def process_frontmatter(self, meta: pf.MetaMap):
        for k, v in meta.items():
            camel_key = self.to_camel(k)
            val = [pf.stringify(item) for item in v] if isinstance(v, pf.MetaList) else pf.stringify(v)
            self.meta[camel_key] = val
            self.meta[k] = val  # Keep original snake_case as well
        logger.debug(f"Frontmatter: {self.meta}")


    def new_section(self, title: str, level: int, primary: bool = False):
        if self.current and self.buffer:
            self.current['content'] = '\n\n'.join(self.buffer).strip()
            self.sections.append(self.current)
        self.buffer = []
        self.count += 1
        sid = f"{slugify(self.filename)}-sec-{self.count}-{slugify(title)}"
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
        if self.current and self.buffer:
            self.current['content'] = '\n\n'.join(self.buffer).strip()
            self.sections.append(self.current)

        doc_node: Dict[str, Any] = {
            '@type':       'Document',
            '@id':         self.meta.get('id', slugify(self.filename)),
            'filename':    self.filename,
            'title':       self.meta.get('title', self.filename),
            'description': self.meta.get('description', ''),
            'dateCreated': self.meta.get('created', ''),
            'author':      self.meta.get('author', ''),
            'version':     self.meta.get('version', ''),
            'category':    self.meta.get('category', ''),
            'keywords':    self.meta.get('keywords', []),
            'trainingQuestions': self.meta.get('trainingQuestions', self.meta.get('training_questions', [])),
            'relatedProducts': self.meta.get('relatedProducts', self.meta.get('related_products', [])),
            'topics':      self.meta.get('topics', [])
            # 🔸 Do not include 'sections': self.sections
        }

        for sec in self.sections:
            if sec.get('primary'):
                doc_node['mainEntity'] = sec['@id']
                break

        context = {
            '@vocab':     'https://schema.org/',
            'mainEntity': {'@id': 'schema:mainEntity', '@type': '@id'},
            'trainingQuestions': {'@container': '@list'},
            'relatedProducts': {'@container': '@list'},
            'topics': {'@container': '@list'},
            'keywords': {'@container': '@list'}
        }

        # Return doc + sections as individual graph nodes
        return {
            '@context': context,
            '@graph': [doc_node] + self.sections
        }



def prepare(doc):
    md = MarkdownToJSONLD()
    doc.md2jsonld = md
    fname = getattr(doc, 'filename', None)
    md.set_filename(fname or 'unknown')
    if doc.metadata:
        md.process_frontmatter(doc.metadata)
    md.new_section('Document Introduction', 1)
    logger.info(f"Parsed frontmatter keys: {list(doc.md2jsonld.meta.keys())}")
    return doc


def action(elem, doc):
    md = doc.md2jsonld

    if isinstance(elem, pf.Header):
        title = pf.stringify(elem)
        lvl = elem.level
        is_primary = elem.attributes.get('primary', 'false').lower() == 'true'
        if lvl <= 2:
            md.new_section(title, lvl, primary=is_primary)
        else:
            md.add_text('#' * lvl + ' ' + title)

    elif isinstance(elem, pf.Para):
        md.add_text(pf.stringify(elem))
    elif isinstance(elem, pf.CodeBlock):
        lang = elem.classes[0] if elem.classes else ''
        md.add_text(f"```{lang}\n{elem.text}\n```")
    elif isinstance(elem, pf.Table):
        md.add_text(pf.stringify(elem))
    elif isinstance(elem, pf.Image):
        alt = pf.stringify(elem)
        md.add_text(f"![{alt}]({elem.url})")
    elif isinstance(elem, (pf.BulletList, pf.OrderedList)):
        md.add_text(pf.stringify(elem))
    elif isinstance(elem, pf.BlockQuote):
        quote_lines = pf.stringify(elem).splitlines()
        md.add_text('\n'.join(f"> {line}" for line in quote_lines))

    return None


def finalize(doc):
    jsonld = {
        "@context": {
            "@vocab": "https://schema.org/",
            "sections": {"@container": "@list"},
            "mainEntity": {"@id": "schema:mainEntity", "@type": "@id"},
            "trainingQuestions": {"@container": "@list"},
            "relatedProducts": {"@container": "@list"},
            "topics": {"@container": "@list"},
            "keywords": {"@container": "@list"},
        },
        "@graph": doc.md2jsonld.build()["@graph"]
    }

    return pf.RawBlock(json.dumps(jsonld, indent=2), format="json")



def main(doc=None):
    logger.info('Running filter')
    return pf.run_filter(action, prepare=prepare, finalize=finalize, doc=doc)


if __name__ == '__main__':
    main()
