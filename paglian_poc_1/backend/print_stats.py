#!/usr/bin/python

import pstats

p = pstats.Stats('profile.dat')

p.strip_dirs().sort_stats('cumulative').print_stats()

