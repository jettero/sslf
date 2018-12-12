# coding: utf-8

import os, socket, datetime, urllib3, time
import simplejson as json
from urllib3.exceptions import InsecureRequestWarning
import logging
import hashlib
import weakref

from sslf.util import (
    DiskBackedQueue, MemQueue, SSLFQueueCapacityError,
    DEFAULT_MEMORY_SIZE, DEFAULT_DISK_SIZE, AttrDict
)

log = logging.getLogger('sslf:returner:hec')

HOSTNAME = socket.gethostname()

class FilteredEvent(Exception):
    pass

def _mk_timestamp(o):
    if isinstance(o, (datetime.datetime,datetime.date)):
        dt = o.timetuple()
        dtt = time.mktime(dt)
        return int(dtt)
    return int(o)

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
def get_queue(disk_queue, *a, mem_size=DEFAULT_MEMORY_SIZE, disk_size=DEFAULT_DISK_SIZE):
    k = (disk_queue,mem_size) + a
    if disk_queue is not None:
        k = k + (disk_size,)
    if k in _queue_cache:
        r = _queue_cache[k]()
        if r is not None:
            log.debug('get_queue k=%s; returning cached queue', k)
            return r
        else:
            log.debug('get_queue k=%s; key in cache, but weakref resolves to None')
    # XXX: the instanciation of the MQ or DBQ should consider/use options such as:
    # mem_size=blah disk_size=blah
    if disk_queue is None:
        log.debug('get_queue k=%s; returning new mem-queue', k)
        q = MemQueue(size=mem_size)
        _queue_cache[k] = weakref.ref(q)
    else:
        log.debug('get_queue k=%s; returning new disk-queue', k)
        q = DiskBackedQueue(disk_queue, mem_size=mem_size, disk_size=disk_size)
        _queue_cache[k] = weakref.ref(q)
    return q


