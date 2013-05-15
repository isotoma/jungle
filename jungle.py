#!/usr/bin/env python

""" 

This script maintains a directory structure, inside a specified
directory, designed for multiple versions of a software stack to be deployed,\
by version number, with a symbolic link maintained to the "current" version.

This enables a swift rollback, by merely repointing the symlink.

We rely on distutils.version.StrictVersion to provide version comparison and
only accept the version numbers that module supports.

"""

import os
import sys
import optparse
import shutil
import stat
import time

from distutils.version import StrictVersion

try:
    import wingdbstub
except ImportError:
    pass

verbose = False
stderr = sys.stderr

class Jungle(object):
    
    def __init__(self, parent):
        if not os.path.exists(parent):
            raise OSError("No such directory: %r" % parent)
        if not os.path.isdir(parent):
            raise OSError("Is not a directory: %r" % parent)
        self.parent = parent # top level directory containing the jungle
        
    def versions(self):
        """ Return StrictVersion objects for every possible version. If
        something is not a valid version number we ignore it. """
        for item in sorted(os.listdir(self.parent)):
            try:
                yield StrictVersion(item)
            except ValueError, e:
                pass
        
    def oldest(self):
        """ Return the lowest version """
        return sorted(self.versions())[0]
    
    def exists(self, version):
        p = self.path(str(version))
        return os.path.isdir(p)
            
    def head(self):
        return max(self.versions())
     
    def path(self, path):
        if isinstance(path, StrictVersion):
            path = str(path)
        return os.path.join(self.parent, path)
                
    def initialise(self):
        """ Set up the appropriate current pointer """
        try:
            head = self.head()
        except ValueError:
            print >>stderr, "No versions in directory %r, cannot initialise" % self.parent
            raise SystemExit(-1)
        if os.path.exists(self.path("current")):
            print >>stderr, "Current already exists in %r, will not initialise existing jungle" % self.parent
            raise SystemExit(-1)
        self._set(self.head())
        
    def _set(self, version):
        if not self.exists(version):
            raise KeyError("Version %s does not exist" % version)
        os.symlink(str(version), self.path("current.new"))
        os.rename(self.path("current.new"), self.path("current"))
        
    def set(self, version):
        self.check_current()
        if not isinstance(version, StrictVersion):
            version = StrictVersion(version)
        if not os.path.exists(self.path("current")):
            raise OSError("No current exists for %s - is this an initialised jungle?" % self.parent)
        self._set(version)
        return version

    def delete(self, version):
        """ Delete the specified version. Raises an error if the specified
        version is current. """
        self.check_current()
        if not isinstance(version, StrictVersion):
            version = StrictVersion(version)
        if not self.exists(version):
            raise KeyError("Version %s does not exist" % version)
        if not os.path.exists(self.path("current")):
            raise OSError("No current exists for %s - is this an initialised jungle?" % self.parent)
        if verbose:
            print >>sys.stderr, "Deleting version %s" % (version,)
        shutil.rmtree(self.path(version))

    def latest(self):
        """ Set current to head """
        self.check_current()
        return self.set(self.head())
        
    def degrade(self, dry_run=False):
        """ Set current to head - 1 and returns the version chosen. If dry-run
        is True then just returns the version chosen. """
        self.check_current()
        v = list(self.versions())
        if len(v) < 2:
            raise ValueError("Not enough versions to rollback")
        previous = sorted(v)[-2]
        if not dry_run:
            self.set(previous)
        return str(previous)
    
    def check_current(self):
        """ Perform complete sanity checks on the status of current. Try to
        rule out any of the mental states a jungle could get into if someone
        tries to do stuff by hand. """
        current = self.path("current")
        if not os.path.exists(current):
            raise OSError("No current exists for %s - is this an initialised jungle?" % self.parent)
        if not os.path.islink(current):
            raise OSError("Current %s is not a symlink, bailing" % current)
        try:
            version = StrictVersion(os.readlink(current))
        except ValueError:
            raise OSError("Current %s does not point to a valid version!" % current)
        if not os.path.isdir(self.path(version)):
            raise OSError("Current does not point to a valid directory!" % current)
        return version
        
    def current(self):
        """ Return the version that current points to """
        current = self.check_current()
        return os.readlink(current)
        
    def status(self):
        """ Prints "current" or "degraded" depending on state """
        current = self.check_current()
        if current == self.head():
            return "current"
        return "degraded"
    
    def age(self, version):
        ftime = os.stat(self.path(version))[stat.ST_MTIME]
        now = time.time()
        age = now-ftime
        days = int(age/(60*60*24.0))
        return days
        
    def prune_age(self, age):
        """ Delete versions older than age days. Will not delete the current
        version. """
        self.check_current()
        for v in self.versions():
            if v == self.current():
                if verbose:
                    print "Skipping current"
            else:
                days = self.age(v)
                if days > age:
                    self.delete(v)
    
    def prune_iterations(self, n):
        """ Maintain a maximum of n versions. Will remove old versions until
        there are n remaining """
        self.check_current()
        while len(list(self.versions())) > n:
            self.delete(self.oldest())
        
    
