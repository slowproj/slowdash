#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 8 August 2022 #

import sys
import pandas as pd


def go(filepath):
    df = pd.read_csv(filepath)
    items = []
    for row in df.itertuples():
        items.append('{"index":%d,"shape":"circle","attr":{"cx":%4f,"cy":%4f,"r":0.01}}' % (row.index, row.x, row.y))
    sys.stdout.write('{\n')
    sys.stdout.write('  "width": 1.0,\n')
    sys.stdout.write('  "height": 1.0,\n')
    sys.stdout.write('  "items": [\n    ')
    sys.stdout.write(',\n    '.join(items))
    sys.stdout.write('\n  ]\n')
    sys.stdout.write('}\n')


def go_svg(filepath):
    df = pd.read_csv(filepath)
    sys.stdout.write('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1000 1000">\n')
    sys.stdout.write('  <g transform="scale(1000,1000)">\n')
    for row in df.itertuples():
        sys.stdout.write('    <circle class="sd-data-item" data-index="%d" cx="%4f" cy="%4f" r="0.01"/>\n' % (row.index, row.x, row.y))
    sys.stdout.write('  </g>\n')
    sys.stdout.write('</svg>\n')

    
if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.stdout.write('Usage: %s CSV_FILE\n' % sys.argv[0])
        sys.exit(-1)
    else:
        go(sys.argv[1])
        #go_svg(sys.argv[1])
