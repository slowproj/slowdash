# Created by Sanshiro Enomoto on 20 March 2022 #

import re, json, enum, datetime, logging


class Schema:
    tag_field_separator = ':'
    
    def __init__(self, schema=None, tag_values=[]):
        self.init_description = schema
        self.init_tag_values = tag_values
        self.initialize()

        
    def __str__(self):
        return (''
            + f'{self.table}'
            + (f'<{self.suffix}>' if self.suffix is not None and len(self.suffix) > 0 else '')
            + (f'[{",".join([self.tag]+self.flags)}]' if self.tag is not None else '')
            + f'@{self.time or ""}({self.time_type or ""})'
            + (f'={",".join(self.fields)}' if self.fields is not None and len(self.fields) > 0 else '')
        )

    
    def initialize(self):
        self.table = None
        self.tag = None
        self.flags = []
        self.time = None
        self.time_type = None
        self.fields = []
        self.field_types = []
        
        self.default_field = None
        self.tag_values = self.init_tag_values
        
        # do not clear suffix or any other additional fields here

        self.channel_table = {}
        self.parse(self.init_description)

            
    def add_channel(self, channel_name : str, field_type=None):
        channel_name_str = str(channel_name)
        if channel_name_str not in self.channel_table:
            self.channel_table[channel_name_str] = { 'name': channel_name_str }
        else:
            self.channel_table[channel_name_str]['name'] = channel_name_str
        if field_type is not None:
            self.channel_table[channel_name_str]['type'] = field_type

                    
    def parse(self, schema):
        # syntax:  TABLE [TAG, FLAG, FLAG...] @TIME(TIME_TYPE) = FIELD(OPT), FIELD(OPT), ...
        # all elements are optional
        # quote with " or ' to use special characters
        
        class State(enum.Enum):
            TABLE=1
            TAGFLAG=2
            AFTER_TAGFLAG=3
            TIME=4
            TIME_TYPE=5
            AFTER_TIME=6
            FIELD=7
            FIELD_OPTS=8
            AFTER_FIELD_OPTS=9
        state = State.TABLE
        token = ''
        quote = None
        
        if schema is None:
            return

        for ch in str(schema):
            if ch == "'" or ch == '"':
                if quote is None:
                    quote = ch
                    continue
                elif ch == quote:
                    quote = None
                    continue
            if quote is not None:
                token += ch
                continue
            if ch == ' ':
                continue
            
            if state == State.TABLE:
                if ch == '[':
                    state = State.TAGFLAG
                elif ch == '@':
                    state = State.TIME
                elif ch == '=':
                    state = State.FIELD
                if state == State.TABLE:
                    token += ch
                else:
                    if len(token) > 0:
                        self.table = token
                        token = ""
                    
            elif state == State.TAGFLAG:
                if ch == ',':
                    if len(token) > 0:
                        if self.tag is None:
                            self.tag = token
                        else:
                            self.flags.append(token)
                        token = ''
                elif ch == ']':
                    if len(token) > 0:
                        if self.tag is None:
                            self.tag = token
                        else:
                            self.flags.append(token)
                        token = ''
                    state = State.AFTER_TAGFLAG
                else:
                    token += ch
                    
            elif state == State.AFTER_TAGFLAG:
                if ch == '@':
                    state = State.TIME
                elif ch == '=':
                    state = State.FIELD
                else:
                    token += ch

                if state != State.AFTER_TAGFLAG and len(token) > 0:
                    logging.error('invalid schema: extra token after tags: "%s"' % token)
                    token = ''

            elif state == State.TIME:
                if ch == '=':
                    if len(token) > 0:
                        self.time = token
                        token = ''
                    state = State.FIELD
                elif ch == '(':
                    if len(token) > 0:
                        self.time = token
                        token = ''
                    state = State.TIME_TYPE
                else:
                    token += ch
                    
            elif state == State.TIME_TYPE:
                if ch == ')':
                    if len(token) > 0:
                        self.time_type = token
                        token = ''
                    state = State.AFTER_TIME
                else:
                    token += ch

            elif state == State.AFTER_TIME:
                if ch == '=':
                    state = State.FIELD
                    if len(token) > 0:
                        logging.error('invalid schema: extra token after time: "%s"' % token)
                        token = ''
                else:
                    token += ch

            elif state == State.FIELD:
                if ch == '(':
                    if len(token) > 0:                    
                        self.fields.append(token)
                        token = ''
                    state = State.FIELD_OPTS
                elif ch == ',':
                    if len(token) > 0:
                        self.fields.append(token)
                        self.field_types.append(None)
                        token = ''
                else:
                    token += ch
                    
            elif state == State.FIELD_OPTS:
                if ch == ')':
                    field_type = None
                    if len(token) > 0:
                        for elem in token.split(','):
                            if elem[0:5].lower() == 'type=' and len(elem) > 5:
                                field_type = elem[5:]
                            elif elem.lower() == 'default':
                                self.default_field = self.fields[-1]
                        token = ''
                    self.field_types.append(field_type)
                    state = State.AFTER_FIELD_OPTS
                else:
                    token += ch
                
            elif state == State.AFTER_FIELD_OPTS:
                if ch == ',':
                    state = State.FIELD
                    if len(token) > 0:
                        logging.error('invalid schema: extra field type: "%s"' % token)
                        token = ''
                else:
                    token += ch

        if len(token) > 0:
            if state == State.TABLE:
                self.table = token
            elif state == State.TIME:
                self.time = token
            elif state == State.FIELD:
                self.fields.append(token)
                self.field_types.append(None)
            else:
                logging.error('invalid schema: extra token: "%s"' % token)

        if len(self.fields) == 1:
            self.default_field = self.fields[0]

                
    def get_query_times(self, start, stop, time_sep='T'):
        if self.time is None:
            time_from = '%d' % start
            time_to = '%d' % stop
        elif self.time_type == 'unix':
            time_from = '%d' % start
            time_to = '%d' % stop
        else:
            datetime_start = datetime.datetime.fromtimestamp(start)
            datetime_stop = datetime.datetime.fromtimestamp(stop)
            if self.time_type == 'naive':
                pass
            else:
                datetime_start = datetime_start.astimezone(datetime.timezone.utc)
                datetime_stop = datetime_stop.astimezone(datetime.timezone.utc)
                if self.time_type == 'aware':
                    pass
                elif self.time_type == 'unspecifiedutc':
                    datetime_start = datetime_start.replace(tzinfo=None)
                    datetime_stop = datetime_stop.replace(tzinfo=None)
                else:
                    return None, None, None
            time_from = "'%s'" % datetime_start.isoformat(sep=time_sep)
            time_to = "'%s'" % datetime_stop.isoformat(sep=time_sep)

        if self.time is not None:
            time_col = self.time
        else:
            time_col = None
                
        return time_col, time_from, time_to

        
    def get_query_tagvalues_fields(self, target_channels):
        tag_values, fields = [],  []
        name_mapping = {}
        if self.tag is None:
            # no tag: channel by field only
            for ch in target_channels:
                if ch in self.fields:
                    fields.append(ch)
        else:
            # tag and fields
            for name in target_channels:
                tagfield = name.split(self.tag_field_separator, 1)
                if len(tagfield) == 1:
                    # tag only
                    if self.default_field is None:
                        # no field to read defined
                        continue
                    tag_value, field = tagfield[0], self.default_field
                    channel = '%s%s%s' % (tag_value, self.tag_field_separator, field)
                    name_mapping[channel] = name
                else:
                    # tag and fields
                    tag_value, field = tagfield[0], tagfield[1]
                if tag_value not in tag_values:
                    tag_values.append(tag_value)
                if field not in fields:
                    if field in self.fields:
                        fields.append(field)
                            
        return tag_values, fields, name_mapping

        
    @staticmethod
    def identify_datatype(value):
        if value is None:
            return None
        
        if isinstance(value, float) or isinstance(value, int):
            return 'numeric'
        
        if isinstance(value, str):
            json_value = value.strip()
            if not (len(json_value) > 2 and json_value[0] == '{' and json_value[-1] == '}'):
                return 'string'
            try:
                json_value = json.loads(json_value)
            except Exception as e:
                return 'string'
        else:
            json_value = value
            
        if 'counts' in json_value:
            if 'xbins' in json_value:
                return 'histogram2d'
            else:
                return 'histogram'
        elif 'y' in json_value:
            return 'graph'
        elif 'table' in json_value:
            return 'table'
        elif 'tree' in json_value:
            return 'tree'
        elif 'mime' in json_value:
            return 'blob'
        else:
            return 'json'


    @staticmethod
    def parse_dburl(url):
        config = {
            'type': None,
            'user': None,
            'password': None,
            'host': None,
            'port': None,
            'db': None
        }
        if url is None or len(url) == 0:
            return config
        
        match = re.findall(r'^[a-zA-Z0-9]+://', url)
        if len(match) > 0:
            config['type'] = match[0][0:-3]
            url = url[len(match[0]):]
        pos = url.find('@')
        if pos >= 0:
            auth = url[0:pos]
            url = url[pos+1:]
            pos = auth.find(':')
            if pos > 0:
                config['user'] = auth[0:pos]
                config['password'] = auth[pos+1:]
            else:
                config['user'] = auth
        pos = url.find('/')
        if pos >= 0:
            config['db'] = url[pos+1:]
            url = url[0:pos]
        pos = url.find(':')
        if pos >= 0:
            config['host'] = url[0:pos]
            config['port'] = url[pos+1:]
        else:
            config['host'] = url
            
        return config
