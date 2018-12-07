import importlib

def mod_cls_split(x, classname='Reader', namespace='sslf.reader'):
    x = x.rsplit('.',1)
    if len(x) == 1:
        # reader = lines / aka x[0]
        # module: sslf.reader.lines / aka defnamespace + x[0]
        # class: Reader
        return f'{namespace}.{x[0]}', classname
    if '.' not in x[0]:
        # reader = lines.Reader
        # module: sslf.reader.lines
        # class: Reader
        return f'{namespace}.{x[0]}', x[1]
    return x[0], x[1]

def find_namespaced_object(x, classname='Reader', namespace='sslf.reader', oargs=None, okwargs=None):
    module, clazz = mod_cls_split(x, classname=classname, namespace=namespace)

    if oargs is None:
        oargs = tuple()

    if okwargs is None:
        okwargs = dict()

    try:
        m = importlib.import_module(module)
        c = getattr(m, clazz)
        o = c(*oargs, **okwargs)
        return o
    except ModuleNotFoundError as e:
        raise Exception(f"couldn't find x={x} as {module}.{clazz}()") from e


