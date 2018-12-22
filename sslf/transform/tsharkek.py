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
                                mdat[dissector] = { 'val': mdat[dissector] }
                            elif dissector not in mdat:
                                mdat[dissector] = dict()
                            mdat[dissector][value_name] = ldat[k]
                    else:
                        rejected_fields.add(k)
                if mdat:
                    if rejected_fields:
                        mdat['other'] = { rf: ldat[rf] for rf in rejected_fields }
                    actual[lname] = mdat
            if actual:
                actual['timestamp'] = item['timestamp']
                return super(TsharkEKProcessor, self).json_post_process(actual)
