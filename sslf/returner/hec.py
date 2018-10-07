
import os, socket, datetime, urllib3, json, time
from urllib3.exceptions import InsecureRequestWarning
import logging

from sslf.util import AttrDict

log = logging.getLogger('sslf:hec')

HOSTNAME = socket.gethostname()

# try to make sure each send is this big
# (but still timely)
_max_content_bytes = 100000 # bytes
_delay_send_wait_time = 500 # ms

class HECEvent(AttrDict):
    def send(self):
        # don't send these to hec.send_event or it'll send them in the payload
        hec = self.pop('hec')
        event = self.pop('event')
        try:
            hec.send_event( event, **self )
        except:
            # put these back for error reporting purposes
            self.hec = hec
            self.event = event
            raise

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

    def build_event(self, evr): # evr is an event reader output object
        return HECEvent(hec=self, event=evr.event,
            source=evr.source, time=evr.time, fields=evr.fields)

    def __init__(self, hec_url, token,
        verify_ssl=True, use_certifi=False, proxy_url=False,
        redirect_limit=10, retries=2, conn_timeout=3, read_timeout=2, backoff=3,
        **base_payload):

        self.token = token
        self.url   = hec_url

        if self.url.endswith('/'):
            self.url = self.url[:len(self.url)-1]

        poolmanager_opts = dict()
        if use_certifi:
            # <rant>
            # certifi is the rational thing to do in most commercial situations
            # where you have old RHEL with ancient CA certs.  It avoids having
            # to update system packages to get modern CA lists.
            #
            # However, if you have modern hosts with update CA certs that you
            # trust, or if you have any self signed or private CA certs it
            # doesn't help and quickly becomes an anti-pattern.
            #
            # Updating /etc/ca_certs with vim or salt (or whatever) should be
            # enough. certifi forces backfilps to use a custom CA.
            # </rant>
            poolmanager_opts['ca_certs'] = certifi.where()
        if verify_ssl:
            poolmanager_opts['cert_reqs'] = 'CERT_REQUIRED'
        else:
            urllib3.disable_warnings(InsecureRequestWarning)

        # NOTE: timeout does not have to respect or relate to retries
        # this just seemed like a convenient way to avoid another init-kw-arg
        poolmanager_opts['timeout'] = retries * conn_timeout
        poolmanager_opts['retries'] = urllib3.util.retry.Retry(total=retries,
            redirect=redirect_limit, connect=conn_timeout, read=read_timeout,
            respect_retry_after_header=True, backoff_factor=backoff)

        if proxy_url:
            self.pool_manager = urllib3.ProxyManager(proxy_url, **poolmanager_opts)
        else:
            self.pool_manager = urllib3.PoolManager(**poolmanager_opts)

        self.base_payload.update(base_payload)

    def __str__(self):
        return f'HEC({self.url}{self.path})'
    __repr__ = __str__

    def _post_message(self, json_data):
        headers = urllib3.make_headers( keep_alive=True,
            user_agent='sslf-hec/3.14', accept_encoding=True)
        headers.update({
            'Authorization': 'Splunk ' + self.token,
            'Content-Type': 'application/json',
        })
        encoded_data = json.dumps(json_data, cls=MyJSONEncoder).encode('utf-8')
        fake_headers = headers.copy()
        fake_headers['Authorization'] = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx' + headers['Authorization'][-4:]
        log.debug("HEC.pool_manager.request('POST', url=%s + path=%s, body=%s, headers=%s)",
            self.url, self.path, encoded_data, fake_headers)
        return self.pool_manager.request('POST', self.url + self.path, body=encoded_data, headers=headers)

    def _send_event(self, event, **payload_data):
        payload = self.base_payload.copy()
        payload.update(payload_data)

        payload['event'] = event

        if not payload.get('time') and isinstance(event, dict):
            payload['time'] = event.get('time')

        if not payload.get('time'):
            payload['time'] = datetime.datetime.now()

        res = self._post_message(payload)

        if res.status == 400:
            return res # splunk seems to use 400 codes for data format errors

        if res.status < 200 or res.status > 299:
            raise Exception(f'HTTP ERROR {res.status}: {res.data}')

        return res

    def send_event(self, event, **payload_data):
        res = self._send_event(event, **payload_data)

        try:
            dat = json.loads(res.data.decode('utf-8'))
        except Exception as e:
            raise Exception(f'Unable to decode reply from Splunk HEC: {e}')

        if res.status == 400:
            raise Exception('Splunk HEC Data Format 400 Error code={code}: {text}'.format(**dat))

        if dat['code'] != 0:
            raise Exception('Splunk HEC Error code={code}: {text}'.format(**dat))

        return dat

HEC = MySplunkHEC
