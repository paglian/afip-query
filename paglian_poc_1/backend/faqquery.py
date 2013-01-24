# -*- coding: utf-8 -*-

import sys
import time
import unicodedata
import string
#import re
import os
#from random import choice

from faqfile import FaqFile
from searchengine import Crawler
from fastnn import FastNeuralNet
from lemmatizer import Lemmatizer


db_path = os.path.dirname(os.path.abspath(__file__)) + '/db/'
valid_chars = string.ascii_letters + ' '
ignore_lemmas = ['ser', 'estar', 'parecer', 'poder']


class FaqQuery:
    """Interface to train an later query FAQ file using a neural network"""

    def __init__(self, faq_file):
        self.verbose_level = 1

        self.make_dirs()

        base_name = os.path.basename(faq_file)

        self.nn = FastNeuralNet(db_path + base_name + "_nn.db")

        # Not crawling data, from Crawler we are just using a couple of methods
        # to get word IDs and URL IDs
        self.crawler = Crawler(db_path + base_name + "_index.db")

        self.set_faq_file(faq_file)

    def make_dirs(self):
        """Make directories needed to run the application"""
        if not os.path.exists(db_path):
            os.makedirs(db_path)

    def set_faq_file(self, faqfile):
        """Sets the current FAQ file"""

        # Read FAQ file and get a dictionary with pairs:
        # (AFIP question ID, question string)
        self.faq = FaqFile(faqfile)

        # Map: URL ID -> [ AFIP Question ID, Question String ]
        self.faqdict = {}

        # When reading this code think "URL" as "neural net output"
        # TODO refactor & replace all ocurrences of "url" with "output"
        self.urlids = []

        # translate AFIP question IDs to URL IDs
        for k, v in self.faq.data.iteritems():
            urlid = self.crawler.geturlid(k)
            self.urlids.append(urlid)
            self.faqdict[urlid] = [k, v]

    def normalize(self, s):
        wsz = ''.join(x for x in unicodedata.normalize('NFKD', unicode(s))
                        if x in valid_chars).lower()
        #print "sanitized %s -> %s" % (word, wsz)
        return wsz

    def parse_sentence(self, s):
        keywords = []

        # Lemmatize sentence and only keep verbs, nouns and PTs
        l = Lemmatizer()
        lemmas = l.lemmatize(s)
        lemmas = l.filter(lemmas, ['V', 'N', 'PT'])

        # Normalize lemmas
        for l in lemmas:
            norm_lemma = self.normalize(l['lemma'])
            if len(norm_lemma) == 0 or norm_lemma in ignore_lemmas:
                continue
            keywords.append(norm_lemma)

        self.vprint("Keywords: ", keywords)

        return [self.crawler.getwordid(word) for word in keywords]

    def train(self, iters=100, print_tests=False):
        """Train neural network with the given FAQ file. Must be a valid JSON
        file"""
        self.__make_train_cache()

        try:
            for i in range(iters):
                self.vprint("\n\n******** ITERATION %d ********\n\n" % (i + 1))
                self.__train()

                if print_tests:
                    self.__print_test_results(i + 1, iters)

        except KeyboardInterrupt:
            print "Aborted!"

    def __make_train_cache(self):
        """for each question in FAQ, build a cache with the parsed data and
        and the url id"""
        self.parsed_data = {}
        self.url_id = {}
        for k, v in self.faq.data.iteritems():
            self.parsed_data[k] = self.parse_sentence(v)
            self.url_id[k] = self.crawler.geturlid(k)

    def __train(self):
        c = 1
        total = len(self.faq.data)

        for k, v in self.faq.data.iteritems():
            self.vprint("%d/%d Training question %s: %s" % (c, total, k, v))

            starttime = time.time()
            exp_url_id = self.url_id[k]
            wordids = self.parsed_data[k]

            ############################## CHECK ##############################
            # Train with bigrams and 3-grams ? e.g.  min = 2, max = 3
            # Or whole query? e.g. min = max = 1000
            min_ngram_len = 1000
            max_ngram_len = 1000
            # Train passing *all* urlids? e.g:
            urlsubset = self.urlids
            # Or just a random subset? e.g:
            #urlsubset = [expurl]
            #for i in range(10):
            #    urlsubset.append(choice(self.urlids))
            ###################################################################

            for ngram_len in range(min_ngram_len, max_ngram_len + 1):
                for i in range(max(1, len(wordids) - ngram_len)):
                    self.nn.trainquery(wordids[i:i + ngram_len], urlsubset,
                                       exp_url_id)

            self.vprint("Done in %f secs\n" % ((time.time() - starttime)))
            c += 1

    def __print_test_results(self, iteration, total):
        """Print some test results"""
        #qids = ["467563"]
        qids = ["138165"]
        queries = ['en que bancos puedo realizar el pago',
            'bancos pago',
            'pago',
            'recategorizarme?',
            'tomar para recategorizarme?',
            'que debo tomar para recategorizarme?']

        for qid in qids:
            scores = [0.0] * len(queries)
            for q in queries:
                test_result = self.query(q, 300)
                for r in test_result:
                    if r[1] != qid:
                        continue
                    else:
                        scores[queries.index(q)] = r[0]
                        break

            print iteration, qid, "Scores: ", scores

        if iteration == total:
            for q in queries:
                result = self.query(q, 300)
                print "\nQuery:", q
                for r in result[:10]:
                    print r

    def query(self, q, N=10):
        """Get result for query q using the currently trained database and
        return N best answers"""

        urlids = self.urlids
        wordids = self.parse_sentence(q)
        result = self.nn.getresult(wordids, urlids)

        # result is hard to read. So we create user-friendly result with
        # form [QuestionRelevance, QuestionID, QuestionString]
        uf_result = []
        for i in range(len(urlids)):
            q = self.faqdict[urlids[i]]
            uf_result.append([result[i], q[0], q[1]])

        # sort by relevance
        uf_result.sort(reverse=True)

        return uf_result[0:N]

    def test(self):
        self.__print_test_results(1, 1)

    def vprint(self, *args, **keys):
        level = 1
        if 'level' in keys:
            level = keys['level']

        if self.verbose_level >= level:
            for arg in args:
                print arg


