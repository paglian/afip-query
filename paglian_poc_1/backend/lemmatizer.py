# -*- coding: utf-8 *-*

import subprocess
import json
import os

class Lemmatizer:

    def __init__(self):
        pass

    def lemmatize(self, sentence):
        """Lemmatizes the given sentence"""

        try:
            # fl returns a JSON string with format ... TODO document!
            # TODO Open socket to connect to the freeling server
            # (localhost:19191) and make the request instead of
            # invoking the fl command in this way:
            fl_path = os.path.dirname(os.path.abspath(__file__))
            output = subprocess.check_output([fl_path + '/fl', sentence])
        except subprocess.CalledProcessError:
            print "Error: fl command has failed!"
            raise
        except OSError:
            print "Error: fl command not found! Aborting execution."
            raise

        #print output

        return json.loads(output)

    def filter(self, lemmas, tags):
        """Filter out lemmas not having any tag in tags"""
        filtered = []

        for l in lemmas:
            current_tag = l['tag']
            for t in tags:
                if current_tag.startswith(t):
                    filtered.append(l)

        return filtered
