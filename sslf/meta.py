import os
import simplejson as json
import logging

log = logging.getLogger('sslf:meta')

class MetaData:

    @property
    def meta_basename(self):
        return '{}.json'.format(self.mid.replace('/','_'))

    @property
    def meta_fname(self):
        return os.path.join(self.meta_data_dir, self.meta_basename)

    def save(self):
        os.makedirs(self.meta_data_dir, exist_ok=True)
        with open(self.meta_fname, 'w') as fh:
            json.dump(self.serialize(), fh)
            log.debug("saved %s to %s", self, self.meta_fname)

    def load(self):
        fname = self.meta_fname
        if os.path.isfile(fname):
            with open(self.meta_fname, 'r') as fh:
                try:
                    dat = json.load(fh)
                except json.decoder.JSONDecodeError as e:
                    log.error("failed to load %s: %s", self.meta_fname, e)
                    return
            self.deserialize(dat)
