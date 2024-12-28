
import time, datetime, json, uuid, re, logging
import export


class Export_CSV(export.Export):
    def __init__(self, app, project, **params):
        super().__init__(app, project, **params)

        
    def process_get(self, path, opts, output):
        if len(path) < 3 or path[1] != 'csv':
            return None
        
        try:
            channels = path[2].split(',')
            length = float(opts.get('length', '3600'))
            to = float(opts.get('to', int(time.time())+1))
            resample = float(opts.get('resample', -1))
            reducer = opts.get('reducer', 'last')
            timezone = opts.get('timezone', 'local')
        except Exception as e:
            logging.error(e)
            return False
        
        if resample is None or resample < 0:
            interval = 0
        else:
            interval = float(resample)

        timeseries = self.app._get_data(channels, length, to, interval, reducer)
        if timeseries is None:
            return False

        table = [ ['DateTime', 'TimeStamp'] ]
        table[0].extend(timeseries.keys())
        for name, data in timeseries.items():
            start = data.get('start', 0)
            tk = data.get('t', [])
            xk = data.get('x', [])
            for k in range(len(tk)):
                if len(table) <= k+1:
                    t = int(10*(start+tk[k]))/10.0
                    date_local = datetime.datetime.fromtimestamp(t)
                    date_utc = datetime.datetime.utcfromtimestamp(t)
                    if timezone.upper() == 'LOCAL':
                        date = date_local
                        timediff = abs((date_local - date_utc).total_seconds())
                        tz = '+' if date_local > date_utc else '-'
                        tz = tz + '%02d:%02d' % (int(timediff/3600), int(timediff%3600))
                    else:
                        date = date_utc
                        tz = '+00:00'
                        
                    table.append([ date.strftime('%Y-%m-%dT%H:%M:%S') + tz, '%d' % t ])
                table[k+1].append(str(xk[k]) if xk[k] is not None else 'null')

        output.write('\n'.join([
            ','.join(['NaN' if col is None else col for col in row]) for row in table
        ]).encode())
                
        return 'text/csv'
