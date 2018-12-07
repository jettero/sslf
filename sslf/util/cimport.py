import importlib

def mod_cls_split(x, namespace, classname):
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

def find_namespaced_class(x, namespace, classname):
    module, clazz = mod_cls_split(x, namespace, classname)

    try:
        m = importlib.import_module(module)
        c = getattr(m, clazz)
        return c
    except ModuleNotFoundError as e:
        raise Exception(f"couldn't find x={x} as {module}.{clazz}") from e


