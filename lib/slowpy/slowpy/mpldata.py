# Created by Sanshiro Enomoto on 7 August 2025 #

import uuid
import numpy as np
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import matplotlib.collections as mcollections
import matplotlib


def _convert_marker(marker):
    """converts Matplotlib marker to SlowDash marker
    """
    
    if marker in '.o':
        return 'circle'
    elif marker in ',s':
        return 'square'
    elif marker in 'dD':
        return 'diamond'
    elif marker in 'v^<>':
        return 'triangle'
    elif marker != 'None':
        return 'open_circle'
    else:
        return ''
        
    
def _extract_plots_and_errorbars(ax, legend_labels):
    """extracts Plots and Errorbars from Matplotlib Axes and convert them to SlowDash Graphs
    Parameters:
      see axes_to_plot() below
    Retrun Values:
      array of dicts, where each dict is a SlowDash graph
    Note:
      - in Axes, plots are stored as Line2D, and errorbars are as combination of
        Line2D (central values) and LineCollection (error bars).
        Matching the central values and error bars are tricky: here, colors are used.
    """
    
    errorbars = {}
    collections = [
        artist for artist in ax.get_children()
        if isinstance(artist, mcollections.LineCollection)
    ]
    for i, c in enumerate(collections):
        colors = c.get_color()
        color = matplotlib.colors.to_hex(colors[0]) if len(colors) > 0 else ''
        graph = {
            '_attr': {
                'name': f'errorbar{i:02d}',
            },
            'x': [], 'y': [], 'x_err': [], 'y_err': []
        }
        for (x0, y0), (x1, y1) in c.get_segments():
            if x0 == x1:
                graph['x'].append(x0)
                graph['y'].append((y0+y1)/2)
                graph['y_err'].append(abs(y1-y0)/2)
            if y0 == y1:
                graph['x_err'].append(abs(x1-x0)/2)
        if len(color) > 0:
            errorbars[color] = graph
        
    plots = []
    lines = ax.get_lines()  # this includes errorbars
    for line in lines:
        color = line.get_color()
        marker = _convert_marker(line.get_marker())
        line_width = 1 if line.get_linestyle() == '-' else 0
        graph = {
            '_attr': {
                'name': '',
                'label': '',
                'color': color,
                'marker_type': marker,
                'marker_size': 4 if len(marker) > 0 else 0,
                'line_width': line_width
            },
            'x': line.get_xdata().tolist(),
            'y': line.get_ydata().tolist(),
        }

        errorbar = errorbars.get(color, None)
        if errorbar:
            if len(errorbar['x_err']) == len(graph['x']):
                graph['x_err'] = errorbar['x_err']
            if len(errorbar['y_err']) == len(graph['y']):
                graph['y_err'] = errorbar['y_err']
            name = errorbar['_attr']['name']
            default_label = 'plt.errorbars(...)'
        else:
            name = f'plot{len(plots):02d}'
            default_label = 'plt.plot(...)'
                
        graph['_attr']['name'] = name
        graph['_attr']['label'] = legend_labels.get(line, default_label)
                
        plots.append(graph)

    return plots

    
def _extract_hists(ax, legend_labels):
    """extracts Histograms from Matplotlib Axes and convert them to SlowDash Histograms
    Parameters:
      see axes_to_plot() below
    Retrun Values:
      array of dicts, where each dict is a SlowDash histogram
    Note:
      - In Axes, all histograms are merged and stored as a "patches", which is an array of Rectangles.
        Separating indivisual histogram is tricky: here, non-adjacent bins are used.
    """
    
    hists = []
    rects = [
        p for p in ax.patches
        if isinstance(p, mpatches.Rectangle) and p.get_y() == 0
    ]

    x, w, n, label, color = [], [], [], None, None
    def _make_hist():
        if not x:
            return None
        if np.max(w) - np.min(w) > 1e-8 * np.mean(w):
            bins = x + [ x[-1] + w[-1] ]
        else:
            bins = { 'min': x[0], 'max': x[-1] + w[0] }
        return {
            '_attr': {
                'name': f'hist{len(hists):02d}',
                'label': label if label is not None else 'plt.hist(...)',
                'color': matplotlib.colors.to_hex(color) if color is not None else '',
            },
            'bins': bins,
            'counts': n,
        }
            
    for r in rects:
        xk, wk, nk = r.get_x(), r.get_width(), r.get_height()
        label_k = legend_labels.get(r, None)
        color_k = r.get_facecolor()
        if x and xk < x[-1] + w[-1]/2:
            hists.append(_make_hist())
            x, w, n, label, color = [], [], [], None, None

        x.append(xk)
        w.append(wk)
        n.append(nk)
        if label_k is not None:
            label = label_k
        if color_k is not None:
            color = color_k

    if x:
        hists.append(_make_hist())
            
    return hists


