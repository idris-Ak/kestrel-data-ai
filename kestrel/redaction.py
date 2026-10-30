"""Local redaction with conservative review triggers, not an anonymity claim.

Full structured names and given names are treated differently: a surname such
as Price must not erase an ordinary mention of price in a customer complaint.
Unresolved signals withhold the comment from the separate model export.

rules-3 keeps every rules-2 replacement unchanged, then resolves residual name
signals it can locate (partial names, unknown name pairs, names after person
cues, ambiguous names in name-like positions) by replacing them with [NAME].
Products, places, calendar words and ordinary English are not names. Contact
and identifier residuals, and any name signal still present after resolution,
continue to withhold the comment.
"""
from collections import Counter, defaultdict
import re

VERSION = 'rules-3'
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


# ---- rules-3 name resolution -------------------------------------------------
BRANDS = {'altura', 'kodiak', 'veyra', 'voltra', 'kestrel'}
MODELS = {'corsa', 'vista', 'terra', 'trek', 'ridge', 'arc', 'gt', 's4', 'e3'}
PLACES = set("""dandenong ringwood essendon frankston box hill geelong ballarat bendigo shepparton
    parramatta penrith chatswood liverpool newcastle wollongong tamworth chermside springwood ipswich
    southport noosa toowoomba rockhampton rocky townsville hunter victoria vic nsw qld queensland
    melbourne sydney brisbane gold sunshine coast hinterland australia australian metro regional seq
    north south east west city cbd highway m1 bruce pacific""".split())
CALENDAR = set("""monday tuesday wednesday thursday friday saturday sunday mon tue wed thu fri sat sun
    january february march april may june july august september october november december
    jan feb mar apr jun jul aug sep sept oct nov dec christmas easter xmas""".split())
ADDRESS_WORDS = set("""dear sir madam sirs mr mrs ms miss dr team manager managers staff department dept
    advisor adviser desk counter reception workshop office service sales parts customer customers
    accessories finance new used cars car motors motor group dealership dealer""".split())
# Ordinary English (incl. ordinary words that are also surnames) never treated as a
# name on its own; a name still needs a name-like position to be redacted.
COMMON_WORDS = set("""a about above absolutely across actually after again against ago ahead all almost
    along already also although always am amazing an and annoying another answer any anyone anything
    anyway appointment are around arrived as ask asked at average away awesome awful back bad basic
    battery be because been before behind being bell below best better between big bit black bloke
    booked booking both bought brake brakes brilliant brown bunch bush busy but buy by call called
    came can cannot cant car careful cheap cheaper check cheers clean clear clearly collected come
    coming communication completely could couldn courteous customer day days dealt definitely did
    didn different disappointed disappointing do does doesn doing don done down drove during each
    early easy efficient either else email emailed english enough even ever every everyone
    everything excellent expensive explained extra fair fantastic far fast faster few finally fine
    first fixed for found friendlier friendly from full genuinely get getting given go going gone
    good got great ha had half happy hard has hasn have haven having he heaps heard hello help helped
    helpful her here hers high him his honest honestly hopeless horrible hour hours how however hunt
    i if impressed in instead into is isn it its itself just keep kept kind kindly knew know lane
    last late later least left less let like little long look lot lots love lovely low made make
    many maybe me means mean miles more most much must my myself need needed never new next nice
    no nobody none nope not nothing now of off often ok okay on once one only or other others our
    out over overall own page park part people perfect person picked plain please pleasant plenty
    polite poor power price prices professional prompt quick quickly quite quote quoted rang rather
    read ready real really recommend ridiculous right rubbish rude said same seemed seen service
    shame sharp she should shook signed simple since slow small smooth so some someone something
    song soon sorry speedy staff still such sun super sure ta take taken team terrible than thank
    thanks that the their them then there these they thing things third this those though through
    time to today told too took top total tried two under understand unexpected until up updates
    us use used very wade waited waiting walker was wasn way we weeks well went were what when where
    which while white who whole why will winter with without won work worth would wouldn wow yes yet
    you young your""".split())
