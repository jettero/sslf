
import os, socket, datetime, urllib3, json, time
from urllib3.exceptions import InsecureRequestWarning
import logging

from sslf.util import DiskBackedQueue, MemQueue, SSLFQueueCapacityError

log = logging.getLogger('sslf:hec')

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


_queue_cache = dict()
def get_queue(disk_queue, *a):
    k = (disk_queue,) + a
    if k in _queue_cache:
        return _queue_cache[k]
    q = _queue_cache[k] = MemQueue() if disk_queue is None else DiskBackedQueue(disk_queue)
    return q

class MySplunkHEC:
    base_payload = {
        'index':      'main',
        'sourcetype': 'json',
        'source':     'unknown',
        'host':       HOSTNAME,
    }
    charset = 'utf-8'
    path = "/services/collector/event"

    def __init__(self, hec_url, token, verify_ssl=True, use_certifi=False, proxy_url=False,
        redirect_limit=10, retries=2, conn_timeout=3, read_timeout=2, backoff=3,
        disk_queue=None, **base_payload):

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
        self.q = get_queue(disk_queue, self.url, self.token)

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

    def encode_event(self, event, **payload_data):
        jdargs = payload_data.pop('_jdargs', {})
        dat = self.base_payload.copy()
        dat.update(payload_data)
        dat['event'] = event
        if not dat.get('time') and isinstance(event, dict):
            dat['time'] = event.get('time')
        if not dat.get('time'):
            dat['time'] = datetime.datetime.now()
        return json.dumps(dat, cls=MyJSONEncoder, **jdargs).encode(self.charset)
    encode_payload = encode_event

    def _decode_res(self, res):
        try:
            dat = json.loads(res.data.decode(self.charset))

            if dat['code'] != 0:
                log.error(f'Splunk HEC Error code={code}: {text}'.format(**dat))

            return dat

        except json.JSONDecodeError as e:
            log.error('Unable to decode reply from Splunk HEC: %s', e)

    def _send_event(self, encoded_payload):
        res = self._post_message(encoded_payload)

        # 400 can be ok, further checking required Splunk will sometimes give a
        # data-format error or similar in the json
        if res.status == 400:
            return self._decode_res(res)

        if res.status < 200 or res.status > 299:
            log.error(f'HTTP ERROR {res.status}: {res.data}')

        return self._decode_res(res)

    def send_event(self, event, **payload_data):
        encoded_payload = self.encode_event(event, **payload_data)
        return self._send_event(encoded_payload)

    def queue_event(self, event, **payload_data):
        encoded_payload = self.encode_event(event, **payload_data)
        try:
            self.q.put(encoded_payload)
        except SSLFQueueCapacityError:
            log.error("queue overflow during queue_event()")

    def flush(self):
        if self.q.cn > 0:
            s = 0
            c = 1
            while True:
                payloadz = self.q.getz()
                if not payloadz:
                    break
                self._send_event(payloadz)
                s += len(payloadz)
                c += 1
            log.info('sent %d byte(s) to HEC(%s) in %d batch(s)', s, self.url, c)

HEC = MySplunkHEC
