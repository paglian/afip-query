# -*- coding: utf-8 -*-

import json


class FaqFile:

    def __init__(self, faqfile):
        f = open(faqfile, 'r')
        self.data = json.load(f)
