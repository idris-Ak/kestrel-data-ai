"""Synthetic-only tests for redaction rules-3 (no customer text).

Adopted from the privacy workstream with decision D10. Rules-2 behaviour that
rules-3 keeps is checked against the retained `Rules2Redactor` class.
"""
import unittest

from kestrel import redaction as v3

KNOWN = {'name': {'Avery Price', 'Morgan Day', 'Lovely Person', 'Will Quinlan', 'Mark Okoro',
                  'Jordan Nakamura', 'Priya', 'Sasha Vellacott'},
         'phone': {'0412 345 678'}, 'email': {'avery@example.test'}, 'rego': {'XYZ123'},
         'id': {'BOOK-8374', '009812'}}


class Rules2BehaviourKept(unittest.TestCase):
    def setUp(self):
        self.r = v3.RedactorV3(KNOWN)

    def test_version(self):
        self.assertEqual(v3.VERSION, 'rules-3')

    def test_structured_identifiers_redacted(self):
        raw = ('Avery Price helped. Email avery@example.test or 0412 345 678. '
               'Rego XYZ123; booking ref: BOOK-8374; customer id 009812. 12 Example Street.')
        text, counts, reasons = self.r.redact(raw)
        for token in ('Avery', 'Price', 'avery@', '345 678', 'XYZ123', 'BOOK-8374', '009812', 'Example Street'):
            self.assertNotIn(token, text)
        self.assertEqual(reasons, [])

    def test_ordinary_words_survive(self):
        text = 'The price was fair but it took all day. They said the work was lovely and I will return.'
        self.assertEqual(self.r.redact(text), (text, {}, []))

    def test_clean_text_identical_to_rules2(self):
        old = v3.Rules2Redactor(KNOWN)
        for text in ('Great service from Priya, quick and easy.', 'Waited two hours for a quote.',
                     'Cust noted that the bill was $175 in 2026.'):
            self.assertEqual(self.r.redact(text), old.redact(text))

    def test_contact_and_identifier_residuals_still_withhold(self):
        self.assertIn('CONTACT_RESIDUAL', self.r.redact('Will Quinlan said email me at abc@invalid')[2])
        self.assertIn('IDENTIFIER_RESIDUAL', self.r.redact('Morgan Smith said check 009812 please')[2])

    def test_empty(self):
        self.assertEqual(self.r.redact(' '), (None, {}, []))


class Rules3Resolution(unittest.TestCase):
    def setUp(self):
        self.r = v3.RedactorV3(KNOWN)

    def check(self, raw, expected):
        text, counts, reasons = self.r.redact(raw)
        self.assertEqual((text, reasons), (expected, []))
        return counts

    def test_partial_name_absorbs_surname(self):
        self.check('Jordan Nakamuro - quick turnaround.', '[NAME] - quick turnaround.')
        self.check("Thanks to Priya O'Connell for the help.", 'Thanks to [NAME] for the help.')
        self.check('Priya Day was great.', '[NAME] was great.')

    def test_partial_name_keeps_pronoun_and_sentence_words(self):
        self.check('Told Priya I needed the car.', 'Told [NAME] I needed the car.')
        self.check('Great at explaining, Priya Even the kids got it.', 'Great at explaining, [NAME] Even the kids got it.')

    def test_unknown_full_name_pair(self):
        self.check('Tobias Wrenfield - great service', '[NAME] - great service')

    def test_products_places_calendar_salutations_are_not_names(self):
        for text in ('The Altura Corsa was ready early.', 'Kodiak Ridge and Voltra Arc both serviced.',
                     'Dear Sir or Madam, I wish to complain.', 'Best on the Gold Coast.',
                     'Rang Monday and Thursday.', 'Plain English all the way.', 'My Kodiak Rdge rattles.'):
            self.assertEqual(self.r.redact(text), (text, {}, []), text)

    def test_ambiguous_names_only_in_name_positions(self):
        for text in ('Will be back.', 'Mark the calendar.', 'Lovely staff, quick job.'):
            self.assertEqual(self.r.redact(text), (text, {}, []), text)
        self.check('Thanks Will for sorting it.', 'Thanks [NAME] for sorting it.')
        self.check('Will was very helpful.', '[NAME] was very helpful.')
        self.check("Mark's advice was spot on.", "[NAME]'s advice was spot on.")
        self.check('Great job, cheers - Mark', 'Great job, cheers - [NAME]')

    def test_common_word_surname_only_redacted_in_name_position(self):
        self.check('Price was fair. Day was long.', 'Price was fair. Day was long.')
        self.check('I spoke to Price at the desk.', 'I spoke to [NAME] at the desk.')

    def test_uncommon_known_surname_alone(self):
        self.check('Vellacott sorted it out.', '[NAME] sorted it out.')

    def test_person_cue_names(self):
        self.check('I commend arha for the help.', 'I commend [NAME] for the help.')
        self.check('Thanks Zorika, legend.', 'Thanks [NAME], legend.')
        for text in ('Thanks heaps.', "Can't ask for more.", 'Everyone I dealt with was kind.',
                     'The machine ask for card first.'):
            self.assertEqual(self.r.redact(text), (text, {}, []), text)

    def test_contractions_are_not_names(self):
        text = "Lightning Didn't even take an hour."
        self.assertEqual(self.r.redact(text), (text, {}, []))

    def test_name_counts_include_resolved(self):
        counts = self.check('Tobias Wrenfield and Priya Nakamuro helped.', '[NAME] and [NAME] helped.')
        self.assertGreaterEqual(counts['NAME'], 2)


if __name__ == '__main__':
    unittest.main()
