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

class TsharkEKProcessor(JSONEventProcessor):

    def json_post_process(self, item):
        if 'timestamp' in item and 'layers' in item:
            actual = dict()
            for lname,ldat in item['layers'].items():
                mdat = dict()
                rejected_fields = set()
                for k in ldat:
                    m = key_key_re.search(k)
                    if m:
                        log.debug('key_key_re.search(%s) -> %s', k, m.groups())
                        prefix, dissector, value_name = m.groups()
                        if dissector == lname:
                            mdat[value_name] = ldat[k]
                        else:
                            ds = dissector.split('_')
                            if ds[0] == lname:
                                dissector = '_'.join(ds[1:])
                            if dissector in mdat and not isinstance(mdat[dissector], dict):
                                mdat[dissector] = { 'value': mdat[dissector] }
                            elif dissector not in mdat:
                                mdat[dissector] = dict()
                            mdat[dissector][value_name] = ldat[k]
                    else:
                        rejected_fields.add(k)
                if rejected_fields:
                    other = dict()
                    for rf in rejected_fields:
                        _rf = rf
                        for bs in sorted(BS_REMAPS, key=lambda x: 0-len(x)):
                            _rf = _rf.replace(bs, BS_REMAPS[bs])
                        rfs = _rf.split('_')
                        o = { lname: mdat }
                        while rfs and isinstance(o, dict) and rfs[0] in o and isinstance(o[rfs[0]], dict):
                            o = o[rfs.pop(0)]
                        assert len(rfs) > 0
                        _rf = '_'.join(rfs)
                        if isinstance(o, dict) and o is not mdat and _rf != rf and _rf not in o:
                            o[_rf] = ldat[rf]
                            log.debug('reject( ldat[%s] --> o[%s] )', rf, _rf)
                        else:
                            other[rf] = ldat[rf]
                            log.debug('reject( other[%s] )', rf)
                    if other:
                        mdat['other'] = other
                if mdat:
                    actual[lname] = mdat
            if actual:
                actual['timestamp'] = item['timestamp']
                return super(TsharkEKProcessor, self).json_post_process(actual)