def _extract_scatters(ax, legend_labels):
    """extracts Scatters from Matplotlib Axes and convert them to SlowDash Graphs
    Parameters:
      see axes_to_plot() below
    Retrun Values:
      array of dicts, where each dict is a SlowDash graph
    """
    
    scatters = []    
    collections = [
        collection for collection in ax.collections
        if isinstance(collection, mcollections.PathCollection)
    ]
    
    for c in collections:
        offsets = c.get_offsets()
        sizes = c.get_sizes()
        colors = c.get_facecolors()
            
        label = legend_labels.get(c, 'plt.scatters(...)')
        color = matplotlib.colors.to_hex(colors[0]) if len(colors) > 0 else 'none'
        marker_size = float(sizes[0])/10.0 if len(sizes) > 0 else 3

        graph = {
            '_attr': {
                'name': f'scatter{len(scatters):02d}',
                'label': label,
                'color': color,
                'marker': 'circle',
                'marker_size': marker_size,
                'line_width': 0,
            },
            'x': [], 'y': []
        }

        x, y = graph['x'], graph['y']
        for k, (xk, yk) in enumerate(offsets):
            x.append(float(xk))
            y.append(float(yk))

        scatters.append(graph)

    return scatters


def axes_to_plot(ax):
    """converts a Matplotlib Axes to a SlowDash Plot
    Parameters:
      - ax: instance of a Matplotlib Axes
    Return Value:
      - A Python dict representing SlowDash Plot
    TODO:
      - extract hist2d
    """
    
    legend_labels = {}
    handles, labels = ax.get_legend_handles_labels()
    for h, l in zip(handles, labels):
        if isinstance(h, matplotlib.container.ErrorbarContainer):
            legend_labels[h.lines[0]] = l
        else:
            legend_labels[h] = l

    plots = _extract_plots_and_errorbars(ax, legend_labels)
    hists = _extract_hists(ax, legend_labels)
    scatters = _extract_scatters(ax, legend_labels)
    
    return {
        'type': 'plot',
        'axes': {
            'title': ax.get_title(),
            'xtitle': ax.get_xlabel(),
            'ytitle': ax.get_ylabel(),
            'xfixed': not ax.get_autoscalex_on(),
            'yfixed': not ax.get_autoscaley_on(),
            'xmin': float(ax.get_xlim()[0]),
            'xmax': float(ax.get_xlim()[1]),
            'ymin': float(ax.get_ylim()[0]),
            'ymax': float(ax.get_ylim()[1]),
            'xlog': ax.get_xscale() == 'log',
            'ylog': ax.get_yscale() == 'log',
        },
        'plots': [ { '_data': data } for data in plots + hists + scatters ]
    }


    
def figure_to_layout(fig):
    """converts a Matplotlib Figure to a SlowDash Layout
    Parameters:
      - fig: instance of a Matplotlib Figure
    Return Value:
      - A Python dict representing SlowDash Layout
    TODO:
      - extract the grid
    """
    
    return { 'panels': [ axes_to_plot(ax) for ax in fig.axes ] }



def slowdashify(fig, name:str):
    """form a Matplotlib Figure object, create a SlowPlot configuration (layout) and dataPacket to fill the layout
    Return Value:
      tuple of slowplot_layout_config and data_packet
    """

    if not isinstance(fig, matplotlib.figure.Figure):
        return None, None

    if name is None or len(name) == 0:
        name = f'MPL-{str(uuid.uuid4()).split("-")[1]}'
    
    layout = figure_to_layout(fig)
    layout_config = {
        'control': {
            'range': { 'length': 900, 'to': 0 },
            'reload': 10,
        },
        'panels': []
    }
    data_packet = {}
    
    for panel in layout.get('panels', []):
        panel_conf ={
            'type': panel.get('type', 'plot'),
            'axes': panel.get('axes', {}),
            'plots': []
        }
        for plot in panel.get('plots', []):
            plotdata = plot.get('_data', {})
            plotname = plotdata.get('_attr', {}).get('name', None)
            if plotname is None:
                plotname = f'unnamed{len(data):02d}'
            channel = f'{name}.{plotname}'
            
            if 'bins' in plotdata:
                datatype = 'histogram'
            elif 'ybins' in plotdata:
                datatype = 'histogram2d'
            elif 'y' in plotdata:
                datatype = 'graph'
            else:
                logging.error(f'Unknown data type: {channel}')
                continue
                
            plot_conf = { 'type': datatype, 'channel': channel }
            plot_conf.update({k:v for k,v in plotdata.get('_attr', {}).items() if k!='name'})
            panel_conf['plots'].append(plot_conf)

            data_packet[channel] = plotdata
            
        layout_config['panels'].append(panel_conf)

    return layout_config, data_packet



if __name__ == '__main__':
    import matplotlib.pyplot as plt

    x = np.linspace(0, 10, 2)
    y1 = 5*np.sin(x) + 7
    y2 = 6*np.cos(x) + 7
    dy = np.random.poisson(5, len(x))

    fig, [ax, ax2] = plt.subplots(2, 1)

    ax.plot(x, y1, label='plot A')
    ax.plot(x, y2)
    ax2.hist(np.random.randn(100), bins=10, label='hist A')
    ax2.hist(np.random.randn(100) + 1.5, bins=10)
    ax.errorbar(x, y1, yerr=dy, fmt='o', label='errorbar A')
    ax.errorbar(x, y2, yerr=dy, fmt='s')
    ax.scatter(y1, y2, c='red', label='scatter A')
    ax.scatter(y2, x, c='blue')

    ax.set_xlabel("X")
    ax.legend()
    ax2.legend()

    config, data = slowdashify(fig, 'MPL')

    import json
    print(json.dumps(config, indent=2))
    print(json.dumps(data, indent=2))
    
    plt.show()
