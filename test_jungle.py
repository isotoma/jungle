
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
        self.mgr = {}
        self.items = items
    
    def __enter__(self):
        for i in self.items:
            self.mgr[i] = mock.patch(i).__enter__()
        return self
    
    def __exit__(self, *args):
        for m in self.mgr.values():
            m.__exit__(*args)
            
    def __getitem__(self, k):
        if k not in self.mgr:
            self.mgr[k] = mock.patch(k).__enter__()
        return self.mgr[k]

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
        j = Jungle("/var/tmp")
        with mock.patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['1.0', '2.0', 'bin', '1.3b1']
            self.assertEqual(list(j.versions()),
                             [StrictVersion('1.0'),
                             StrictVersion('1.3b1'),
                             StrictVersion('2.0')])
            mock_listdir.return_value = ['bin']
            self.assertEqual(list(j.versions()),
                             [])
            mock_listdir.return_value = []
            self.assertEqual(list(j.versions()),
                             [])
    
    def test_head(self):
        j = Jungle("/var/tmp")
        with mock.patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['1.0', '2.0', 'bin', '1.3b1']
            self.assertEqual(j.head(), "2.0")
            mock_listdir.return_value = ['bin']
            self.assertRaises(ValueError, j.head)
            
    def test_initialise_no_versions(self):
        j = Jungle("/var/tmp")
        with mock.patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['bin']
            self.assertRaises(SystemExit, j.initialise)

    def test_initialise_with_current(self):
        j = Jungle("/var/tmp")
        with mock.patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['1.0']
            with mock.patch('os.path.exists') as mock_exists:
                mock_exists.return_value = True
                self.assertRaises(SystemExit, j.initialise)
            
    def test_initialise(self):
        def exists(v):
            return {
                '/t/current': False,
            }.get(v, True)
        with multipatch('os.symlink') as m:
            m['os.listdir'].return_value = ['1.0']
            m['os.path.exists'].side_effect = exists
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            j.initialise()
            m['os.symlink'].assert_called_with('1.0', '/t/current')
                
        
if __name__ == '__main__':
    main()
                         
        