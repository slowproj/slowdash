# Created by Sanshiro Enomoto on 17 July 2024 #


import numpy as np
from .basetypes import DataElement


class HistogramScale:
    def __init__(self, nbins, range_min, range_max):
        self.nbins = max(nbins, 0)
        self.min = min(range_min, range_max)
        self.max = max(range_min, range_max)
        if not (self.min < self.max):
            self.nbins = 0
        elif self.nbins > 0:
            self.bin_width = (self.max - self.min) / self.nbins

            
    def get_bin_of(self, value):
        if self.nbins <= 0 or value < self.min or value >= self.max:
            return None
        return int((value - self.min) / self.bin_width)

    
    def get_bin_range_of(self, bin_index):
        if self.nbins <= 0:
            return (None, None)
        left = self.min + bin_index * self.bin_width
        right = left + self.bin_width
        return (left, right)


    
class Histogram(DataElement):
    def __init__(self, name, nbins, range_min, range_max):
        super().__init__()
        self.name = name
        self.scale = HistogramScale(nbins, range_min, range_max)
        if self.scale.nbins > 0:
            self.counts = [0] * self.scale.nbins
        else:
            self.counts = []
        self.overflow, self.underflow = 0, 0

        
    def clear(self):
        super().clear()
        self.counts[:] = 0
        self.overflow, self.underflow = 0, 0

        
    def fill(self, value, weight=1):
        bin = self.scale.get_bin_of(value)
        if bin is not None:
            self.counts[bin] += weight
        else:
            if value < self.scale.min:
                self.underflow += weight
            if value >= self.scale.max:
                self.overflow += weight

                
    def rebin(self, nbins, range_min, range_max):
        if nbins <= 0:
            return
        new_scale = HistogramScale(nbins, range_min, range_max)
        new_counts = [0] * new_scale.nbins
        for bin in range(self.scale.nbins):
            (left, right) = self.scale.get_bin_range_of(bin)
            for k in range(int(self.counts[bin])):
                value = np.random.uniform(left, right)
                new_bin = new_scale.get_bin_of(value)
                if new_bin is not None:
                    new_counts[new_bin] += 1
        self.scale = new_scale
        self.counts = new_counts

        
    def to_json(self):
        return { **super().to_json(),  **{
            'bins': { 'min': self.scale.min, 'max': self.scale.max },
            'counts': self.counts
        }}

    
    @staticmethod
    def from_json(name, obj):
        bins, counts = obj['bins'], obj['counts']
        hist = Histogram(name, len(counts), bins['min'], bins['max'])
        hist.counts = counts
        return hist
        

    
class Histogram2d(DataElement):
    def __init__(self, name, xnbins, xrange_min, xrange_max, ynbins, yrange_min, yrange_max):
        super().__init__()
        self.name = name
        self.xscale = HistogramScale(xnbins, xrange_min, xrange_max)
        self.yscale = HistogramScale(ynbins, yrange_min, yrange_max)
        if self.xscale.nbins > 0 and self.yscale.nbins > 0:
            self.counts = [ [0]*self.xscale.nbins for yslice in range(self.yscale.nbins) ]
        else:
            self.counts = None
        self.outliers = 0

        
    def clear(self):
        super().clear()
        for yslice in self.counts:
            yslice[:] = 0
        self.outliers = 0

        
    def fill(self, x, y, weight=1):
        xbin = self.xscale.get_bin_of(x)
        ybin = self.yscale.get_bin_of(y)
        if self.counts is None or xbin is None or ybin is None:
            self.outliers += weight
        else:
            self.counts[ybin][xbin] += weight

                
    def to_json(self):
        return { **super().to_json(),  **{
            'xbins': { 'min': self.xscale.min, 'max': self.xscale.max },
            'ybins': { 'min': self.yscale.min, 'max': self.yscale.max },
            'counts': self.counts
        }}

    
    @staticmethod
    def from_json(name, obj):
        xbins, ybins, counts = obj['xbins'], obj['ybins'], obj['counts']
        hist = Histogram2d(name, len(counts[0]), xbins['min'], xbins['max'], len(counts), ybins['min'], ybins['max'])
        hist.counts = counts
        return hist



    
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
                result[key] = (round(mean, self.ndigits) if mean is not None else 'NaN')
            elif key.lower() in ['sd', 'std', 'rms', 'sigma']:
                result[key] = (round(std, self.ndigits) if std is not None else 'NaN')
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
    
