#! /bin/env python3

import sys, time, logging, requests
from datetime import datetime
from urllib.parse import urlparse
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)



############################################################

class DataStore:
    def __init__(self, couchdb_url, series_name, design_name="SlowView"):
        self.couch = None
        self.db = None
        if (couchdb_url is None) or (series_name is None):
            return
        try:
            import couchdb
        except Exception as e:
            logger.error('Unable to import couchdb Python module')
            return
        
        url = urlparse(couchdb_url)
        self.url = 'http://%s' % url.netloc
        self.db_name = url.path[1:]
        self.series = series_name
        
        views = {
            "_id": '_design/%s' % design_name,
            "views": {
                self.series: {
                    "map": '''function (doc) {
                        if (doc.series != "%s") return;
                        emit(doc.timestamp, {
                            "%s": {
                                id: doc._id+'/' +doc.filename, 
                                mime: doc._attachments[doc.filename].content_type, 
                                meta: doc.properties
                            },
                            "%sProperties": {
                                tree: doc.properties
                            }
                        });
                    }''' % (self.series, self.series, self.series)
                },
                ("%sProperties" % self.series): {
                    "map": '''function (doc) {
                        if (doc.series != "%s") return;
                        var record = {};
                        for (var group in doc.properties) {
                            for (var key in doc.properties[group]) {
                                record[key] = doc.properties[group][key];
                            }
                        }
                        emit(doc.timestamp, record);
                    }''' % self.series
                }
            }
        }

        db_created = False
        for i in range(12):
            if self.couch is None:
                self.couch = couchdb.Server(self.url)
            try:
                self.db = self.couch[self.db_name]
            except Exception as e:
                try:
                    self.db = self.couch.create(self.db_name)
                except Exception as e:
                    logger.info('Unable to find database "%s", retrying in 5 sec: %s' % (self.db_name, str(e)))
                    time.sleep(5)
                    continue
                db_created = True
                logger.info('Database "%s" created.' % self.db_name)
            break
        else:
            logger.info('Unable to find database "%s"' % self.db_name)
            self.couch = None
            self.db = None
            
        if db_created:
            # these must exist, but may not be created yet
            for sys_db_name in ['_users', '_replicator', '_global_changes']:
                try:
                    sys_db = self.couch[sys_db_names]
                except Exception as e:
                    self.couch.create(sys_db_name)
                            
        if self.db is not None:
            logger.info('DB connected: %s' % self.db_name)
            design = self.db.get("_design/%s" % design_name)
            if (design is None) or (self.series not in design.get('views', {})):
                try:
                    self.db.save(views)
                    logger.info('Design document created: %s' % design_name)
                except Exception as e:
                    logger.error('Unable to create design "%s": %s' % (design_name, str(e)))


    def save(self, content, mime, properties):
        if self.db is None:
            return
        
        now = datetime.now()
        doc_id = '%.3f' % now.timestamp()
        filename = now.strftime(self.series + '-%y%m%d-%H%M%S.' + mime2ext(mime))
        properties['Meta'] = {
            'Document': doc_id,
            'FileName': filename
        }
        doc = {
            "_id": doc_id,
            "timestamp": now.timestamp(),
            "series": self.series,
            "filename": filename,
            "properties": properties
        }
        try:
            self.db.save(doc)
            self.db.put_attachment(doc, content, filename=filename, content_type=mime)
            logger.info('uploaded to CouchDB: %s' % filename)
        except Exception as e:
            logger.error('Unable to save file "%s": %s' % (filename, str(e)))
            

            
############################################################

