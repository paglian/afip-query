#!/bin/bash
rm -f profile.dat
python -m cProfile -o profile.dat faqquery.py faqs/afip_mono_faq_full.json --train

