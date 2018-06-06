
class AttrDict(dict):
    def __getattribute__(self, name):
        try: return super(AttrDict, self).__getattribute__(name)
        except: pass
        return self.get(name)
