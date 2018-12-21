
import logging
import re

from sslf.reader.cmdjson import Reader as CmdJSONReader

log = logging.getLogger('sslf:read:tshark')

key_key_re = re.compile(r'^((.+)_)\1(.+)')

class Reader(CmdJSONReader):
    def __init__(self, *a, **kw):
        if 'config' not in kw:
            kw['config'] = dict()
        kw['config']['parse_time'] = 'timestamp'
        super(Reader, self).__init__(*a, **kw)

    def compute_command(self, config):
        kw = {
            'local_src': '(src net 10.0.0.0/8 or src net 192.168.0.0/16)',
            'local_dst': '(dst net 10.0.0.0/8 or dst net 192.168.0.0/16)',
            'tcp_syn':   'tcp[tcpflags] & tcp-syn != 0',
        }

        kw['out']    = '({local_src} and not {local_dst})'
        kw['in']     = '({local_dst} and not {local_src})'
        kw['in_out'] = '({out} or {in})'
        kw.update(config)

        filter     = config.get('pcap_filter', '{tcp_syn} and {in_out}')
        interface  = config.get('interface', 'eth0')
        out_proto  = config.get('out_proto', 'ip tcp')
        dns        = config.get('dns', False)

        self.out_proto = out_proto.split()

        max = 50
        while max > 0 and '{' in filter and '}' in filter:
            filter = filter.format(**kw)
            max -= 1

        # cmd = tshark -i eth0 -T ek -f 'net 10.2.3.4/23 and tcp[tcpflags] & tcp-syn != 0' -nj ip
        cmd = f'tshark -i {interface} -T ek -f "{filter}"'
        if out_proto:
            cmd += f' -j "{out_proto}"'
        if not dns:
            cmd += ' -n'
        return cmd

    def json_post_process(self, item):
        if 'timestamp' in item and 'layers' in item:
            actual = dict()
            for lname,ldat in item['layers'].items():
                mdat = dict()
                pre_dis = set()
                rejected_fields = set()
                for k in ldat:
                    m = key_key_re.search(k)
                    if m:
                        log.debug('key_key_re.search(%s) -> %s', k, m.groups())
                        prefix, dissector, value_name = m.groups()
                        pre_dis.add( (prefix,dissector) )
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
                #if todo_keys and todo_reject:
                #    r = re.compile('^(' + '|'.join(todo_prefixes) + ')_(.+)')
                if mdat:
                    actual[lname] = mdat
            if actual:
                actual['timestamp'] = item['timestamp']
                import simplejson as json
                log.debug(f'WTF( {json.dumps(actual, indent=2)} )')
                return super(Reader, self).json_post_process(actual)
