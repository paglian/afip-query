# -*- coding: utf-8 *-*

from nltk import wordpunct_tokenize
from nltk.metrics.distance import edit_distance


class SpellChecker:
    """Very simple spell checker"""

    def __init__(self, corpus):
        """Intializes the spell checker with the given corpus"""
        self.tokenize = wordpunct_tokenize

        words = [w.lower() for w in self.tokenize(corpus) if w.isalnum()]
        self.lexicon = frozenset(words)

    def get_candidates(self, word, D=1):
        """If word is in lexicon returns [(word, 1.0)].
        Otherwise returns a list with all the words in lexicon that has
        a distance equal to 1. If there is no such word, returns [(word, 0.0)]
        D is the max Levenshtein edit-distance
        """
        if word in self.lexicon:
            return [(word, 1.0)]

        candidates = [c for c in self.lexicon if edit_distance(c, word) == D]

        l = len(candidates)

        if l == 0:
            return [(word, 0.0)]

        return zip(candidates, [1.0 / l] * l)

    def correct_word(self, word):
        """This is a short-hand for check(word)[0][0]"""
        return self.get_candidates(word)[0][0]

    def correct_sentence(self, s):
        tokens = self.tokenize(s)

        misspell_found = False
        cs = ""

        for t in tokens:
            t = t.lower()

            # Do not check words that are not alpahnumeric
            if t.isalnum():
                ct = self.correct_word(t)
                if ct != t:
                    misspell_found = True
            else:
                ct = t

            if len(cs) > 0 and (t.isalnum() or t == u'\u00bf'):
                cs += " "
            cs += ct

        if misspell_found:
            return cs.rstrip()
        else:
            return s
