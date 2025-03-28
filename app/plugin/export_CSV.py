# Created by Sanshiro Enomoto on 28 December 2024 #


import datetime, copy, logging

import slowlette
from sd_component import ComponentPlugin


class Export_CSV(ComponentPlugin):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)


    @slowlette.get('/api/export/csv/{channels}')
    async def export_csv(self, channels:str, opts:dict, timezone:str='local', resample:float=0):
        if len(timezone) == 0:
            timezone = 'local'
            
        data_opts = copy.deepcopy(opts)
        if resample < 0:  # replace "no resampling" with "auto resampling"; this does not affect single channel request
            resample = 0
        data_opts['resample'] = resample
        if 'timezone' in data_opts:
            del data_opts['timezone']

        timeseries = await self.app.request_data(channels, **data_opts)
        if timeseries is None:
            return None

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

        content = '\n'.join([
            ','.join(['NaN' if col is None else col for col in row]) for row in table
        ]).encode()
                
        return slowlette.Response(content_type='text/csv', content=content)