def main():
    def print_usage():
        print \
"""Usage:
    faqquery.py <faq_file> --train          # Train using the given file. e.g afipquery afip_mono_faq.json --train
    faqquery.py <faq_file> --test           # Print some test results. e.g afipquery afip_mono_faq.json --test
    faqquery.py <faq_file> --test-and-train #
    faqquery.py <faq_file>                  # Interactive query mode. e.g. afipquery afip_mono_faq.json
    faqquery.py <faq_file> <query_string>   # Single query mode. e.g afipquery afip_mono_faq.json "Como me inscribo?"
"""

    def print_results(fq, query):
        N = 10
        result = fq.query(query, N)
        print "\nTop %d results:" % N
        for r in result:
            print r

    def single_query_mode(faq_file, query):
        fq = FaqQuery(faq_file)
        print_results(fq, query)

    def interactive_mode(faq_file):
        fq = FaqQuery(faq_file)
        while True:
            print "\n\nQuery:",
            query = raw_input()
            print_results(fq, query)

    def train_mode(faq_file):
        fq = FaqQuery(faq_file)
        print "Training..."
        fq.train()
        print "Training finished!"

    def test_mode(faq_file):
        fq = FaqQuery(faq_file)
        fq.verbose_level = 0
        fq.test()

    def train_and_test_mode(faq_file):
        fq = FaqQuery(faq_file)
        fq.verbose_level = 0
        print "Training..."
        fq.train(print_tests=True)
        print "Training finished!"

    # Command line parsing -- TODO use getopt
    argc = len(sys.argv)

    if argc < 2:
        print_usage()
    else:
        faq_file = sys.argv[1]

        if argc == 2:
            interactive_mode(faq_file)
        elif argc == 3:
            if sys.argv[2] == '--train':
                train_mode(faq_file)
            elif sys.argv[2] == '--test':
                test_mode(faq_file)
            elif sys.argv[2] == '--train-and-test':
                train_and_test_mode(faq_file)
            elif sys.argv[2].startswith('-'):
                print_usage()
            else:
                single_query_mode(faq_file, sys.argv[2])
        else:
            print_usage()


if __name__ == '__main__':
    main()

