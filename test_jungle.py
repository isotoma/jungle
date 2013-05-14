
import wingdbstub

from unittest import TestCase, main
import mock

import os
import jungle
from jungle import Jungle, cmd, parse_command
from distutils.version import StrictVersion

jungle.stderr = mock.MagicMock()

class multipatch:
    
    """ Mock a bunch of functions at once """
    
    def __init__(self, *items):
        self.mocks = {}
        self.managers = []
        self.items = items
    
    def __enter__(self):
        for i in self.items:
            self.patch(i)
        return self
    
    def patch(self, term):
        m = mock.patch(term)
        self.managers.append(m)
        self.mocks[term] = m.__enter__()
        
    def __exit__(self, *args):
        for m in self.managers:
            m.__exit__(*args)
            
    def __getitem__(self, k):
        if k not in self.mocks:
            self.patch(k)
        return self.mocks[k]

class CommandParseTest(TestCase):
    
    def test_empty(self):
        self.assertEqual(parse_command([]),
                         (cmd.do_help, {}, []))
        
    def test_unrecognised_command(self):
        self.assertRaises(SystemExit, parse_command, ['foo'])
        ## could also test error output
        
    def test_unrecognised_argument(self):
        self.assertRaises(SystemExit, parse_command, ['-x'])
        ## could also test error output
        
    def test_verbose(self):
        self.assertEqual(jungle.verbose, False)
        parse_command(['-v'])
        self.assertEqual(jungle.verbose, True)
        
    def test_init(self):
        self.assertEqual(parse_command(['init']), (cmd.do_init, {}, []))
        self.assertEqual(parse_command(['init', '/foo']), (cmd.do_init, {}, ['/foo']))
        
class JungleTest(TestCase):
    
    def test_init(self):
        self.assertRaises(OSError, Jungle, "/foo")
        self.assertRaises(OSError, Jungle, "/etc/hosts")
    
    def test_versions(self):
        ldrv = [['1.0', '2.0', 'bin', '1.3b1'],
                ['bin'],
                []]
        with multipatch() as m:
            m['os.listdir'].side_effect = lambda x: ldrv.pop(0)
            m['os.path.exists'].return_value = True
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            # with versions
            self.assertEqual(list(j.versions()),
                             [StrictVersion('1.0'),
                             StrictVersion('1.3b1'),
                             StrictVersion('2.0')])
            # just bin
            self.assertEqual(list(j.versions()), [])
            # empty
            self.assertEqual(list(j.versions()), [])
    
    def test_head(self):
        ldrv = [['1.0', '2.0', 'bin', '1.3b1'],
                ['bin']]
        with multipatch() as m:
            m['os.listdir'].side_effect = lambda x: ldrv.pop(0)
            m['os.path.exists'].return_value = True
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            self.assertEqual(j.head(), "2.0")
            self.assertRaises(ValueError, j.head)
            
    def test_initialise_no_versions(self):
        with multipatch() as m:
            m['os.listdir'].return_value = ['bin']
            m['os.path.exists'].return_value = True
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            self.assertRaises(SystemExit, j.initialise)

    def test_initialise_with_current(self):
        with multipatch() as m:
            m['os.listdir'].return_value = ['1.0']
            m['os.path.exists'].return_value = True
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            self.assertRaises(SystemExit, j.initialise)

    def _exists(self, *missing):
        def exists(v):
            return not v in missing
        return exists
            
    def test_initialise(self):
        with multipatch('os.symlink', 'os.rename') as m:
            m['os.listdir'].return_value = ['1.0']
            m['os.path.exists'].side_effect = self._exists("/t/current")
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            j.initialise()
            m['os.symlink'].assert_called_with('1.0', '/t/current.new')
            m['os.rename'].assert_called_with("/t/current.new", "/t/current")
                
        
if __name__ == '__main__':
    main()
                         
        