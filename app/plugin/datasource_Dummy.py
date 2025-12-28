# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, logging, datetime
from sd_datasource import DataSource

from math import *
import numpy as np
    
    
class DataSource_Dummy(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.ts_channels = params.get('timeseries', [])
        self.hist_channels = params.get('histogram', [])
        self.hist2d_channels = params.get('histogram2d', [])
        self.graph_channels = params.get('graph', [])
        self.clock_channel_name = params.get('clock', {}).get('name', None)
        self.log_channel_name = params.get('log', {}).get('name', None)

        
    def get_channels(self):
        channels = []
        for ch in self.ts_channels:
            name = ch.get('name', None)
            if name is not None:
                channels.append({'name': name})
        for ch in self.hist_channels:
            name = ch.get('name', None)
            if name is not None:
                channels.append({'name': name, 'type': 'histogram'})
        for ch in self.hist2d_channels:
            name = ch.get('name', None)
            if name is not None:
                channels.append({'name': name, 'type': 'histogram2d'})
        for ch in self.graph_channels:
            name = ch.get('name', None)
            if name is not None:
                channels.append({'name': name, 'type': 'graph'})
        if self.clock_channel_name is not None:
            channels.append({'name': self.clock_channel_name, 'type': 'tree'})
        if self.log_channel_name is not None:
            channels.append({'name': self.log_channel_name, 'type': 'table'})
                
        return channels

    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last', filler='fillna', envelope=0):
        result = {}
        for ch in self.ts_channels:
            name = ch.get('name', None)
            if name is None or name not in channels:
                continue
            series = { 't': [], 'x': []}
            formula = str(ch.get('formula', '0'))
            noise = ch.get('noise', 0)
            walk = ch.get('walk', 0)
            decay = ch.get('decay', 0)
            intervals = ch.get('intervals', 10)
            
            start, n, xw = to-length, int(length/intervals), 0
            for k in range(n):
                dt = k * intervals
                t = start+dt
                xw = (1-decay) * xw + np.random.normal(0, walk)
                x = eval(formula) + np.random.normal(0, noise) + xw

                series['t'].append(dt)
                series['x'].append(float('%.4g'%x))
            result[name] = {'start': start, 'length': length, 't': series['t'], 'x': series['x'] }

        if resampling is None:
            return result
            
        return self.resample(result, length, to, resampling, reducer, filler, envelope)

    
    def get_object(self, channels, length, to):
        result = {}

        for ch in self.hist_channels:
            name = ch.get('name', None)
            if name is None or name not in channels:
                continue

            pdf = str(ch.get('pdf', None))
            entries = ch.get('entries', 100)
            samples = []
            if pdf is not None:
                try:
                    samples = [ eval(pdf) for k in range(entries) ]
                except Exception as e:
                    logging.error('error in PDF: %s' % str(e))

            if len(samples) > 0:
                span = max(samples) - min(samples)
                binmin, binmax = min(samples)-0.1*span, max(samples)+0.1*span
            else:
                binmin, binmax = 0, 1
            nbins = int(len(samples)/10)                
            
            bins = ch.get('bins', None)
            if bins is not None:
                nbins = bins.get('n', nbins)
                binmin = bins.get('min', binmin)
                binmax = bins.get('max', binmax)
            if not (binmax > binmin):
                binmin, binmax = 0, 1

            counts = [ 0 for bin in range(nbins) ]
            for xk in samples:
                ik = int(nbins * (xk - binmin) / (binmax - binmin))
                if ik >= 0 and ik < nbins:
                    counts[ik] = counts[ik] + 1

            result[name] = {
                'start': to-length, 'length': length,
                't': to,
                'x': {
                    'bins': { 'min': binmin, 'max': binmax },
                    'counts': counts,
                    '_stat': {
                        'Entries': len(samples),
                        'Mean': '%.3f' % np.mean(samples),
                        'Std': '%.3f' % np.std(samples)
                    }
                }
            }

            
        for ch in self.hist2d_channels:
            name = ch.get('name', None)
            if name is None or name not in channels:
                continue

            pdf = str(ch.get('pdf', None))
            entries = ch.get('entries', 100)
            xbins = ch.get('xbins', {'n': 10, 'min': 0, 'max': 10} )
            ybins = ch.get('ybins', {'n': 10, 'min': 0, 'max': 10} )

            x, y = [], []
            if pdf is not None:
                try:
                    for k in range(entries):
                        sample = eval(pdf)
                        x.append(sample[0])
                        y.append(sample[1])
                except Exception as e:
                    logging.error('error in PDF: %s' % str(e))
                    
            xedges = np.linspace(xbins.get('min'), xbins.get('max'), xbins.get('n')+1, endpoint=True).tolist()
            yedges = np.linspace(ybins.get('min'), ybins.get('max'), ybins.get('n')+1, endpoint=True).tolist()
            counts = np.histogram2d(x, y, [xedges, yedges])[0].T.tolist()
            
            result[name] = {
                'start': to-length, 'length': length,
                't': to,
                'x': {
                    'xbins': { 'min': xbins.get('min'), 'max': xbins.get('max') },
                    'ybins': { 'min': ybins.get('min'), 'max': ybins.get('max') },
                    'counts': counts
                }
            }

            
        for ch in self.graph_channels:
            name = ch.get('name', None)
            if name is None or name not in channels:
                continue

            entries = ch.get('entries', 100)
            mean = ch.get('mean', 1)
            x, y, y_err = [], [], []
            for i in range(entries):
                yk = float(np.random.poisson(mean, 1)[0])
                x.append(i)
                y.append(yk)
                y_err.append(round(np.sqrt(yk), 2))
                
            result[name] = {
                'start': to-length, 'length': length,
                't': to,
                'x': { 'x': x, 'y': y, 'y_err': y_err }
            }

            
        if self.clock_channel_name in channels:
            result[self.clock_channel_name] = {
                'start': to-length, 'length': length,
                't': to,
                'x': {
                    'tree': {
                        'date': datetime.datetime.fromtimestamp(to).strftime('%a, %d %b %Y'),
                        'time': datetime.datetime.fromtimestamp(to).strftime('%H:%M:%S')
                    }
                }
            }

            
        if self.log_channel_name in channels:
            table = []
            interval = 10
            start, n = to-length, int(length/interval)
            if n > 100:
                n = 100
            times = [ start + interval * k for k in range(n) ]
            for tk in times:
                if np.random.uniform(0, 1) < 0.8:
                    table.append([
                        datetime.datetime.fromtimestamp(tk).isoformat(),
                        'good',
                        'Everything is fine'
                    ])
                else:
                    table.append([
                        datetime.datetime.fromtimestamp(tk).isoformat(),
                        'bad',
                        'Something went wrong'
                    ])
            result[self.log_channel_name] = {
                'start': to-length, 'length': length,
                't': to,
                'x': {
                    'columns': ['time', 'status', 'message'],
                    'table': table
                }
            }

            
        return result