from PIL import Image, ImageStat
import PIL.ExifTags as ExifTags
import io
def extract_properties(data, mime):
    if not mime.startswith('image/'):
        return {}
    
    properties = {
        "Basic": {},
        "Exif": {},
        "Stats": {},
        "Meta": {}
    }
    
    inp = io.BytesIO(data)
    with Image.open(inp) as img:
        properties["Basic"]["Date"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        properties["Basic"]['Format'] = img.format
        properties["Basic"]['Size'] = '(%d,%d)' % (img.size[0], img.size[1])

        for tag in [ 34665, 34853, 37500 ]:
            try:
                exif = img.getexif().get_ifd(tag)
            except:
                exif = None
            if exif:
                for k, v in exif.items():
                    if k in ExifTags.TAGS:
                        properties["Exif"][ExifTags.TAGS[k]] = str(v)

        stat = ImageStat.Stat(img.convert('L'))
        properties["Stats"]['Brightness'] = '%.3f' % (stat.mean[0]/2.56) # 0..100
        
    return properties


def mime2ext(mime):
    if mime == 'image/jpeg':
        return 'jpg'
    elif mime == 'image/png':
        return 'png'
    elif mime.startswith('text/'):
        return 'txt'
    else:
        return 'dat'
        

############################################################

series_name = None
source_url = None
light_url = None
couchdb_url = None
interval = 0

is_running = True
is_fetching = False
is_stop_requested = False
last_fetch_time = 0


def _get_channels():
    return [
        {'name': 'Run', 'type': 'tree'},
    ]


def _get_data(channel):
    if channel == 'Run':
        return { 'tree': {
            'Config': {
                'Series': series_name,
                'SourceUrl': source_url,
                'CouchdbUrl': couchdb_url,
                'Interval': interval
            },
            'Status': {
                'Running': is_running
            }
        }}

    return None


def _initialize(params):
    global series_name, interval, source_url, couchdb_url, light_url
    global datastore
    global is_running, is_fetching, last_fetch_time
    try:
        series_name = params.get('series_name', 'photos')
        source_url = params.get('source_url', None)
        light_url = params.get('light_url', None)
        couchdb_url = params.get('couchdb_url', None)
        interval = float(params.get('interval', 600))
    except Exception as e:
        logger.error('Bad initialization parameter' % str(e))
        interval = 0

    is_running = True
    is_fetching = False
    datastore = DataStore(couchdb_url, series_name)

    last_fetch_time = 0
    
    
def _finalize():
    global light_url
    try:
        requests.get(light_url)
    except Exception as e:
        print(e)
    
def start():
    global is_running, light_url
    is_running = True
    last_fetch_time = 0
    try:
        requests.get('%s?seq=Byg' % light_url)
    except Exception as e:
        print(e)
    
def stop():
    global is_running, light_url
    is_running = False
    try:
        requests.get(light_url)
    except Exception as e:
        print(e)

    
def fetch():
    global source_url, light_url, datastore
    global is_running, is_fetching

    if is_fetching or (source_url is None):
        return
    is_fetching = True
    #... TODO: use a lock

    if light_url is not None:
        try:
            if is_running:
                requests.get('%s?seq=r:1,yg' % light_url)
            else:
                requests.get('%s?seq=Br:1,n' % light_url)
        except Exception as e:
            print(e)
                
    logger.info('requesting URL resource: %s' % source_url)
    try:
        response = requests.get(source_url)
        if response.status_code != 200:
            response = None
            logger.error('unable to fetch URL resource "%s": status %d' % (source_url, response.status_code))
        else:
            logger.info('URL resource fetched: %d: %s' % (response.status_code, source_url))
    except Exception as e:
        response = None
        logger.error('unable to fetch URL resource "%s": %s' % (source_url, str(e)))

    if response is not None:
        mime = response.headers.get('Content-Type', None)
        datastore.save(response.content, mime, extract_properties(response.content, mime))

    is_fetching = False

    
def _loop():
    global is_running, interval, last_fetch_time
    if is_running and (interval > 0):
        now = time.time()
        if now > last_fetch_time + interval:
            fetch()
            last_fetch_time = now
    time.sleep(1)


def _process_command(doc):
    try:
        if doc.get('start', False):
            start()
        elif doc.get('stop', False):
            stop()
        elif doc.get('single', False):
            fetch()
        elif doc.get('update', False):
            try:
                global source_url, interval
                source_url = doc.get('source_url', source_url)
                interval = float(doc.get('interval', interval))
            except Exception as e:
                return { "status": "error", "message": str(e) }
        else:
            return False
    except Exception as e:
        return { "status": "error", "message": str(e) }

    return True




if __name__ == '__main__':
    pi_url = 'http://10.95.99.68/~picam',
    _initialize({
        'series_name': 'RPiCamera',
        'source_url': '%s/photo.cgi' % pi_url,
        'light_url': '%s/light.cgi' % pi_url,
        'couchdb_url': 'http://admin:neutrino@localhost:5984/photos',
        'interval': 0
    })
    start()
    fetch()
