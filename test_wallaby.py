import string
import unittest
import mock
import wallaroo
from functools import partial
from wallaby import (
    TypeConstructor, TypeWrapper, T, 
    Source, Sink, Pipeline, computation
)


class TestTypeWrapper(unittest.TestCase):
    def test_type_chain(self):
        class C(object): pass
        t = TypeWrapper(str) >> TypeWrapper(int) >> TypeWrapper(bool) >> TypeWrapper(C)
        self.assertEqual(t._chain, [str, int, bool, C])
        self.assertIsNone(t.state)

    def test_stateful(self):
        class C(object): pass
        
        t = TypeWrapper(str) >> TypeWrapper(C, stateful=True) >> TypeWrapper(bool) >> TypeWrapper(int)
        self.assertEqual(t._chain, [str, C, bool, int])
        self.assertTrue(t.state, C)

    def test_function_signatures(self):
        def f():
            return ''
        
        def f1(i):
            return str(i)
        
        def f2(i, s):
            return i + int(s)
        
        t1 = TypeWrapper(str)
        t2 = TypeWrapper(int) >> TypeWrapper(str)
        t3 = TypeWrapper(int) >> TypeWrapper(str) >> TypeWrapper(int)
        # f = f ** t1.signature()
        f1 = f1 ** t2.signature()
        f2 = f2 ** t3.signature()
        # self.assertEqual(f(), '')
        self.assertEqual(f1(2), '2')
        with self.assertRaises(TypeError):
            f1('2')
        self.assertEqual(f2(3, '5'), 8)
        with self.assertRaises(TypeError):
            f2('2', '3')


class TestTypeConstructor(unittest.TestCase):
    def test_stateful_constructor(self):
        w = T[str] >> T.State[str] >> T[str]
        self.assertIsInstance(w, TypeWrapper)
        self.assertEqual(w.state, str)
        w1 = T[str] >> T[str] >> T[str]
        self.assertIsInstance(w, TypeWrapper)
        self.assertIsNone(w1.state)

    def test_getitem(self):
        t = TypeConstructor()
        w = t[int]
        self.assertIsInstance(w, TypeWrapper)
        self.assertEqual(w._val, int)
        self.assertEqual(w._chain, [int])
    
    @unittest.expectedFailure
    def test_signatures_no_input_arguments(self):
        def f():
            return ''

        t1 = T[str]
        f = f ** t1.signature()
        self.assertEqual(f(), '')

    def test_T_function_signatures(self):
        def f1(i):
            return str(i)
        
        def f2(i, s):
            return i + int(s)
        
        t1 = T[str]
        t2 = T[int] >> T[str]
        t3 = T[int] >> T[str] >> T[int]
        f1 = f1 ** t2.signature()
        f2 = f2 ** t3.signature()
        self.assertEqual(f1(2), '2')
        with self.assertRaises(TypeError):
            f1('2')
        self.assertEqual(f2(3, '5'), 8)
        with self.assertRaises(TypeError):
            f2('2', '3')
    
    @unittest.expectedFailure
    def test_T_signatures_no_input_arguments(self):
        def f():
            return ''

        t1 = T.str
        f = f ** t1.signature()
        self.assertEqual(f(), '')

    def test_T_function_signatures_use_attributes(self):
        class C(object): pass
        class D(object):
            def __init__(self, c):
                pass

        def f1(i):
            return str(i)
        
        def f2(i, s):
            return i + int(s)
        
        def f3(c):
            return D(c)
        T.globals = locals()
        t1 = T.str
        t2 = T.int >> T.str
        t3 = T.int >> T.str >> T.int
        t4 = T.C >> T.D
        f1 = f1 ** t2.signature()
        f2 = f2 ** t3.signature()
        f3 = f3 ** t4.signature()
        self.assertEqual(f1(2), '2')
        with self.assertRaises(TypeError):
            f1('2')
        self.assertEqual(f2(3, '5'), 8)
        with self.assertRaises(TypeError):
            f2('2', '3')
        self.assertIsInstance(f3(C()), D)
        with self.assertRaises(TypeError):
            f3(D(C()))


