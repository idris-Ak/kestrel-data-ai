"""Local redaction with conservative review triggers, not an anonymity claim.

Full structured names and given names are treated differently: a surname such
as Price must not erase an ordinary mention of price in a customer complaint.
Unresolved signals withhold the comment from the separate model export.
"""
from collections import Counter, defaultdict
import re

VERSION = 'rules-2'
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', re.I)
PHONE = re.compile(r'(?<!\w)(?:(?:\+61[\s().-]*(?:\(0\)[\s.-]*)?|0)[2-478](?:[\s().-]*\d){8}|1[38]00(?:[\s.-]*\d){6})(?!\d)')
REGO = re.compile(r'\b((?:rego|registration|number\s*plate|plate)\s*(?:is\s*|no\.?\s*|[:#=-]\s*)?)([A-Z0-9]{2,6}(?:[ -][A-Z0-9]{2,4})?)(?!\w)', re.I)
ID = re.compile(r'\b((?:(?:cust(?:omer)?|dms|booking)\s+(?:id|no\.?|number|ref(?:erence)?)(?:\s*[:#=-]\s*|\s+)|(?:cust(?:omer)?)\s*#\s*|ref(?:erence)?\s*[:#]\s*))([\w-]+)', re.I)
ADDRESS = re.compile(r'\b\d{1,5}\s+(?:[A-Za-z]+\s+){1,4}(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|crescent|court|ct)\b', re.I)
TITLE_NAME = re.compile(r'\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b')
AMBIGUOUS_NAMES = {'will', 'bill', 'mark', 'may', 'pat', 'van', 'april', 'june',
                   'august', 'rose', 'joy', 'lovely', 'son', 'hung', 'local'}
IGNORE_NAMES = {'none', 'anonymous', 'local guide', 'test', 'testing', 'n/a',
                'nan', 'tbc', 'unknown'}
BUSINESS_PHRASES = {
    'New Cars', 'Used Cars', 'Service Dept', 'Service Department', 'Service Advisor',
    'Customer Service', 'Head Office', 'Sales Manager', 'Service Manager',
    'Parts Department', 'Parts Counter', 'Good Friday', 'Southport Motors',
    'Publicis Sapient',
}
POSSIBLE_NAME = re.compile(r'\b[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}\b')
PERSON_CONTEXT = re.compile(r"(?i:\b(?:thanks|thank you|cheers|regards|ask for|spoke to|my name is|signed|commend|praise|dealt with|served by))[, :]+([A-Za-z][a-z'-]{1,25})\b")
PARTIAL_NAME = re.compile(r"\[NAME\]\s+(?:[A-Z][a-z]+(?:['’-][A-Z]?[a-z]+)*|[A-Z]\b)")
CONTEXT_WORDS = {'for', 'to', 'again', 'all', 'everyone', 'team', 'guys', 'very',
                 'so', 'and', 'but', 'the', 'a', 'service', 'sales', 'parts', 'mate'}
POSSIBLE_IDENTIFIER = re.compile(r'\b(?:\d{7,}|[A-Z]{2,3}\d{2,4}[A-Z]{0,2})\b')


def bounded(value, flags=re.I):
    return re.compile(r'(?<!\w)' + re.escape(value) + r'(?!\w)', flags)


def literal_pattern(values):
    """A literal trie avoids scanning thousands of separate regexes per comment."""
    trie = {}
    for value in values:
        node = trie
        for char in value.casefold():
            node = node.setdefault(char, {})
        node[''] = {}

    def expression(node):
        branches = [re.escape(char) + expression(child)
                    for char, child in sorted(node.items()) if char]
        tail = branches[0] if len(branches) == 1 else '(?:' + '|'.join(branches) + ')' if branches else ''
        return '(?:' + tail + ')?' if '' in node and tail else tail

    return re.compile(r'(?<!\w)' + expression(trie) + r'(?!\w)', re.I) if trie else None


class Redactor:
    def __init__(self, known):
        values_by_kind = defaultdict(set)
        self.ambiguous = []
        self.numeric_ids = set()
        self.surnames = set()
        for kind, values in sorted(known.items()):
            for value in values:
                value = str(value).strip()
                if not value or value.casefold() in IGNORE_NAMES:
                    continue
                if kind == 'name':
                    tokens = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)?", value)
                    if len(tokens) > 1:
                        values_by_kind['NAME'].add(value)
                        self.surnames.update(t.casefold() for t in tokens[1:])
                    if not tokens:
                        continue
                    given = tokens[0]
                    if given.casefold() in AMBIGUOUS_NAMES:
                        self.ambiguous.append(bounded(given.capitalize(), flags=0))
                    elif len(given) >= 3:
                        values_by_kind['NAME'].add(given)
                    continue
                if kind == 'id' and value.isdigit():
                    if len(value) >= 5:
                        self.numeric_ids.add(value)
                    continue
                if kind == 'id' and len(value) < 5:
                    continue
                values_by_kind[kind.upper()].add(value)
        self.exact = [(literal_pattern(values_by_kind[kind]), kind)
                      for kind in ('EMAIL', 'PHONE', 'REGO', 'ID', 'NAME') if values_by_kind[kind]]
        self.numeric_pattern = literal_pattern(self.numeric_ids)

    def redact(self, value):
        if value is None or not str(value).strip():
            return None, {}, []
        text = str(value)
        counts = Counter()
        for pattern, tag in ((EMAIL, 'EMAIL'), (PHONE, 'PHONE'), (ADDRESS, 'ADDRESS'), (TITLE_NAME, 'NAME')):
            text, n = pattern.subn('[' + tag + ']', text)
            counts[tag] += n
        for pattern, tag in self.exact:
            text, n = pattern.subn('[' + tag + ']', text)
            counts[tag] += n

        def replace_reg(match):
            if any(c.isdigit() for c in match[2]):
                counts['REGO'] += 1
                return match[1] + '[REGO]'
            return match[0]

        text = REGO.sub(replace_reg, text)
        text, n = ID.subn(lambda m: m[1] + '[ID]', text)
        counts['ID'] += n
        reasons = []
        if '@' in text or EMAIL.search(text) or PHONE.search(text):
            reasons.append('CONTACT_RESIDUAL')
        if (self.numeric_pattern and self.numeric_pattern.search(text)) or POSSIBLE_IDENTIFIER.search(text):
            reasons.append('IDENTIFIER_RESIDUAL')
        if any(p.search(text) for p in self.ambiguous):
            reasons.append('AMBIGUOUS_KNOWN_NAME')
        for match in POSSIBLE_NAME.finditer(text):
            if match[0] not in BUSINESS_PHRASES:
                reasons.append('POSSIBLE_PERSON_NAME')
                break
        for match in PERSON_CONTEXT.finditer(text):
            if match[1].casefold() not in CONTEXT_WORDS:
                reasons.append('PERSON_CONTEXT_RESIDUAL')
                break
        if PARTIAL_NAME.search(text):
            reasons.append('PARTIAL_NAME_RESIDUAL')
        for word in re.findall(r'\b[A-Z][a-z]{2,}\b', text):
            if word.casefold() in self.surnames:
                reasons.append('POSSIBLE_SURNAME')
                break
        return text, {k: v for k, v in sorted(counts.items()) if v}, sorted(set(reasons))
