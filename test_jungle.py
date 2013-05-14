
from unittest import TestCase, main
import mock

import os
import jungle
from jungle import Jungle, cmd, parse_command
from distutils.version import StrictVersion

jungle.stderr = mock.MagicMock()

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
                          
        
if __name__ == '__main__':
    main()
                         
        