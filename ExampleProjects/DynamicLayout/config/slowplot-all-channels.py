import logging

async def _setup(app):
    channels = await app.request_channels()
    logging.debug(f'Channels: {channels}\n')

    layout = {
        "panels": [{
            "type": "timeaxis",
            "plots": [{ "type": "timeseries", "channel": ch['name'] }]
        } for ch in channels if ch.get('type', 'numeric') == 'numeric' ]
    }

    return layout