class TestComputation(unittest.TestCase):
    def test_computation_error(self):
        @computation(T[str] >> T.State[str] >> T[int])
        def reverse(i, state):
            return i + 1, True

        with self.assertRaises(TypeError):
            reverse(3, 'a')

    def test_computation_curried(self):
        @computation(T[int] >> T.State[str] >> T[str, bool])
        def reverse(i, state):
            return str(i + 1) + state, True
        res = reverse(5)('a')
        self.assertEqual(res, ('6a', True))

    def test_stateless_computations(self):
        ab = mock.Mock()
        ab.to = mock.Mock()
        @computation(T[str] >> T[str])
        def reverse(data):
            return data[::-1]
        
        @computation(T[str] >> T[int])
        def add(data):
            return int(data) + 1

        pipeline = reverse >> add
        pipeline.init(ab)
        calls = ab.to.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertIn('add', str(calls[1][0][0]))
        with self.assertRaises(TypeError):
            pipeline = add >> reverse
    
    def test_stateful_computations(self):
        ab = mock.Mock()
        ab.to_stateful = mock.Mock()

        class MyState(object):
            def __init__(self):
                self._data = []

            def update(self, data):
                self._data.append(data)

        @computation(T[str] >> T.State[MyState] >> T[str, bool])
        def reverse(data, state):
            state.update(data)
            return data[::-1], True

        @computation(T[str] >> T.State[MyState] >> T[int, bool])
        def add(data, state):
            state.update(data)
            return (int(data) + 1, True)

        pipeline = reverse >> add
        pipeline.init(ab)
        calls = ab.to_stateful.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertEqual(calls[0][0][1:], (MyState, 'reverse'))
        self.assertIn('add', str(calls[1][0][0]))
        self.assertEqual(calls[1][0][1:], (MyState, 'add'))
        with self.assertRaises(TypeError):
            pipeline = add >> reverse

    def test_stateless_source_and_sink(self):
        config1 = mock.Mock()
        config2 = mock.Mock()
        ab = mock.Mock()
        ab.to = mock.Mock()
        ab.new_pipeline = mock.Mock()
        ab.to_sink = mock.Mock()

        @computation(T[str] >> T[str])
        def reverse(data):
            return data[::-1]
        
        @computation(T[str] >> T[int])
        def add(data):
            return int(data) + 1

        pipeline = Source(config1, 'new_pipeline') >> reverse >> add >> Sink(config2)
        pipeline.init(ab)
        calls = ab.to.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertIn('add', str(calls[1][0][0]))
        ab.new_pipeline.assert_called_with('new_pipeline', config1)
        ab.to_sink.assert_called_with(config2)
        with self.assertRaises(TypeError):
            pipeline = Source(config1, 'new_pipeline') >> add >> reverse >> Sink(config2)
    
    def test_type_checks_1(self):
        config1 = mock.Mock()
        config2 = mock.Mock()
        ab = mock.Mock()
        ab.to = mock.Mock()
        ab.new_pipeline = mock.Mock()
        ab.to_sink = mock.Mock()

        class C(object): pass
        class D(C): pass

        @computation(T[str] >> T[D])
        def reverse(data):
            return D()

        @computation(T[C] >> T[int])
        def add(data):
            return 1

        pipeline = Source(config1, 'new_pipeline') >> reverse >> add >> Sink(config2)
        pipeline.init(ab)
        calls = ab.to.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertIn('add', str(calls[1][0][0]))
        ab.new_pipeline.assert_called_with('new_pipeline', config1)
        ab.to_sink.assert_called_with(config2)
        with self.assertRaises(TypeError):
            pipeline = Source(config1, 'new_pipeline') >> add >> reverse >> Sink(config2)
    
    def test_type_checks_2(self):
        ab = mock.Mock()
        ab.to_stateful = mock.Mock()

        class C(object): pass
        class D(C): pass
        class MyState(object):
            def __init__(self):
                self._data = []

            def update(self, data):
                self._data.append(data)

        @computation(T[str] >> T.State[MyState] >> T[D, bool])
        def reverse(data, state):
            state.update(data)
            return D(), True

        @computation(T[C] >> T.State[MyState] >> T[int, bool])
        def add(data, state):
            state.update(data)
            return 1, True

        pipeline = reverse >> add
        pipeline.init(ab)
        calls = ab.to_stateful.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertIn('add', str(calls[1][0][0]))
        self.assertEqual(calls[0][0][1:], (MyState, 'reverse'))
        self.assertEqual(calls[1][0][1:], (MyState, 'add'))
        with self.assertRaises(TypeError):
            pipeline = add >> reverse

    def test_stateful_partitioned(self):
        ab = mock.Mock()
        ab.to_state_partition = mock.Mock()
        ab.to_stateful = mock.Mock()

        class MyState(object):
            def __init__(self):
                self._data = []

            def update(self, data):
                self._data.append(data)

        @wallaroo.partition
        def partition(data):
            return data.letter[0]
        part_keys = list(string.ascii_lowercase)

        @computation(T[str] >> T.State[MyState, partition, part_keys] >> T[str, bool])
        def reverse(data, state):
            state.update(data)
            return data[::-1], True

        @computation(T[str] >> T.State[MyState] >> T[int, bool])
        def add(data, state):
            state.update(data)
            return (int(data) + 1, True)

        pipeline = reverse >> add
        pipeline.init(ab)
        calls = ab.to_stateful.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertIn('add', str(calls[0][0][0]))
        self.assertEqual(calls[0][0][1:], (MyState, 'add'))
        calls = ab.to_state_partition.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertEqual(calls[0][0][1:], (MyState, 'reverse', partition, part_keys))
        with self.assertRaises(TypeError):
            pipeline = add >> reverse
    
    def test_stateful_partitioned_partial_application(self):
        ab = mock.Mock()
        ab.to_state_partition = mock.Mock()
        ab.to_stateful = mock.Mock()

        class MyState(object):
            def __init__(self):
                self._data = []

            def update(self, data):
                self._data.append(data)

        @wallaroo.partition
        def partition(data):
            return data.letter[0]
        part_keys = list(string.ascii_lowercase)

        @computation(T[str] >> T.State[MyState, partition, part_keys] >> T[str, bool])
        def reverse(data, state):
            state.update(data)
            return data[::-1], True

        def add(n, data, state):
            state.update(data)
            return (int(data) + n, True)
        add_one = computation(T[str] >> T.State[MyState] >> T[int, bool])(partial(add, 1))

        pipeline = reverse >> add_one
        pipeline.init(ab)
        calls = ab.to_stateful.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertIn('add', str(calls[0][0][0]))
        self.assertEqual(calls[0][0][1:], (MyState, 'add'))
        calls = ab.to_state_partition.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertIn('reverse', str(calls[0][0][0]))
        self.assertEqual(calls[0][0][1:], (MyState, 'reverse', partition, part_keys))
        with self.assertRaises(TypeError):
            pipeline = add >> reverse


constructor_suite = unittest.TestLoader().loadTestsFromTestCase(TestTypeConstructor)
wrapper_suite = unittest.TestLoader().loadTestsFromTestCase(TestTypeWrapper)
computation_suite = unittest.TestLoader().loadTestsFromTestCase(TestComputation)
suite = unittest.TestSuite([
    constructor_suite,
    wrapper_suite,
    computation_suite
])


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)