
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
        jungle.verbose = False
        
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
            
    def test_oldest(self):
        with multipatch() as m:
            m['os.listdir'].return_value = ['1.0', '2.0', '1.3b1']
            m['os.path.exists'].return_value = True
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            self.assertEqual(j.oldest(), '1.0')

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
            
    def test_set_no_current(self):
        with multipatch('os.symlink', 'os.rename') as m:
            m['os.listdir'].return_value = ['1.0']
            m['os.path.exists'].side_effect = self._exists("/t/current")
            m['os.path.isdir'].return_value = True
            j = Jungle("/t")
            self.assertRaises(OSError, j.set, '1.0')

    def _pass_current_checks(self, m):
        """ Set up the patches needed to pass the checks on current """
        m['os.path.exists'].return_value = True
        m['os.path.islink'].return_value = True
        m['os.path.isdir'].return_value = True
        m['os.readlink'].return_value = '1.0'
        
    def test_check_current(self):
        with multipatch() as m:
            self._pass_current_checks(m)
            j = Jungle("/t")
            j.check_current()
        
    def test_set(self):        
        with multipatch('os.symlink', 'os.rename') as m:
            self._pass_current_checks(m)
            m['os.listdir'].return_value = ['1.0']
            m['os.path.exists'].side_effect = self._exists("/t/current")
            j = Jungle("/t")
            j.initialise()
            m['os.symlink'].assert_called_with('1.0', '/t/current.new')
            m['os.rename'].assert_called_with("/t/current.new", "/t/current")
            # now set it to 2.0
            m['os.listdir'].return_value = ['1.0', '2.0']
            m['os.path.exists'].side_effect = self._exists()
            j.set('2.0')
            m['os.symlink'].assert_called_with('2.0', '/t/current.new')
            m['os.rename'].assert_called_with("/t/current.new", "/t/current")
            
    def test_delete(self):
        with multipatch('shutil.rmtree') as m:
            self._pass_current_checks(m)
            j = Jungle("/t")
            j.delete("2.0")
            m['shutil.rmtree'].asset_called_with('/t/2.0')

    def test_degrade(self):
        with multipatch('os.symlink', 'os.rename') as m:
            m['os.listdir'].return_value = ['1.0', '2.0', '1.0b3']
            self._pass_current_checks(m)
            j = Jungle("/t")
            rv = j.degrade()
            self.assertEqual(rv, '1.0')
            m['os.symlink'].assert_called_with('1.0', '/t/current.new')
            
    def test_latest(self):
        with multipatch('os.symlink', 'os.rename') as m:
            m['os.listdir'].return_value = ['1.0', '2.0', '1.0b3']
            self._pass_current_checks(m)
            j = Jungle("/t")
            v = j.latest()
            self.assertEqual(v, '2.0')
            m['os.symlink'].assert_called_with('2.0', '/t/current.new')
            
    def test_current(self):
        with multipatch() as m:
            self._pass_current_checks(m)
            m['os.readlink'].return_value = '2.0'
            j = Jungle("/t")
            self.assertEqual(j.current(), '2.0')
            
    def test_status(self):
        with multipatch() as m:
            self._pass_current_checks(m)
            m['os.listdir'].return_value = ['1.0', '2.0', '1.0b3']
            m['os.readlink'].return_value = '2.0'
            j = Jungle("/t")
            self.assertEqual(j.status(), 'current')
            m['os.readlink'].return_value = '1.0'
            self.assertEqual(j.status(), 'degraded')
        
    def test_age(self):
        def fake_stat(t):
            l = [None]*9
            l[8] = t
            return l
        with multipatch() as m:
            self._pass_current_checks(m)
            m['time.time'].return_value = 10*24*3600
            m['os.stat'].return_value = fake_stat(0)
            j = Jungle("/t")
            self.assertEqual(j.age("foo"), 10)
            m['os.stat'].return_value = fake_stat(9*24*3600)
            self.assertEqual(j.age("foo"), 1)
            m['os.stat'].return_value = fake_stat(9*24*3600+1800)
            self.assertEqual(j.age("foo"), 0)
    
    def test_prune_age(self):
        ages = {
            '/t/1.0': 10,
            '/t/1.0b3': 9,
            '/t/1.2': 5,
            '/t/2.0': 3
        }
        def fake_stat(pathname):
            l = [None]*9
            l[8] = (10 - ages[pathname])*24*3600
            return l
        
        def setup():
            self._pass_current_checks(m)
            m['os.listdir'].return_value = ['1.0', '2.0', '1.0b3', '1.2']
            m['time.time'].return_value = 10*24*3600
            m['os.stat'].side_effect = fake_stat
            m['os.readlink'].return_value = '2.0'
            
        with multipatch('shutil.rmtree') as m:
            setup()
            j = Jungle("/t")
            j.prune_age(9)
            m['shutil.rmtree'].assert_called_with('/t/1.0')

        with multipatch('shutil.rmtree') as m:
            setup()
            j = Jungle("/t")
            j.prune_age(5)
            m['shutil.rmtree'].assert_any_call_with('/t/1.0b3')
            m['shutil.rmtree'].assert_any_call_with('/t/1.0')

        with multipatch('shutil.rmtree') as m:
            setup()
            j = Jungle("/t")
            j.prune_age(0)
            m['shutil.rmtree'].assert_any_call_with('/t/1.0b3')
            m['shutil.rmtree'].assert_any_call_with('/t/1.0')
            m['shutil.rmtree'].assert_any_call_with('/t/1.2')
        
    def test_prune_iterations(self):
        versions = ['1.0', '2.0', '1.0b3', '1.1', '1.5']
        def fake_rmtree(pathname):
            versions.remove(os.path.basename(pathname))
        with multipatch() as m:
            self._pass_current_checks(m)
            m['os.listdir'].side_effect = lambda x: versions
            m['os.readlink'].return_value = '2.0'
            m['shutil.rmtree'].side_effect = fake_rmtree
            j = Jungle("/t")
            j.prune_iterations(3)
            self.assertEqual(m['shutil.rmtree'].call_count, 2)
            m['shutil.rmtree'].assert_any_call_with('/t/1.0b3')
            m['shutil.rmtree'].assert_any_call_with('/t/1.0')
            
if __name__ == '__main__':
    main()
                         
        