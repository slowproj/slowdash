# Created by Sanshiro Enomoto on 21 October 2023 #


import sys, os, time, json

import numpy as np
from matplotlib import pyplot as mpl_plt
from matplotlib import colors
import matplotlib.animation as animation

from .histograms import Histogram, Histogram2d
from .graphs import Graph
from .store import DataStore, create_datastore_from_url


class Axes:
    def __init__(self, figure, *args):
        self.figure = figure
        (nrows, ncols, index) = args
        self.mpl_axes = figure.mpl_figure.add_subplot(nrows, ncols, index)
        self.xaxis = self.mpl_axes.xaxis
        self.yaxis = self.mpl_axes.yaxis
        
        self.config = {
            "type": "plot",
            "plots": [],
            "axes": { "xfixed": False, "yfixed": False, "xlog": False, "ylog": False },
            "legend": { "style": "hidden" }
        }
        self.use_mpl_colors = True
        

    def set_title(self, label, **kwargs):
        self.config['axes']['title'] = label
        self.mpl_axes.set_title(label, **kwargs)

    def set_xlabel(self, label, **kwargs):
        self.config['axes']['xtitle'] = label
        self.mpl_axes.set_xlabel(label, **kwargs)

    def set_ylabel(self, label, **kwargs):
        self.config['axes']['ytitle'] = label
        self.mpl_axes.set_ylabel(label, **kwargs)

    def set_xlim(self, left=None, right=None, **kwargs):
        self.config['axes']['xfixed'] = True
        self.config['axes']['xmin'] = left
        self.config['axes']['xmax'] = right
        self.mpl_axes.set_xlim(left, right, **kwargs)

    def set_ylim(self, bottom=None, top=None, **kwargs):
        self.config['axes']['yfixed'] = True
        self.config['axes']['ymin'] = bottom
        self.config['axes']['ymax'] = top
        self.mpl_axes.set_ylim(bottom, top, **kwargs)

    def set_xscale(self, value, **kwargs):
        self.config['axes']['xlog'] = (value == 'log')            
        self.mpl_axes.set_xscale(value, **kwargs)

    def set_yscale(self, value, **kwargs):
        self.config['axes']['ylog'] = (value == 'log')
        self.mpl_axes.set_yscale(value, **kwargs)

    def legend(self, *args, **kwargs):
        self.config['legend']['style'] = 'box'
        self.mpl_axes.legend(*args, **kwargs)

        
    def cla(self):
        self.config['plots'] = []
        self.mpl_axes.cla()


    def plot(self, obj, *args, **kwargs):
        if type(obj) is str and 'data' in kwargs:
            obj = kwargs['data'][obj]
            if len(args) > 0 and type(args[0]) is str:
                args[0] = kwargs['data'][args[0]]
                    
        nx, ny = 0, 0
        if isinstance(obj, list) or isinstance(obj, np.ndarray):
            nx = len(obj)
            if len(args) == 1 and isinstance(args[0], list):
                ny = len(args[0])

        if nx > 0:
            graph = Graph(slowplot.create_name(kwargs.get('label', None), 'plot'))
            if len(args) == 0 or type(args[0]) is str:
                graph.x = [ k for k in range(nx) ]
                graph.y = [ float(xk) for xk in obj ]
            else:
                graph.x = [ float(xk) for xk in obj ]
                graph.y = [ float(yk) for yk in args[0] ]
            obj = graph
            
        if len(args) > 0 and type(args[-1]) is str:
            kwargs.update(self._decode_format(args[-1]))
            
        if isinstance(obj, Histogram):
            return self._draw_histogram(obj, **kwargs)
        elif isinstance(obj, Histogram2d):
            return self._draw_histogram2d(obj, **kwargs)
        elif isinstance(obj, Graph):
            return self._draw_graph(obj, **kwargs)

        return None

                
    def errorbar(self, x, y, yerr=None, xerr=None, **kwargs):
        graph = Graph(slowplot.create_name(kwargs.get('label', None), 'plot'))
        graph.x = [ float(xk) for xk in x ]
        graph.y = [ float(xk) for xk in x ]
        if xerr is not None:
            graph.x_err = [ float(xk) for xk in xerr ]
        if xerr is not None:
            graph.y_err = [ float(xk) for xk in yerr ]

        return self._draw_graph(graph, **kwargs)

    
    def hist(self, values, bins=None, **kwargs):
        if type(values) is str and 'data' in kwargs:
            values = kwargs['data'][values]
                
        if bins is None:
            counts, edges = np.histogram(values)
        else:
            counts, edges = np.histogram(values, bins)
        name = slowplot.create_name(kwargs.get('label', None), 'hist')
        hist = Histogram(name, len(edges)-1, edges[0], edges[-1])
        hist.counts = counts.tolist()
        
        return self._draw_histogram(hist, **kwargs)
        

    def hist2d(self, x, y, bins=None, weights=None, **kwargs):
        if 'data' in kwargs:
            if type(x) is str:
                x = kwargs['data'][x]
            if type(y) is str:
                y = kwargs['data'][y]
                
        if bins is None:
            counts, xedges, yedges = np.histogram2d(x, y, weights=weights)
        else:
            counts, xedges, yedges = np.histogram2d(x, y, bins, weights=weights)
        name = slowplot.create_name(kwargs.get('label', None), 'hist2d')
        hist2d = Histogram2d(name, len(xedges)-1, xedges[0], xedges[-1], len(yedges)-1, yedges[0], yedges[-1])
        for yk in range(len(yedges)-1):
            hist2d.counts[yk][:] = counts[yk][:].tolist()
        
        return self._draw_histogram2d(hist2d, **kwargs)
        

    def scatter(self, x, y, s=None, c=None, marker=None, **kwargs):
        kwargs['markersize'] = s if s is not None else 5
        kwargs['marker'] = marker if marker is not None else 'o'
        if c is not None:
            kwargs['color'] = c
        if 'linewidth' not in kwargs:
            kwargs['linewidth'] = 0
            
        return self.plot(x, y, **kwargs)

    
    def _decode_format(self, fmt):
        opts = {}
        
        if colors.is_color_like(fmt):
            opts['color'] = fmt
            return opts
            
        for ch in fmt:
            if ch in '.,ov^<>12348spP*hH+xXDd|_':
                opts['marker'] = ch
            elif ch in 'bgrcmykw':
                opts['color'] = {
                    'b': 'blue',
                    'g': 'green',
                    'r': 'red',
                    'c': 'cyan',
                    'm': 'magenta',
                    'y': 'yellow',
                    'k': 'black',
                    'w': 'white'
                }[ch]
                
        return opts
    
        
    def _get_opts(self, **kwargs):
        opts = {}
        if 'color' in kwargs:
            opts['color'] = kwargs['color']
        if 'alpha' in kwargs:
            opts['opacity'] = kwargs['alpha']
        if 'linewidth' in kwargs:
            opts['line_width'] = kwargs['linewidth']
        if 'marker' in kwargs:
            marker = kwargs['marker'][0]
            if marker in '.o':
                opts['marker_type'] = 'circle'
            elif marker in ',s':
                opts['marker_type'] = 'square'
            elif marker in 'dD':
                opts['marker_type'] = 'diamond'
            elif marker in 'v^<>':
                opts['marker_type'] = 'triangle'
            else:
                opts['marker_type'] = 'opencircle'
            opts['marker_size'] = 5
        if 'markersize' in kwargs:
            opts['marker_size'] = kwargs['markersize']
        return opts

            
    def _draw_graph(self, graph, **kwargs):
        obj = {'type': 'graph', 'channel': graph.name }
        obj.update(self._get_opts(**kwargs))
        self.config['plots'].append(obj)

        xerr = graph.x_err if graph.has_x_err() else None
        yerr = graph.y_err if graph.has_y_err() else None
        if xerr is None and yerr is None:
            p = self.mpl_axes.plot(graph.x, graph.y, **kwargs)
        else:
            p = self.mpl_axes.errorbar(graph.x, graph.y, xerr=xerr, yerr=yerr, **kwargs)
        if self.use_mpl_colors:
            obj['color'] = colors.to_hex(p[0].get_color())

        if slowplot.datastore is not None:
            slowplot.datastore.write_object(graph)
            
        return p
            

    def _draw_histogram(self, hist, **kwargs):
        obj = { 'type': 'histogram', 'channel': hist.name }
        obj.update(self._get_opts(**kwargs))
        self.config['plots'].append(obj)
        
        bins = np.linspace(hist.scale.min, hist.scale.max, hist.scale.nbins+1, endpoint=True).tolist()
        
        n, b, p = self.mpl_axes.hist(bins[:-1], bins, weights=hist.counts, **kwargs)
        if self.use_mpl_colors:
            obj['color'] = colors.to_hex(p[0].get_facecolor())
            obj['opacity'] = 1

        if slowplot.datastore is not None:
            slowplot.datastore.write_object(hist)
            
        return (n, b, p)

                   
    def _draw_histogram2d(self, hist2d, **kwargs):
        obj = { 'type': 'histogram2d', 'channel': hist2d.name }
        obj.update(self._get_opts(**kwargs))
        self.config['plots'].append(obj)
        
        xbins = np.linspace(hist2d.xscale.min, hist2d.xscale.max, hist2d.xscale.nbins+1, endpoint=True).tolist()
        ybins = np.linspace(hist2d.yscale.min, hist2d.yscale.max, hist2d.yscale.nbins+1, endpoint=True).tolist()
        x, y, weights = [], [], []
        for ky in range(hist2d.yscale.nbins):
            x.extend(xbins[:-1])
            y.extend([ybins[ky]]*(len(xbins)-1))
            weights.extend(hist2d.counts[ky])
        result = self.mpl_axes.hist2d(x, y, bins=[xbins, ybins], weights=weights, **kwargs)

        if slowplot.datastore is not None:
            slowplot.datastore.write_object(hist2d)
            
        return result

                   
    def _get_config(self):
        if len(self.config.get('plots')) > 0:
            return self.config
        else:
            return None
    

    def grid(self, visible=None, which='major', axis='both', **kwargs):
        self.mpl_axes.grid(visible, which, axis, **kwargs)
        
    def get_xaxis(self):
        return self.xaxis
    
    def get_yaxis(self):
        return self.yaxis
    
                   
        
