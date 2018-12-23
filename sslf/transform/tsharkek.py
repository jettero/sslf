# coding: utf-8

import logging
import re

from .json import JSONEventProcessor

log = logging.getLogger("sslf:trans:tsharkek")

key_key_re = re.compile(r'^((.+)_)\1(.+)')

BS_REMAPS = {
    'text_tcp_option':  'tcp_options_text',
    'text_tcp_options': 'tcp_options_text',
}

def lname_set(dat, rounds=1):
    for _ in range(rounds):
        dat = [ i.rsplit('_',1) for i in dat ]
        dat = set( i[0] for i in dat if len(i)>1 )
    return dat

def _dedup_key_prefix(dat, lname):
    if lname not in dat:
        dat[lname] = dict()
    elif not isinstance(dat[lname], dict):
        dat[lname] = { 'val': dat[lname] }
    for k in [ k for k in dat if k.startswith(lname + '_') ]:
        j = k[len(lname)+1:]
        dat[lname][j] = dat.pop(k)
    return dedup_key_prefixes( dat[lname] )

def dedup_key_prefixes(dat):
    r = 0
    ls = True
    while ls:
        r += 1
        ls = lname_set(dat, r)
        log.debug("dedup_key_prefixes(%s)", ls)
        for lname in ls:
            if lname in dat:
                _dedup_key_prefix(dat, lname)
    for lname in lname_set(dat):
        _dedup_key_prefix(dat, lname)
    return dat

class TsharkEKProcessor(JSONEventProcessor):

    def json_post_process(self, item, dedup=True):
        if 'timestamp' in item and 'layers' in item:
            actual = dict()
            for lname,ldat in item['layers'].items():
                mdat = dict()
                rejected_fields = set()
                for lk in ldat:
                    k = lk
                    for bs in sorted(BS_REMAPS, key=lambda x: 0-len(x)):
                        k = k.replace(bs, BS_REMAPS[bs])
                    m = key_key_re.search(k)
                    if m:
                        log.debug('key_key_re.search(%s) -> %s', lk, m.groups())
                        prefix, dissector, value_name = m.groups()
                        if dissector == lname:
                            mdat[value_name] = ldat[lk]
                        else:
                            ds = dissector.split('_')
                            if ds[0] == lname:
                                dissector = '_'.join(ds[1:])
                            if dissector in mdat and not isinstance(mdat[dissector], dict):
                                mdat[dissector] = { 'val': mdat[dissector] }
                            elif dissector not in mdat:
                                mdat[dissector] = dict()
                            mdat[dissector][value_name] = ldat[lk]
                    else:
                        rejected_fields.add((k,lk))
                if mdat:
                    if rejected_fields:
                        for k,rf in rejected_fields:
                            if k.startswith(lname + '_'):
                                k = k[len(lname)+1:]
                            while k in mdat:
                                k += '_'
                            log.debug('reject( %s ) -> %s', rf, k)
                            mdat[k] = ldat[rf]
                    actual[lname] = dedup_key_prefixes(mdat) if dedup else mdat
            if actual:
                actual['timestamp'] = item['timestamp']
                return super(TsharkEKProcessor, self).json_post_process(actual)
