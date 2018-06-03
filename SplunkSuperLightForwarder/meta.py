import os
import jsonpickle

class MetaData(object):

    @property
    def _mid(self):
        try:
            assert self.mid is not None
            return self.mid
        except:
            raise Exception("{} failed to define a meta-data-id in @mid".format(self.__class__.__name__))

    @property
    def _meta_data_dir(self):
        try:
            assert self.meta_data_dir is not None
            return self.meta_data_dir
        except:
            raise Exception("{} failed to define a meta-data-dir".format(self.__class__.__name__))

    def save(self):
        fname = os.path.join(self._meta_data_dir, '{}.json'.format(self._mid))
        with open(fname, 'w') as fh:
            fh.write( jsonpickle.dumps(self) )
