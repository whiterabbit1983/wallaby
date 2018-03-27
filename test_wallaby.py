import unittest
from wallaby import TypeConstructor, TypeWrapper, T


class TestTypeWrapper(unittest.TestCase):
    def test_type_chain(self):
        class C: pass
        t = TypeWrapper(str) >> TypeWrapper(int) >> TypeWrapper(bool) >> TypeWrapper(C)
        self.assertEqual(t._chain, [str, int, bool, C])

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
    def test_getitem(self):
        t = TypeConstructor()
        w = t[int]
        self.assertIsInstance(w, TypeWrapper)
        self.assertEqual(w._val, int)
        self.assertEqual(w._chain, [int])
    
    def test_T_function_signatures(self):
        def f():
            return ''
        
        def f1(i):
            return str(i)
        
        def f2(i, s):
            return i + int(s)
        
        t1 = T[str]
        t2 = T[int] >> T[str]
        t3 = T[int] >> T[str] >> T[int]
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
    
    def test_T_function_signatures_use_attributes(self):
        class C: pass
        class D:
            def __init__(self, c):
                pass

        def f():
            return ''
        
        def f1(i):
            return str(i)
        
        def f2(i, s):
            return i + int(s)
        
        def f3(c):
            return D(c)

        t1 = T.str
        t2 = T.int >> T.str
        t3 = T.int >> T.str >> T.int
        t4 = T.C >> T.D
        # f = f ** t1.signature()
        f1 = f1 ** t2.signature()
        f2 = f2 ** t3.signature()
        f3 = f3 ** t4.signature()
        # self.assertEqual(f(), '')
        self.assertEqual(f1(2), '2')
        with self.assertRaises(TypeError):
            f1('2')
        self.assertEqual(f2(3, '5'), 8)
        with self.assertRaises(TypeError):
            f2('2', '3')
        self.assertIsInstance(f3(C()), D)
        with self.assertRaises(TypeError):
            f3(D(C()))


constructor_suite = unittest.TestLoader().loadTestsFromTestCase(TestTypeConstructor)
wrapper_suite = unittest.TestLoader().loadTestsFromTestCase(TestTypeWrapper)
suite = unittest.TestSuite([
    constructor_suite,
    wrapper_suite
])


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)