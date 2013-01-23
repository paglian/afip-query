# -*- coding: utf-8 *-*

import subprocess
import json


class Lemmatizer:

    def __init__(self):
        pass

    def lemmatize(self, sentence):
        """Lemmatizes the given sentence"""

        try:
            # lemmatize using an external command that returns a JSON string
            output = subprocess.check_output(['./fl', sentence])
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
