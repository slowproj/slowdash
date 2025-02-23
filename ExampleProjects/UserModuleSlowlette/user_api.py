import slowlette

app = slowlette.Slowlette()


@app.get('/channels')
def get_channels():
    return [ { 'name': 'data_query', 'type': 'tree' } ]


@app.get('/data/{channels}')
def get_data(channels:str, length:float=None, to:float=None, resample:float=None, reducer:str=None):
    if 'data_query' not in channels.split(','):
        return None
    
    record = { "data_query": { "x": {
        'tree': {
            'channels': channels,
            'length': length,
            'to': to,
            'resample': resample,
            'reducer': reducer,
        }
    }}}

    return record



if __name__ == '__main__':
    print(get_channels())
    print(get_data('data_query'))
