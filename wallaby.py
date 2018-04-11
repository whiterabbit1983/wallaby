import operator
import wallaroo
import hask
from functools import wraps, partial
from hask import H
from hask.lang.syntax import Syntax, __signature__
from hask.lang.type_system import build_sig, make_fn_type, TypedFunc


class sig(Syntax):
    def __init__(self, signature):
        super(self.__class__, self).__init__("Syntax error in type signature")

        if not isinstance(signature, __signature__):
            msg = "Signature expected in sig(); found %s" % signature
            raise SyntaxError(msg)

        elif len(signature.sig.args) < 2:
            raise SyntaxError("Not enough type arguments in signature")

        self.sig = signature.sig
        return

    def __call__(self, fn):
        fn_args = build_sig(self.sig)
        fn_type = make_fn_type(fn_args)
        obj = TypedFunc(fn, fn_args, fn_type)
        obj.__name__ = fn.__name__ if not isinstance(fn, partial) else fn.func.__name__
        obj.__doc__ = fn.__doc__
        return obj


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
        stateless = wallaroo.computation(name=self.comp_name)
        stateful = wallaroo.state_computation(name=self.comp_name)
        if state:
            if partition:
                ab.to_state_partition(stateful(comp), state, self.comp_name, *partition)
            else:
                ab.to_stateful(stateful(comp), state, self.comp_name)
        else:
            ab.to(stateless(comp))

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
        # self.comp_name = p.comp_name
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
        comp_name = func.__name__ if not isinstance(func, partial) else func.func.__name__
        func = (sig(type_sig.signature())(func))
        return Pipeline(
            func, type_sig[0], type_sig[-1], comp_name, 
            state=type_sig.state, partition=type_sig.partition
        )
    return _decor


T = TypeConstructor()
T.State = TypeConstructor(stateful=True)


__all__ = ['T', 'Sink', 'Source', 'computation']
