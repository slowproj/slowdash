
import datetime, copy, logging
import component


class Export_CSV(component.ComponentPlugin):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)

        
    def process_get(self, path, opts, output):
        if len(path) < 3 or path[1] != 'csv':
            return None

        timezone = opts.get('timezone', 'local')
        data_path = ['data'] + path[2:]
        data_opts = copy.deepcopy(opts)
        resample = data_opts.get('resample', None)
        if resample is None or resample < 0:
            data_opts['resample'] = 0

        timeseries = self.app.process_get(data_path, data_opts, output)
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
