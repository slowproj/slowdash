#! /usr/bin/python

import json
from math import *

def draw():
    sch = {
        'width': 1000,
        'height': 1000,
        'items': []
    }
    
    rings = [ 
        sqrt(0.5473 + i * (20.25 - 0.5473) / 12.0) for i in range(0, 13) 
    ]

    for i in range(0, 4):
        r1 = rings[0] / 9.2
        phiA = 2*pi * (i/4.0)
        phiB = phiA + pi/2
        x0 = 0.5
        y0 = 0.5
        x1A = 0.5 + r1 * cos(phiA)
        y1A = 0.5 - r1 * sin(phiA)
        x1B = 0.5 + r1 * cos(phiB)
        y1B = 0.5 - r1 * sin(phiB)
        pathdata = (x0, y0, x1A, y1A, r1, r1, x1B, y1B)
        pathstring = "M%.3f,%.3f L%.3f,%.3f A%.3f,%.3f 0 0,0 %.3f,%.3f z" % pathdata
        sch['items'].append({
            'index': i,
            'shape':'path', 
            'attr': {'d': pathstring }
        })

    for i in range(0, 144):
        r0 = rings[i/12] / 9.2
        r1 = rings[i/12+1] / 9.2
        phiA = 2*pi * ((i%12)/12.0) - ((i/12+1)%2) * pi/12
        phiB = phiA + pi/6
        x0A = 0.5 + r0 * cos(phiA)
        y0A = 0.5 - r0 * sin(phiA)
        x0B = 0.5 + r0 * cos(phiB)
        y0B = 0.5 - r0 * sin(phiB)
        x1A = 0.5 + r1 * cos(phiA)
        y1A = 0.5 - r1 * sin(phiA)
        x1B = 0.5 + r1 * cos(phiB)
        y1B = 0.5 - r1 * sin(phiB)
        pathdata = (x0A, y0A, r0, r0, x0B, y0B, x1B, y1B, r1, r1, x1A, y1A)
        pathstring = "M%.3f,%.3f A%.3f,%.3f 0 0,0 %.3f,%.3f L%.3f,%.3f A%.3f %.3f 0 0,1 %.3f,%.3f z" % pathdata
        sch['items'].append({
            'index': i,
            'shape':'path', 
            'attr': {'d': pathstring }
        })
        
    return sch


if __name__ == '__main__':
    print json.dumps(draw(), indent=4)
