# -*- coding: utf-8 -*-

import sys
import time
import unicodedata
import string
#import re
import subprocess
import json
import os

from faqfile import FaqFile
from searchengine import Crawler
from fastnn import FastNeuralNet

db_path = './db/'
valid_chars = string.ascii_letters + ' '
ignore_lemmas = ['ser', 'estar', 'parecer']


class FaqQuery:
    """Interface to train an later query FAQ file using a neural network"""

    def __init__(self, faq_file):
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

    def sanitize(self, s):
        wsz = ''.join(x for x in unicodedata.normalize('NFKD', unicode(s))
                        if x in valid_chars).lower()
        #print "sanitized %s -> %s" % (word, wsz)
        return wsz

    def get_word_ids(self, s):
        # TODO refactor!
        #
        # Tokenize and lemmatize using Freeling:
        try:
            output = subprocess.check_output(['./fl', s])
        except subprocess.CalledProcessError:
            print "Error: fl command has failed!"
            raise
        except OSError:
            print "Error: fl command not found! Aborting execution."
            raise

        # print output

        lemmas = json.loads(output)

        words = []

        # Only use verbs, nouns and PTs
        for k, v in lemmas.iteritems():
            tag = v['tag']
            if tag.startswith('V') or tag.startswith('N') or tag.startswith('PT'):
                    szlemma = self.sanitize(v['lemma'])
                    if len(szlemma) == 0 or szlemma in ignore_lemmas:
                        continue
                    words.append(szlemma)

        print "Keywords: ", words

        # Finally get IDs
        return [self.crawler.getwordid(word) for word in words]

    def train(self, iters=30):
        """Train neural network with the given FAQ file. Must be a valid JSON
        file"""

        total = len(self.faq.data)

        try:
            # train with iters iterations
            for i in range(iters):
                print "\n\n*********** ITERATION %d ***********\n\n" % (i + 1)

                # for each question in FAQ
                c = 1
                for k, v in self.faq.data.iteritems():
                    print "%d/%d Training question %s: %s" % (c, total, k, v)
                    starttime = time.time()
                    expurl = self.crawler.geturlid(k)
                    wordids = self.get_word_ids(v)

                    ########### CHECK ##########
                    # Train with bigrams and 3-grams ?
                    # Train passing *all* urlids ?
                    min_ngram_len = 2
                    max_ngram_len = 3
                    for ngram_len in range(min_ngram_len - 1, max_ngram_len):
                        for i in range(len(wordids) - ngram_len):
                            rwordids = wordids[i:i + ngram_len + 1]
                            self.nn.trainquery(rwordids, self.urlids, expurl)
                    ############################

                    print "Done in %f secs\n" % ((time.time() - starttime))
                    c += 1
        except KeyboardInterrupt:
            print "Aborted!"

    def query(self, q, N=10):
        """Get result for query q using the currently trained database"""

        urlids = self.urlids
        wordids = self.get_word_ids(q)
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


def main():
    def print_usage():
        print \
"""Usage:
    afipquery <faq_file> --train         ### Train using the given file. e.g afipquery --train afip_mono_faq.json
    afipquery <faq_file>                 ### Interactive mode. e.g. afipquery afip_mono_faq.json
    afipquery <faq_file> <query_string>  ### Single query mode. e.g afipquery afip_mono_faq.json "Como me inscribo?"
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
        fq.train()
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
            else:
                single_query_mode(faq_file, sys.argv[2])
        else:
            print_usage()


if __name__ == '__main__':
    main()

