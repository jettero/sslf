
import os, socket, datetime, urllib3, json, time
from urllib3.exceptions import InsecureRequestWarning
import logging
from collections import deque

from sslf.util import AttrDict

log = logging.getLogger('sslf:hec')

HOSTNAME = socket.gethostname()

# try to make sure each send is this big
# (but still timely)
_max_content_bytes = 100000 # bytes
_delay_send_wait_time = 500 # ms

class MyJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime,datetime.date)):
            dt = o.timetuple()
            dtt = time.mktime(dt)
            return int(dtt)
        if o.__class__.__name__ in ('Decimal'):
            return float(o)
        return json.JSONEncoder.default(self,o)


class Payload:
    max_bytes = _max_content_bytes
    sep = b' '
    charset = 'utf-8'

    def __init__(self, *items):
        # we compose to ensure correct encoding on append()
        # without worring about extend() (et al?)
        self.q = deque()
        for item in items:
            self.q.append(item)

    def append(self, item):
        if isinstance(item, Payload):
            for x in item:
                self.append(x)
        else:
            if not isinstance(item, str):
                item = json.dumps(item, cls=MyJSONEncoder)
            self.q.append(item)

    def pop(self):
        ret = bytes()
        while bool(self) and len(self.q) > 0:
            item = self.q[0].encode(self.charset)
            l = len(ret)
            if l > 0:
                l += 1 # count sep byte
            l += len(item)
            if l > self.max_bytes:
                break
            self.q.popleft()
            if ret:
                ret += self.sep
            ret += item
        return ret

    def __iter__(self):
        while self:
            yield self.pop()

    def __bool__(self):
        return len(self.q) > 0

    def __len__(self):
        s = len(self.q)-1 # start with the separators
        for item in self.q:
            s += len(item) # and the length of the items
        return s

    def __repr__(self):
        l = len(self.q)
        if l == 0:
            return 'Payload<empty>'
        if l == 1:
            return 'Payload<1 item>'
        return f'Payload<{l} items>'


class MySplunkHEC:
    base_payload = {
        'index':      'main',
        'sourcetype': 'json',
        'source':     'my-splunk-hec',
        'host':       HOSTNAME,
    }

    path = "/services/collector/event"

    def __init__(self, hec_url, token, verify_ssl=True, use_certifi=False, proxy_url=False,
        redirect_limit=10, retries=2, conn_timeout=3, read_timeout=2, backoff=3, **base_payload):

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
            # enough. certifi forces backfilps to use a custom CA and causes
            # confusion regards to why updating the system CA certs doesn't
            # alter the behavior of programs using certifi.
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

    def _post_message(self, dat):
        headers = urllib3.make_headers( keep_alive=True, user_agent='sslf-hec/3.14', accept_encoding=True)
        headers.update({ 'Authorization': 'Splunk ' + self.token, 'Content-Type': 'application/json' })
        fake_headers = headers.copy()
        fake_headers['Authorization'] = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx' + headers['Authorization'][-4:]
        log.debug("HEC.pool_manager.request('POST', url=%s + path=%s, body=%s, headers=%s)",
            self.url, self.path, dat, fake_headers)
        return self.pool_manager.request('POST', self.url + self.path, body=dat, headers=headers)

    def encode_events(self, *events, **payload_data):
        payload = Payload()

        for event in events:
            dat = self.base_payload.copy()
            dat.update(payload_data)
            dat['event'] = event
            if not dat.get('time') and isinstance(event, dict):
                dat['time'] = event.get('time')
            if not dat.get('time'):
                dat['time'] = datetime.datetime.now()
            payload.append(dat)

        return payload

    def _decode_res(self, res):
        try:
            dat = json.loads(res.data.decode('utf-8'))

            if dat['code'] != 0:
                log.error(f'Splunk HEC Error code={code}: {text}'.format(**dat))

        except json.JSONDecodeError as e:
            log.error('Unable to decode reply from Splunk HEC: %s', e)

    def _send_event(self, encoded_payload):
        res = self._post_message(encoded_payload)

        if res.status == 400:
            self._decode(res)
            return

        if res.status < 200 or res.status > 299:
            log.error(f'HTTP ERROR {res.status}: {res.data}')

        self._decode_res(res)

    def send_event(self, *events, **payload_data):
        def _preprocess_event(event):
            if isinstance(event, dict) and 'event' in event:
                payload_data.update(**event)
                event = payload_data.pop('event')
            return event
        events = [ _preprocess_event(e) for e in events ]
        payload = self.encode_events(*events, **payload_data)

        while payload:
            self._send_event(payload.pop())

HEC = MySplunkHEC
