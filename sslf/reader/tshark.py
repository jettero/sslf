
import logging

from sslf.reader.cmdjson import Reader as CmdJSONReader

log = logging.getLogger('sslf:read:tshark')

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
        cmd = f'tshark -i {interface} -T ek -f "{filter}" -j "{out_proto}"'
        if not dns:
            cmd += ' -n'
        return cmd

    def json_post_process(self, item):
        if 'timestamp' in item and 'layers' in item:
            actual = dict()
            for op in self.out_proto:
                ldat = item['layers'][op]
                mdat = dict()
                for lk in ldat:
                    opp = op + '_'
                    if lk.startswith(opp):
                        mk = lk
                        while mk.startswith(opp):
                            mk = mk[len(opp):]
                        mdat[mk] = ldat[lk]
                if mdat:
                    actual[op] = mdat
            if actual:
                actual['timestamp'] = item['timestamp']
                return super(Reader, self).json_post_process(actual)