NOT_NAME = BRANDS | MODELS | PLACES | CALENDAR | ADDRESS_WORDS | COMMON_WORDS
PERSON_VERB = re.compile(r"[ \t]+(?:was|is|has|had|did|does|helped|went|got|made|took|kept|gave|came|"
                         r"called|rang|explained|sorted|arranged|answered|showed|told|knew|looked|"
                         r"greeted|offered|fixed|organised|organized|followed|listened|treated|"
                         r"smiled|stayed|walked|picked|dropped|returned|phoned|emailed|replied|"
                         r"asked|apologised|handled|managed|delivered|drove|sat|spent|helps|sorts)\b")
CUE_BEFORE = re.compile(r"(?i:\b(?:thanks|thank you|thanks to|cheers|regards|ask for|asked for|spoke to|"
                        r"spoke with|speak to|talked to|my name is|signed|commend|praise|dealt with|"
                        r"served by|helped by|looked after by|named|called)|\[NAME\] and|\[NAME\],)[, :]*$")
SENTENCE_START = re.compile(r"(?:^|[.!?;:\n(\"'\u201c\u2018-]\s*|\s[-\u2013\u2014]\s*)$")
TOKEN = r"[A-Z](?:[a-z]+|['\u2019][A-Z][a-z]+)(?:[A-Z][a-z]+)?(?:['\u2019-][A-Za-z]+)*"
NAME_TAIL = re.compile(r"\[NAME\][ \t]+((?:(?:de|di|da|van|von|der|le|la|du|del|dos|bin)[ \t]+)*(?:"
                       + TOKEN + r"|[B-HJ-Z]\.?))(?![\w'\u2019])")
PAIR = re.compile(r"\b(" + TOKEN + r")[ \t]+(" + TOKEN + r")(?![\w'\u2019])")
CONTRACTION = re.compile(r"['\u2019](?:t|s|ve|ll|re|d|m)$")
# Lowercase unknown words are names only after a strong person cue ("ask for card" is not).
STRONG_CUE = re.compile(r"(?i:thanks|thank you|cheers|regards|spoke to|my name is|commend|praise|dealt with|served by)[, :]+$")
CAPITAL = re.compile(r"(?<![\w\[])(" + TOKEN + r")(?![\w'\u2019\]])")