class Cmd:
    
    def _parent(self, args, argc=1):
        if len(args) == 0:
            parent = os.getcwd()
            remaining = args
        elif len(args) == 1:
            parent = args[0]
            remaining = args[1:]
        if len(args) != argc:
            print >>stderr, "Too many arguments"
            raise SystemExit(-1)
        return parent, remaining
            
    def do_init(self, opts, args):
        parent, _ = self._parent(args)
        print "Initialising jungle in", parent
        j = Jungle(parent)
        j.initialise()
        
    def do_set(self, opts, args):
        parent, r = self._parent(args, argc=2)
        j = Jungle(parent)
        version = r[0]
        j.set(version)

    def do_upgrade(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        j.upgrade()

    def opts_degrade(self, p):
        p.add_option("--dry-run", default=False, action="store_true", help="don't make any changes")
        
    def do_degrade(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        j.degrade(dry_run=opts.dry_run)
    
    def do_current(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        j.current()
    
    def do_status(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        j.status()
        
    def opts_prune(self, p):
        p.add_option("--age", default=None, action="store_int", help="age in days to preserve")
        p.add_option("--iterations", default=None, action="store_int", help="iterations to preserve")
    
    def do_prune(self, opts, args):
        if (opts.age is None) == (opts.iterations is None):
            print >>sys.stderr, "One and only one of age or iterations must be chosen"
            raise SystemExit(-1)
        parent, _ = self._parent(args)
        j = Jungle(parent)
        if opts.age is not None:
            j.prune_age(opts.age)
        if opts.iterations is not None:
            j.prune_iterations(opts.iterations)
    
    def do_delete(self, opts, args):
        parent, r = self._parent(args, argc=2)
        j = Jungle(parent)
        version = r[0]
        j.delete(version)
    
    def do_help(self, opts, args):
        print "Help!"
        raise SystemExit(0)

cmd = Cmd()

def parse_command(args):
    """ Avoiding dependencies on things like argparse, to make this as simple
    and portable as possible. sigh. """

    global verbose
    if len(args) == 0:
        return cmd.do_help, {}, []
    while args and args[0].startswith("-"):
        if args[0] == '-v':
            verbose = True
            args = args[1:]
        else:
            print >>stderr, "Unrecognised argument: %s" % args[0]
            raise SystemExit(-1)
    if len(args) == 0:
        return cmd.do_help, {}, []
    command = args[0]
    func = getattr(cmd, "do_" + command, None)
    if func is None:
        print >>stderr, "Unrecognised command: %s" % args[0]
        raise SystemExit(-1)
    p = optparse.OptionParser(usage="")
    p.remove_option("-h")
    optfunc = getattr(cmd, "opts_" + command, lambda x: None)
    optfunc(p)
    opts, args = p.parse_args(args[1:])
    return func, opts, args

if __name__ == '__main__':
    func, opts, args = parse_command(sys.argv[1:])
    func(opts, args)
    