class SendEventResult:
    OK_NO_PROBLEM      = 0
    CONNECTION_PROBLEM = 1
    SERVER_PROBLEM     = 2
    DATA_PROBLEM       = 4

    code = 0
    msg  = ''
    data = None

    def __init__(self, code, data, msg, *a, **kw):
        self.code = code
        if msg:
            log.error(msg, *a, **kw)

    @classmethod
    def connection_error(cls, msg, *a, **kw):
        return cls(cls.CONNECTION_PROBLEM, None, msg, *a, **kw)

    @classmethod
    def server_error(cls, msg, *a, **kw):
        return cls(cls.SERVER_PROBLEM, None, msg, *a, **kw)

    @classmethod
    def data_error(cls, msg, *a, **kw):
        return cls(cls.DATA_PROBLEM, None, msg, *a, **kw)

    @classmethod
    def data_ok(cls, data):
        return cls(cls.OK_NO_PROBLEM, data, '')

    @property
    def istransient(self):
        return self.code in (self.CONNECTION_PROBLEM, self.SERVER_PROBLEM)

    @property
    def ok(self):
        return self.code == self.OK_NO_PROBLEM

    def __bool__(self):
        return self.ok


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
        redirect_limit=10, retries=1, conn_timeout=2, read_timeout=2, backoff=3,
        disk_queue=None, mem_size=DEFAULT_MEMORY_SIZE, disk_size=DEFAULT_DISK_SIZE,
        base_payload=None, record_age_filter=27000000):

        self.record_age_filter = record_age_filter

        if base_payload is None or not isinstance(base_payload, dict):
            base_payload = dict()

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
            import certifi
            log.warning("using certifi (ignoring /etc/ssl/) for %s", self.url)
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

        self.base_payload = self.base_payload.copy()
        self.base_payload.update(base_payload)
        self.q = get_queue(disk_queue, self.url, self.token,
            mem_size=mem_size, disk_size=disk_size)

    def __str__(self):
        return f'HEC({self.url}{self.path})'
    __repr__ = __str__

    @property
    def urlpath(self):
        return self.url + self.path

    def _post_message(self, dat):
        headers = urllib3.make_headers( keep_alive=True, user_agent='sslf-hec/3.14', accept_encoding=True)
        headers.update({ 'Authorization': 'Splunk ' + self.token, 'Content-Type': 'application/json' })
        fake_headers = headers.copy()
        fake_data = dat[0:100] + '…'.encode('utf-8') if len(dat) > 100 else dat
        fake_headers['Authorization'] = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx' + headers['Authorization'][-4:]
        log.debug("HEC.pool_manager.request('POST', url=%s + path=%s, body=%s, headers=%s)",
            self.url, self.path, fake_data, fake_headers)
        return self.pool_manager.request('POST', self.urlpath, body=dat, headers=headers)

    def encode_event(self, event, **payload_data):
        jdargs = payload_data.pop('_jdargs', {})
        dat = self.base_payload.copy()
        dat.update(payload_data)
        if isinstance(event, dict) and 'event' in event:
            _event = event.pop('event')
            dat.update(event)
            event = _event
        if isinstance(event, str):
            event = event.strip()
        if not event:
            raise FilteredEvent('event must not be empty')
        dat['event'] = event
        _now = datetime.datetime.now()
        if 'time' not in dat:
            _e = event if isinstance(event, dict) else dict()
            dat['time'] = dat.get('fields', {}).get('time', _e.get('time'))
            if not dat.get('time'):
                dat['time'] = _now
        if self.record_age_filter and self.record_age_filter > 0:
            age = _mk_timestamp(_now) - _mk_timestamp(dat.get('time', 0))
            if age > self.record_age_filter:
                raise FilteredEvent('event is too old to bother with')
        return json.dumps(dat, cls=MyJSONEncoder, **jdargs).encode(self.charset)
    encode_payload = encode_event

    def _decode_res(self, res):
        try:
            dat = json.loads(res.data.decode(self.charset))

            if dat['code'] != 0:
                log.error('Splunk HEC Error code={code}: {text}'.format(**dat))

            return dat

        except json.JSONDecodeError as e:
            log.error('Unable to decode reply from Splunk HEC: %s', e)

    def _send_event(self, encoded_payload):

        if os.environ.get('SSLF_DEBUG_HEC_SEND_LOG'):
            log.info('writing encoded_payload(s) to /tmp/sslf-hec-send.log')
            with open('/tmp/sslf-hec-send.log', 'ab') as fh:
                fh.write(encoded_payload + b'\n')

        try:
            res = self._post_message(encoded_payload)
        except urllib3.exceptions.MaxRetryError:
            return SendEventResult.connection_error('max retry error connecting to %s', self.url)
        except urllib3.exceptions.ReadTimeoutError:
            return SendEventResult.connection_error('read timeout error connecting to %s', self.url)

        if res.status == 400:
            # 400 can be ok, further checking required Splunk will sometimes
            # give a data-format error or similar in the json
            #
            # XXX: we assume it's fine here, but we should probably check for
            # data format errors here (we're not checking anywhere else). OTOH,
            # it probably doesn't matter very much — splunk didn't accept it
            # and we're not going to re-queue it anyway.
            return SendEventResult.data_ok(self._decode_res(res))

        if res.status < 200 or res.status > 299:
            return SendEventResult.server_error('HTTP ERROR %d: %s', res.status, res.data)

        return SendEventResult.data_ok(self._decode_res(res))

    def send_event(self, event, **payload_data):
        try:
            encoded_payload = self.encode_event(event, **payload_data)
        except FilteredEvent as e:
            log.debug('filtering event: %s', e)
            return # silently discard filtered events
        return self._send_event(encoded_payload)

    def queue_event(self, event, **payload_data):
        ''' attempt to queue an event
            returns true when item is queued
            returns false when item is filtered or queue capacity exceeded
        '''
        try:
            self.q.put( self.encode_event(event, **payload_data) )
            return True
        except FilteredEvent as e:
            log.debug('filtering event: %s', e)
        except SSLFQueueCapacityError:
            log.warning("queue overflow during queue_event() … discarding event")

    def flush(self):
        flush_result = AttrDict(s=0, c=0, ok=True)
        while self.q.cn > 0:
            payloadz = self.q.getz()
            if not payloadz:
                break
            res = self._send_event(payloadz)
            if res.ok:
                flush_result['s'] += len(payloadz)
                flush_result['c'] += 1
            elif res.istransient:
                # this is probably a transient network problem or a transient
                # splunk problem; requeue and abort the flush-q
                self.q.unget(payloadz)
                flush_result['ok'] = False
                log.info('aborting flush() on %s due to network or splunk error', self.url)
                break
            else:
                # XXX: this could very well turn out to be an incorrect assumption
                # We assume:
                #   the 200 - 299 errors indicate a transient accept issue —
                #   probably a disk is full, or the system is busy or
                #   something?
                self.q.unget(payloadz)
                flush_result['ok'] = False
                break
        if flush_result.c > 0:
            log.info('sent events to %s, %d bytes, %d batches', self.url, flush_result.s, flush_result.c)
        return flush_result

HEC = MySplunkHEC
Returner = MySplunkHEC
