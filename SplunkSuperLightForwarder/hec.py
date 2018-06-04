
import os, socket, datetime, urllib3, json, time

HOSTNAME = socket.gethostname()

class MyJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime,datetime.date)):
            dt = o.timetuple()
            dtt = time.mktime(dt)
            return int(dtt)
        if o.__class__.__name__ in ('Decimal'):
            return float(o)
        return json.JSONEncoder.default(self,o)

class MySplunkHEC(object):
    base_payload = {
        'index':      'main',
        'sourcetype': 'json',
        'source':     'my-splunk-hec',
        'host':       HOSTNAME,
    }

    path = "/services/collector/event"
    url_format = "{0.proto}://{0.server}:{0.port}{0.path}"

    def __init__(self, hec_url, token, verify_ssl=True, **base_payload):
        self.token  = token
        self.url    = hec_url
        self.verify = verify_ssl
        self.proto  = 'http'

        self.pool_manager = urllib3.PoolManager(timeout=2.5)

        if self.verify == False:
            urllib3.disable_warnings()

        self.base_payload.update(base_payload)

    def _post_message(self, json_data):
        headers = {
            'Authorization': 'Splunk ' + self.token,
            'Content-Type': 'application/json',
        }
        encoded_data = json.dumps(json_data, cls=MyJSONEncoder).encode('utf-8')
        return self.pool_manager.request('POST', self.url, body=encoded_data, headers=headers)

    def send_event(self, event, **payload_data):
        payload = self.base_payload.copy()
        payload.update(payload_data)

        payload['event'] = event

        if not payload.get('time'):
            payload['time'] = event.get('time', datetime.datetime.now())

        res = self._post_message(payload)

        if res.status == 400:
            return res # splunk seems to use 400 codes for data format errors

        if res.status < 200 or res.status > 299:
            raise Exception("HTTP ERROR {status}: {error_maybe}".format(status=res.status, error_maybe=res.data))

        return res

    def check_event(self, event, **payload_data):
        res = self.send_event(event, **payload_data)

        try:
            dat = json.loads(res.data.decode('utf-8'))
        except Exception as e:
            raise Exception("Unable to decode reply from Splunk HEC: {0}".format(e))

        if res.status == 400:
            raise Exception("Splunk HEC Data Format 400 Error code={code}: {text}".format(**dat))

        if dat['code'] != 0:
            raise Exception("Splunk HEC Error code={code}: {text}".format(**dat))

        return dat

HEC = MySplunkHEC
