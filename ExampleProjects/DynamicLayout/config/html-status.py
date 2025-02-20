import statistics

async def _setup(app):
    channels = await app.request_channels()
    data = await app.request_data([ch['name'] for ch in channels], length=3600)
    
    html = '<table>'
    html += '<tr><th>Channel</th><th>N</th><th>Mean</th><th>Median</th><th>Stdev</th></tr>'
    for ch in channels:
        if ch.get('type', 'numeric') != 'numeric':
            continue
        name = ch['name']
        ts = data[name]['x']
        n = len(ts)
        mean = statistics.mean(ts) if n > 0 else 'NaN'
        median = statistics.median(ts) if n > 0 else 'NaN'
        stdev = statistics.stdev(ts) if n > 1 else 'NaN'
        html += f'<tr><th>{name}</th><td>{n}</td><td>{mean:.2f}</td><td>{median:.2f}</td><td>{stdev:.2f}</td></tr>'
    html += '</table>'

    return html
