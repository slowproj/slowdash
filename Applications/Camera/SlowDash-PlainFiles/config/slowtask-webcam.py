
import json, time

import slowpy.control, slowpy.store
ctrl = slowpy.control.ControlSystem()

http = None
datastore_ts, datastore_objts = None, None
blob_storage = None
photo_interval = 3600


async def _initialize(params):
    global http, datastore_ts, datastore_objts, blob_storage
    global photo_interval
    
    camera_url = params.get('camera_url', None)
    db_url = params.get('db_url', None)
    photo_interval = float(params.get('photo_interval', 3600))
    storage_path = params.get('photo_storage_path', 'photo')
    
    if camera_url is None:
        print("ERROR: camera_url not given")
    if db_url is None:
        print("ERROR: db_url not given")

    if camera_url:
        try:
            http = ctrl.http(camera_url)
            print(f"Camera connected at {camera_url}")
        except Exception as e:
            print(e)
            http = None

    if db_url:
        try:
            datastore_ts = slowpy.store.create_datastore_from_url(db_url, 'data')
            datastore_objts = slowpy.store.create_datastore_from_url(db_url, 'photo')
            print(f"DB connected at {db_url}")
        except Exception as e:
            print(e)
            datastore_ts, datastore_objts = None, None
        
    blob_storage = slowpy.store.BlobStorage_File(names=[storage_path, '%Y-%m', '%y%m%d-%H%M%S-%Z'], ext='.jpg')


last_photo_time = 0
async def _loop():
    global last_photo_time
    now = time.monotonic()
    if now - last_photo_time >= photo_interval:
        read_photo()
        last_photo_time = now
        
    await ctrl.aio_sleep(1)

        
def read_photo():
    if http is None or datastore_objts is None:
        return
    try:
        photo = http.get()
    except Exception as e:
        print(e)
        return

    properties = extract_properties(photo)
    datastore_objts.append(json.dumps({'tree': properties}), tag='Properties')
    datastore_ts.append(properties['Stats']['Brightness'], tag='Brightness')

    modified_photo = edit_image(photo)
    blob_id = blob_storage.write(modified_photo)
    datastore_objts.append(blob_id, tag='Photo')
    print(blob_id)


############################################################

from PIL import Image, ImageDraw, ImageStat, ImageFont   # pip install pillow
import PIL.ExifTags as ExifTags
import io, datetime

def extract_properties(photo):
    properties = {
        "Basic": {},
        "Exif": {},
        "Stats": {},
        "Meta": {}
    }
    
    inp = io.BytesIO(photo)
    with Image.open(inp) as img:
        properties["Basic"]["Date"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

    
def edit_image(photo):
    inp = io.BytesIO(photo)
    with Image.open(inp) as img:
        try:
            exif = img.info.get("exif")
        except:
            exif = None

        imprint_datetime(img)

        outp = io.BytesIO()
        if exif is not None:
            img.save(outp, format=img.format, exif=exif)
        else:
            img.save(outp, format=img.format)

        return outp.getvalue()

    
def imprint_datetime(img: Image):
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")

        # drop-shadow in white
        x, y = 10, 10
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            draw.text((x + dx, y + dy), timestamp, font=font, fill="white")
        
        # text in black
        draw.text((x, y), timestamp, font=font, fill="black")

    

    
############################################################

        
if __name__ == '__main__':    
    async def main():
        await _initialize({
            'camera_url': 'http://192.168.1.43/~pi/photo.cgi',
            'db_url': 'sqlite:///SlowPhoto',
            'photo_interval': 10
        })
        ctrl.stop_by_signal()
        while not ctrl.is_stop_requested():
            await _loop()

    import asyncio
    asyncio.run(main())
