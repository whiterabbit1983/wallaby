import operator
from functools import wraps, partial
from hask import H


class TypeConstructor(object):
    def __getitem__(self, key):
        return TypeWrapper(key)

    def __getattr__(self, name):
        return TypeWrapper(eval(name))


class StateConstructor(TypeConstructor):
    pass


class Chain(object):
    def __init__(self, val):
        self._chain = [val]
        self._val = val

    def _action(self, other_chain):
        self._chain.append(other_chain._val)

    def __rshift__(self, w):
        self._action(w)
        return self


class TypeWrapper(Chain):
    def signature(self):
        init_sig = H / self._chain[0]
        return reduce(operator.rshift, self._chain[1:], init_sig)


class Pipeline(Chain):
    def __init__(self, comp, state=None):
        super(Computation, self).__init__(partial(self._executor, comp, state))

    def _executor(self, comp, state, ab):
        if state:
            ab.to_stateful(comp, state, comp.__name__)
        else:
            ab.to(comp, comp.__name__)

    def init(self, ab):
        """
        Initialize application builder
        """
        for executor in self._chain:
            executor(ab)


class Source(Pipeline):
    def __init__(self, config, pipename):
        super().__init__(partial(self._executor, config, pipename))

    def _executor(self, config, pipename, ab):
        ab.new_pipeline(pipename, config)


class Sink(Pipeline):
    def __init__(self, config):
        super().__init__(partial(self._executor, config))
    
    def _executor(self, config, ab):
        ab.to_sink(config)


def computation(type_sig):
    """
    Convert a function into computation

    :param type_sig: type signature
    """
    def _decor(func):
        func = wraps(func)(func ** type_sig.signature())
        # TODO: get the state from signature
        state = None
        return Pipeline(func, state=state)
    return _decor


T = TypeConstructor()
T.State = StateConstructor()

__all__ = ['T', 'Sink', 'Source', 'computation']
