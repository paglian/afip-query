# -*- coding: utf-8 *-*

from nltk import wordpunct_tokenize
from nltk.metrics.distance import edit_distance
from nltk.probability import FreqDist


class SpellChecker:
    """Very simple spell checker"""

    def __init__(self, corpus):
        """Intializes the spell checker with the given corpus"""
        self.tokenize = wordpunct_tokenize

        words = [w.lower() for w in self.tokenize(corpus) if w.isalnum()]

        self.wcount = len(words)
        self.fdist = FreqDist(w.lower() for w in words)

    def get_candidates(self, word, D=1):
        """If word is in lexicon returns [(word, 1.0)].
        Otherwise returns a list with all the words in lexicon that has
        a distance equal or less than to D (D is the Levenshtein edit-distance)
        If there is no such word, returns [(word, 0.0)]
        """
        word = word.lower()

        if word in self.fdist:
            return [(word, 1.0)]

        candidates = []
        counts = []
        for w, c in self.fdist.iteritems():
            if edit_distance(w, word) <= D:
                candidates.append(w)
                counts.append(c)

        if len(candidates) == 0:
            candidates.append(word)
            counts.append(0)

        probs = [float(c) / self.wcount for c in counts]

        return sorted(zip(candidates, probs), key=lambda x: x[1], reverse=True)

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
