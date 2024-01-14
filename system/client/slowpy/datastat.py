# Created by Sanshiro Enomoto on 3 June 2023 #


import numpy as np


class HistogramBasicStat:
    def __init__(self, fields=['n', 'underflow', 'overflow', 'mean', 'std'], ndigits=4):
        self.fields = fields
        self.ndigits = ndigits

    def __call__(self, hist):
        n, sum, sum2 = 0, 0, 0
        for k in range(hist.scale.nbins):
            xk0, xk1 = hist.scale.get_bin_range_of(k)
            xk = (xk0 + xk1) / 2.0
            yk = hist.counts[k]
            n += yk
            sum += xk * yk
            sum2 += xk*xk * yk
            mean = None if n < 1 else sum/n
            std = None if n < 1 else np.sqrt(sum2/n - mean*mean)
        result = {}
        for key in self.fields:
            if key.lower() in ['n', 'counts', 'entries']:
                result[key] = n
            elif key.lower() == 'underflow':
                result[key] = hist.underflow
            elif key.lower() == 'overflow':
                result[key] = hist.overflow
            elif key.lower() == 'outliers':
                result[key] = hist.underflow + hist.overflow
            elif key.lower() in ['m', 'mean']:
                result[key] = round(mean, self.ndigits)
            elif key.lower() in ['sd', 'std', 'rms', 'sigma']:
                result[key] = round(std, self.ndigits)
            else:
                result[key] = None
        return result


class HistogramCountStat:
    def __init__(self, lower, upper, label=None):
        self.lower = lower
        self.upper = upper
        self.label = label if label is not None else 'Counts(%s,%s)' % (str(lower), str(upper))

    def find_bin(self, hist, value):
        if value < hist.scale.min:
            bin = 0
            frac = 0
        elif value >= hist.scale.max:
            bin = len(hist.counts)-1
            frac = 1
        else:
            bin = hist.scale.get_bin_of(value)
            low, high = hist.scale.get_bin_range_of(bin)
            frac = float(value - low) / (high - low)
        return (bin, frac)
        
    def __call__(self, hist):
        value = 0
        (lower_bin, lower_frac) = self.find_bin(hist, self.lower)
        (upper_bin, upper_frac) = self.find_bin(hist, self.upper)
        value += hist.counts[lower_bin] * (1-lower_frac)
        value += hist.counts[upper_bin] * upper_frac
        for k in range(lower_bin+1, upper_bin):
            value += hist.counts[k]
        return { self.label: round(10*value)/10.0 }


class Histogram2dBasicStat:
    def __init__(self, fields=['n', 'outliers', 'mean', 'sd'], ndigits=4):
        self.fields = fields
        self.ndigits = ndigits

    def __call__(self, hist2d):
        n, xsum, xsum2, ysum, ysum2 = 0, 0, 0, 0, 0
        for ky in range(hist2d.yscale.nbins):
            yk0, yk1 = hist2d.yscale.get_bin_range_of(ky)
            yk = (yk0 + yk1) / 2.0
            for kx in range(hist2d.xscale.nbins):
                xk0, xk1 = hist2d.xscale.get_bin_range_of(kx)
                xk = (xk0 + xk1) / 2.0
                zk = hist2d.counts[ky][kx]
                n += zk
                xsum += xk * zk
                ysum += yk * zk
                xsum2 += xk*xk * zk
                ysum2 += yk*yk * zk
        xmean = None if n < 1 else xsum/n
        ymean = None if n < 1 else ysum/n
        xstd = None if n < 1 else np.sqrt(xsum2/n - xmean*xmean)
        ystd = None if n < 1 else np.sqrt(ysum2/n - ymean*ymean)
            
        result = {}
        for key in self.fields:
            if key.lower() in ['n', 'counts', 'entries']:
                result[key] = n
            elif key.lower() in ['outliers', 'outofrange']:
                result[key] = hist2d.outliers
            elif key.lower() in ['m', 'mean']:
                result['x_' + key] = round(xmean, self.ndigits)
                result['y_' + key] = round(ymean, self.ndigits)
            elif key.lower() in ['sd', 'std', 'rms', 'sigma']:
                result['x_' + key] = round(xstd, self.ndigits)
                result['y_' + key] = round(ystd, self.ndigits)
            else:
                result[key] = None
        return result


class GraphYStat:
    def __init__(self, fields=['n', 'y-mean', 'y-std'], ndigits=4):
        self.fields = fields
        self.ndigits = ndigits

    def __call__(self, graph):
        result = {}
        for key in self.fields:
            key2 = key[2:] if key[0:2].lower() == 'y-' else key
            if key.lower() in ['n', 'counts', 'entries']:
                result[key] = len(graph.y)
            elif key2.lower() in ['m', 'mean']:
                result[key] = round(np.mean(graph.y), self.ndigits)
            elif key2.lower() in ['sd', 'std', 'rms', 'sigma']:
                result[key] = round(np.std(graph.y), self.ndigits)
            else:
                result[key] = None
        return result