class Figure:
    def __init__(self, **kwargs):
        self.axes_list = []
        self.mpl_figure = mpl_plt.figure(**kwargs)
        self.grid = (1, 1)

        
    def add_subplot(self, nrows=1, ncols=1, index=1):
        axes = Axes(self, nrows, ncols, index)
        self.axes_list.append(axes)
        self.grid = (nrows, ncols)
        return axes

    
    def _get_config(self):
        config = {
            'control': {
                'reload': 0,
                'grid': { 'rows': self.grid[0], 'columns': self.grid[1] }
            },
            'panels': []
        }
        for ax in self.axes_list:
            ax_config = ax._get_config()
            if ax_config is not None:
                config['panels'].append(ax_config)
            
        return config

        
    def subplots_adjust(self, **kwargs):
        self.mpl_figure.subplots_adjust(**kwargs)
            
    def savefig(self, *args, **kwargs):
        self.mpl_figure.savefig(*args, **kwargs)

            

class slowplot:
    datastore = None
    figure_list = []
    animation_list = []
    recurrence_interval = 0
    sequence = 0

    
    @classmethod
    def set_datastore(cls, datastore=None):
        if datastore is None:
            datastore = 'sqlite:///SlowStore.db'
        if type(datastore) == str:
            cls.datastore = create_datastore_from_url(datastore)
            if cls.datastore is None:
                sys.stderr.write('invalid DataStore name: %s\n' % datastore)
        else:
            cls.datastore = datastore

        
    @classmethod
    def create_name(cls, label, prefix):
        if label is None or len(label) == 0:
            cls.sequence = cls.sequence + 1
            return '%s%03d' % (prefix, cls.sequence)
        name = label[0] if label[0].isalpha() else '_'
        for i in range(1, len(label)):
            name += label[i] if label[i].isalnum() or label[i] in [ '-', '.' ] else '_'
        return name

        
    @classmethod
    def figure(cls, **kwargs):
        fig = Figure(**kwargs)
        cls.figure_list.append(fig)
        return fig

    
    @classmethod
    def subplots(cls, nrows=1, ncols=1, **kwargs):
        fig = cls.figure(**kwargs)
        for row in range(nrows):
            for col in range(ncols):
                fig.add_subplot(nrows, ncols, len(fig.axes_list)+1)
        
        return fig, (fig.axes_list[0] if len(fig.axes_list) == 1 else fig.axes_list)

    
    @classmethod
    def plot(cls, *args, **kwargs):
        if len(cls.figure_list) == 0:
            cls.subplots()
        cls.figure_list[-1].axes_list[-1].plot(*args, **kwargs)


    @classmethod
    def errorbar(cls, *args, **kwargs):
        if len(cls.figure_list) == 0:
            cls.subplots()
        cls.figure_list[-1].axes_list[-1].errorbar(*args, **kwargs)


    @classmethod
    def hist(cls, *args, **kwargs):
        if len(cls.figure_list) == 0:
            cls.subplots()
        cls.figure_list[-1].axes_list[-1].hist(*args, **kwargs)

    @classmethod
    def hist2d(cls, *args, **kwargs):
        if len(cls.figure_list) == 0:
            cls.subplots()
        cls.figure_list[-1].axes_list[-1].hist2d(*args, **kwargs)

    @classmethod
    def scatter(cls, *args, **kwargs):
        if len(cls.figure_list) == 0:
            cls.subplots()
        cls.figure_list[-1].axes_list[-1].scatter(*args, **kwargs)

        
    @classmethod
    def show(cls):
        cls.sequence = 0
        mpl_plt.show()    # show calls the recurrent task


    @classmethod
    def set_recurrence(cls, task_func, interval=1000):
        if len(cls.animation_list) > 0:
            #... update callbacks
            return

        def exec_func(data):
            for fig in cls.figure_list:
                for ax in fig.axes_list:
                    ax.cla()
            task_func()
            cls.sequence = 0

        def idle_func(data):
            pass
        
        cls.recurrence_interval = interval
        
        if len(cls.figure_list) == 0:
            cls.subplots()
            
        for i in range(0, len(cls.figure_list)):
            cls.animation_list.append(animation.FuncAnimation(
                cls.figure_list[i].mpl_figure,
                exec_func if i == 0 else idle_func,
                interval=cls.recurrence_interval,
                cache_frame_data=False
            ))


    @classmethod
    def generate_slowdash_config(cls, filepath=None):
        if len(cls.figure_list) == 0:
            return
        
        if filepath is None:
            try:
                import __main__
                name = os.path.splitext(os.path.basename(__main__.__file__))[0]
            except:
                # in Notebook etc.
                name = 'slowpy-notebook'
            filepath = 'slowplot-%s.json' % name

        with open(filepath, 'w') as f:
            config = cls.figure_list[-1]._get_config()
            config['meta'] = { 'name': name }
            config['control']['reload'] = int(cls.recurrence_interval/1000)
            json.dump(config, f, indent=4)
        sys.stderr.write('SlowDash config file generated: %s\n' % filepath)


    @classmethod
    def title(cls, label, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_title(label, **kwargs)

    @classmethod
    def xlabel(cls, label, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_xlabel(label, **kwargs)

    @classmethod
    def ylabel(cls, label, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_ylabel(label, **kwargs)

    @classmethod
    def xlim(cls, left=None, right=None, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_xlim(left, right, **kwargs)

    @classmethod
    def ylim(cls, bottom=None, top=None, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_ylim(bottom, top, **kwargs)

    @classmethod
    def xscale(cls, value, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_xscale(value, **kwargs)

    @classmethod
    def yscale(cls, value, **kwargs):
        if len(cls.figure_list) and len(cls.figure_list[-1].axes_list):
            cls.figure_list[-1].axes_list[-1].set_yscale(value, **kwargs)

    @classmethod
    def legend(cls, *args, **kwargs):
        if len(cls.figure_list):
            for ax in cls.figure_list[-1].axes_list:
                cls.figure_list[-1].axes_list[-1].legend(*args, **kwargs)

    @classmethod
    def grid(cls, *args, **kwargs):
        if len(cls.figure_list):
            for ax in cls.figure_list[-1].axes_list:
                cls.figure_list[-1].axes_list[-1].grid(*args, **kwargs)
        
    @classmethod
    def subplots_adjust(cls, *args, **kwargs):
        if len(cls.figure_list):
            cls.figure_list[-1].subplots_adjust(*args, **kwargs)
            
    @classmethod
    def savefig(cls, *args, **kwargs):
        if len(cls.figure_list):
            cls.figure_list[-1].savefig(*args, **kwargs)

