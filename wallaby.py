import operator
from functools import wraps, partial
from hask import H


class TypeConstructor(object):
    _globals = globals()

    def __init__(self, stateful=False):
        self.stateful = stateful

    @property
    def globals(self):
        return self._globals
    
    @globals.setter
    def globals(self, val):
        self._globals = val

    def __getitem__(self, key):
        return TypeWrapper(key, stateful=self.stateful)

    def __getattr__(self, name):
        return TypeWrapper(eval(name, self._globals), stateful=self.stateful)


class Chain(object):
    def __init__(self, val):
        self._chain = [val]
        self._val = val

    def _bind(self, other_chain):
        self._chain.append(other_chain._val)

    def __rshift__(self, w):
        self._bind(w)
        return self


class TypeWrapper(Chain):
    def __init__(self, t, stateful=False):
        partitioned = isinstance(t, tuple) and [x for x in t if x != str and callable(x) and hasattr(x, 'partition')]
        super(TypeWrapper, self).__init__(t[0] if partitioned else t)
        self.partition = None
        self.state = t if stateful else None
        if partitioned:
            self.state = t[0]
            self.partition = t[1:]

    def _bind(self, w):
        if self.state is None:
            self.state = w.state
        if self.partition is None:
            self.partition = w.partition
        return super(TypeWrapper, self)._bind(w)

    def __getitem__(self, n):
        return self._chain[n]

    def signature(self):
        init_sig = H / self._chain[0]
        return reduce(operator.rshift, self._chain[1:], init_sig)


class Pipeline(Chain):
    def __init__(self, comp, in_type, out_type, comp_name, state=None, partition=None):
        super(Pipeline, self).__init__(partial(self._executor, comp, state, partition))
        self.in_type = in_type
        self.out_type = out_type
        self.comp = comp
        self.comp_name = comp_name
        self.state = state

    def __call__(self, *args, **kwargs):
        return self.comp(*args, **kwargs)

    def _executor(self, comp, state, partition, ab):
        if state:
            if partition:
                ab.to_state_partition(comp, state, comp.__name__, *partition)
            else:
                ab.to_stateful(comp, state, comp.__name__)
        else:
            ab.to(comp)

    def _bind(self, p):
        in_ = p.in_type
        out = self.out_type
        if isinstance(out, tuple):
            out = out[0]
        if all([out, in_]) and (out != in_ and not issubclass(out, in_)):
            raise TypeError(
                "function '{in_func}' expects {in_type} or its subclasses as "
                "a first argument but {out_type} has been passed from '{out_func}'".format(
                    in_func=p.comp_name,
                    in_type=in_,
                    out_func=self.comp_name,
                    out_type=out
                )
            )
        self.out_type = p.out_type
        self.comp_name = p.comp_name
        return super(Pipeline, self)._bind(p)

    def init(self, ab):
        """
        Initialize application builder
        """
        for executor in self._chain:
            executor(ab)


class Source(Pipeline):
    def __init__(self, config, pipename):
        super(Pipeline, self).__init__(partial(self._executor, config, pipename))
        self.in_type = None
        self.out_type = None
        self.comp_name = ''

    def _executor(self, config, pipename, ab):
        ab.new_pipeline(pipename, config)


class Sink(Pipeline):
    def __init__(self, config):
        super(Pipeline, self).__init__(partial(self._executor, config))
        self.in_type = None
        self.out_type = None
        self.comp_name = ''

    def _executor(self, config, ab):
        ab.to_sink(config)


def computation(type_sig):
    """
    Convert a function into computation

    :param type_sig: type signature
    """
    def _decor(func):
        wraps_func = func if not isinstance(func, partial) else func.func
        func = wraps(wraps_func)(func ** type_sig.signature())
        return Pipeline(
            func, type_sig[0], type_sig[-1], func.__name__, 
            state=type_sig.state, partition=type_sig.partition
        )
    return _decor


T = TypeConstructor()
T.State = TypeConstructor(stateful=True)


__all__ = ['T', 'Sink', 'Source', 'computation']