class RedactorV3(Redactor):
    """rules-2 replacements, then [NAME] for located residual name signals."""

    def __init__(self, known):
        super().__init__(known)
        self.ambiguous_words = {p.pattern[len('(?<!\\w)'):-len('(?!\\w)')].replace('\\', '').casefold()
                                for p in self.ambiguous}

    # A name-like position: after a person cue, mid-sentence, possessive,
    # followed by a person verb, or a dash/comma sign-off at the end.
    def name_position(self, text, start, end, verbs=True):
        before, after = text[:start], text[end:]
        if CUE_BEFORE.search(before):
            return True
        if after[:2] in ("'s", "\u2019s") or (verbs and PERSON_VERB.match(after)):
            return True
        if re.match(r"[ \t]*[.!]?[ \t]*$", after) and re.search(r"[-\u2013\u2014,][ \t]*$", before):
            return True
        return not SENTENCE_START.search(before)

    def nameish(self, token, second=False):
        key = CONTRACTION.sub('', token.casefold())
        if key in self.ambiguous_words or (second and key in self.surnames):
            return True
        return key not in NOT_NAME

    def resolve(self, text):
        n = 0

        def absorb(value):
            nonlocal n
            while True:
                match = next((m for m in NAME_TAIL.finditer(value)
                              if m[1].split()[-1].casefold() in self.surnames
                              or m[1].split()[-1].rstrip('.').casefold() not in NOT_NAME), None)
                if not match:
                    return value
                value = value[:match.start()] + '[NAME]' + value[match.end():]
                n += 1

        text = absorb(text)
        # Unknown two-token person names (products, places and ordinary words excluded).
        out, last = [], 0
        for m in PAIR.finditer(text):
            a, b = m[1], m[2]
            if m[0] in BUSINESS_PHRASES or a.casefold() in BRANDS:
                continue
            if b.casefold() in MODELS:
                continue
            if self.nameish(a) and self.nameish(b, second=True):
                out.append(text[last:m.start()] + '[NAME]'); last = m.end(); n += 1
        text = ''.join(out) + text[last:]
        # Single tokens: names after cues, ambiguous names and surnames in name-like positions.
        out, last = [], 0
        for m in CAPITAL.finditer(text):
            word = CONTRACTION.sub('', m[1]); key = word.casefold()
            end = m.start() + len(word)
            if key in BRANDS | MODELS | PLACES | CALENDAR - self.ambiguous_words:
                continue
            if key in self.ambiguous_words or key in self.surnames:
                hit = (self.name_position(text, m.start(), end, verbs=key in self.ambiguous_words)
                       if key in NOT_NAME or key in self.ambiguous_words else True)
            else:
                hit = bool(CUE_BEFORE.search(text[:m.start()])) and key not in CONTEXT_WORDS and key not in COMMON_WORDS | ADDRESS_WORDS
            if hit:
                out.append(text[last:m.start()] + '[NAME]'); last = end; n += 1
        text = ''.join(out) + text[last:]
        # Lowercase unknown words straight after a person cue (e.g. "I commend arha").
        def cue_word(m):
            nonlocal n
            word = m[1]
            if (word[0].isupper() or word.casefold() in CONTEXT_WORDS | NOT_NAME
                    or not STRONG_CUE.search(m[0][:m.start(1) - m.start()])):
                return m[0]
            n += 1
            return m[0][:m.start(1) - m.start()] + '[NAME]'
        text = PERSON_CONTEXT.sub(cue_word, text)
        return absorb(text), n

    def residual_name_reasons(self, text):
        reasons = []
        if any(self.name_position(text, m.start(), m.end()) for p in self.ambiguous for m in p.finditer(text)):
            reasons.append('AMBIGUOUS_KNOWN_NAME')
        for m in PAIR.finditer(text):
            if (m[0] not in BUSINESS_PHRASES and m[1].casefold() not in BRANDS and m[2].casefold() not in MODELS
                    and self.nameish(m[1]) and self.nameish(m[2], second=True)):
                reasons.append('POSSIBLE_PERSON_NAME'); break
        for m in PERSON_CONTEXT.finditer(text):
            if (m[1].casefold() not in CONTEXT_WORDS | NOT_NAME and m[1][0].islower()
                    and STRONG_CUE.search(m[0][:m.start(1) - m.start()])):
                reasons.append('PERSON_CONTEXT_RESIDUAL'); break
        if any(m[1].split()[-1].casefold() in self.surnames or m[1].split()[-1].rstrip('.').casefold() not in NOT_NAME
               for m in NAME_TAIL.finditer(text)):
            reasons.append('PARTIAL_NAME_RESIDUAL')
        for m in CAPITAL.finditer(text):
            word = CONTRACTION.sub('', m[1]); key = word.casefold()
            if key in self.surnames and key not in self.ambiguous_words and (
                    key not in NOT_NAME or self.name_position(text, m.start(), m.start() + len(word), verbs=False)):
                reasons.append('POSSIBLE_SURNAME'); break
        return reasons

    def redact(self, value):
        text, counts, reasons = super().redact(value)
        if text is None:
            return text, counts, reasons
        name_reasons = {'AMBIGUOUS_KNOWN_NAME', 'POSSIBLE_PERSON_NAME', 'PERSON_CONTEXT_RESIDUAL',
                        'PARTIAL_NAME_RESIDUAL', 'POSSIBLE_SURNAME'}
        if not name_reasons & set(reasons):
            return text, counts, reasons  # rules-2 passes stay byte-identical
        text, n = self.resolve(text)
        counts = dict(counts)
        if n:
            counts['NAME'] = counts.get('NAME', 0) + n
        kept = [r for r in reasons if r not in name_reasons]
        if '@' in text or EMAIL.search(text) or PHONE.search(text):
            kept.append('CONTACT_RESIDUAL')
        if (self.numeric_pattern and self.numeric_pattern.search(text)) or POSSIBLE_IDENTIFIER.search(text):
            kept.append('IDENTIFIER_RESIDUAL')
        kept += self.residual_name_reasons(text)
        return text, {k: v for k, v in sorted(counts.items()) if v}, sorted(set(kept))


# Drop-in: kestrel.preparation imports `Redactor`; the rules-2 class stays available.
Rules2Redactor = Redactor
Redactor = RedactorV3
