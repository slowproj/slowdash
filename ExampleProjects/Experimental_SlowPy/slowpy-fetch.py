#! /usr/bin/env python3        

from slowpy.data import SlowFetch

sf = SlowFetch('http://localhost:18881')

print(sf.channels())
print(sf.dataframe(['ch00', 'ch01'], start=-3600,resample=600))
