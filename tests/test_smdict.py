import unittest

import sys

xdart_dir = 'C:/Users/walroth/Documents/repos/xdart/'
if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.modules.datashare import SMDict


def summed(a, b):
    return a + b


def message_summed(a, b, message):
    return f"summed: {summed(a, b)}, message:{message}"


class TestSMDict(unittest.TestCase):
    def test_init(self):
        smdict = SMDict()
        smdict2 = SMDict(addr=smdict.name())

        smdict['a'] = 5
        self.assertEqual(smdict2['a'], 5)

    def test_setget(self):
        smdict = SMDict()
        smdict2 = SMDict(smdict.name())
        smdict['a'] = 5
        smdict['b'] = 'test'
        smdict['c'] = {'a':4, 'b':5}
        smdict['d'] = [0,2,3,4]
        smdict['e'] = ['a','b',1,2]
        smdict['a'] = [2,3,4]
        test = {}
        test.update(smdict)
        print(test)
        print(smdict)
        self.assertEqual(smdict, smdict2)

    def test_update(self):
        smdict = SMDict()
        smdict2 = SMDict(addr=smdict.name())
        test = {'a':5, 'b':6}
        smdict.update(test)
        self.assertEqual(smdict, test)
        self.assertEqual(smdict2, test)

    def test_kwargs(self):
        test = {'a': 5, 'b': 6, 'message': "test finished"}
        smdict = SMDict()
        smdict.update(test)
        self.assertEqual(message_summed(**smdict), message_summed(**test))


if __name__ == '__main__':
    unittest.main()
