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

verbose = False
stderr = sys.stderr

class Jungle(object):
    
    def __init__(self, parent):
        if not os.path.exists(parent):
            raise OSError("No such directory: %r" % parent)
        if not os.path.isdir(parent):
            raise OSError("Is not a directory: %r" % parent)
        self.parent = parent # top level directory containing the jungle
        self.release = os.path.join(self.parent, "release")
        self.current = os.path.join(self.parent, "current")
        self.current_new = os.path.join(self.parent, "current.new")
        
    def versions(self):
        """ Return StrictVersion objects for every possible version. If
        something is not a valid version number we ignore it. """
        for item in sorted(os.listdir(self.release)):
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
        return os.path.join(self.release, path)
                
    def initialise(self):
        """ Set up the appropriate current pointer """
        if os.path.exists(self.current):
            print >>stderr, "Current already exists in %r, will not initialise existing jungle" % self.parent
            raise SystemExit(-1)
        if not os.path.exists(self.release):
            print >>stderr, "No release directory exists in %r" % self.parent
            raise SystemExit(-1)
        try:
            head = self.head()
        except ValueError:
            print >>stderr, "No versions in directory %r, cannot initialise" % self.release
            raise SystemExit(-1)
        self._set(self.head())
        
    def _set(self, version):
        if not self.exists(version):
            raise KeyError("Version %s does not exist" % version)
        os.symlink("release/" + str(version), self.current_new)
        os.rename(self.current_new, self.current)
        
    def set(self, version):
        self.check_current()
        if not isinstance(version, StrictVersion):
            version = StrictVersion(version)
        if not os.path.exists(self.current):
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
        if not os.path.exists(self.current):
            raise OSError("No current exists for %s - is this an initialised jungle?" % self.parent)
        if version == self.current_version():
            raise OSError("Will not delete current version")
        if verbose:
            print >>sys.stderr, "Deleting version %s" % (version,)
        shutil.rmtree(self.path(version))

    def upgrade(self):
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
        current = self.current
        if not os.path.exists(current):
            raise OSError("No current exists for %s - is this an initialised jungle?" % self.parent)
        if not os.path.islink(current):
            raise OSError("Current %s is not a symlink, bailing" % current)
        ln = os.readlink(current)
        if not ln.startswith("release/"):
            raise OSError("Current %s does not point to something in release!" % current)
        try:
            version = StrictVersion(ln[8:])
        except ValueError:
            raise OSError("Current %s does not point to a valid version!" % current)
        if not os.path.isdir(self.path(version)):
            raise OSError("Current does not point to a valid directory!" % current)
        return version

    current_version = check_current
    
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
            if v == self.current_version():
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
            if self.oldest() == self.current_version():
                raise OSError("I won't delete the current version, bailing.")
            self.delete(self.oldest())
        
    
class Cmd:
    
    def _parent(self, args, argc=1):
        if argc == 1:
            if len(args) == 0:
                parent = os.getcwd()
                remaining = args
            elif len(args) == 1:
                parent = args[0]
                remaining = args[1:]
            else:
                print >> stderr, "Wrong arguments"
                raise SystemExit(-1)
        elif argc == 2:
            if len(args) == 0:
                parent = os.getcwd()
                remaining = args
            elif len(args) == 1:
                parent = os.getcwd()
                remaining = args
            elif len(args) == 2:
                parent = args[0]
                remaining = args[1:]
            else:
                print >> stderr, "Wrong arguments"
                raise SystemExit(-1)
        return parent, remaining
            
    def help_init(self):
        print
        print "Initialise a new jungle. This will return an error if run on an existing"
        print "jungle, or if there are no software versions present"
        print
        print "Usage:"
        print
        print "    jungle init [pathname]"
        
    def do_init(self, opts, args):
        parent, _ = self._parent(args)
        print "Initialising jungle in", parent
        j = Jungle(parent)
        j.initialise()
        
    def help_set(self):
        print 
        print "Set the specified version as the current version"
        print
        print "Usage:"
        print
        print "    jungle set [pathname] <version>"
        
    def do_set(self, opts, args):
        parent, r = self._parent(args, argc=2)
        j = Jungle(parent)
        version = r[0]
        j.set(version)
        
    def help_upgrade(self):
        print
        print "Set the current to the most recent version present (Head)"
        print 
        print "Usage:"
        print
        print "    jungle upgrade [pathname]"

    def do_upgrade(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        j.upgrade()
        
    def help_degrade(self):
        print
        print "Set the current to the second from most recent version present (Head-1) and print the version chosen."
        print
        print "Usage:"
        print
        print "    jungle degrade [--dry-run] [pathname]"

    def opts_degrade(self, p):
        p.add_option("--dry-run", default=False, action="store_true", help="don't make any changes")
        
    def do_degrade(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        j.degrade(dry_run=opts.dry_run)
        
    def help_current(self):
        print
        print "Print the current version"
        print
        print "Usage:"
        print
        print "    jungle current [pathname]"
    
    def do_current(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        print j.current_version()
        
    def help_status(self):
        print
        print "Print 'current' if current is at head or 'degraded' otherwise"
        print
        print "Usage:"
        print
        print "    jungle status [pathname]"
    
    def do_status(self, opts, args):
        parent, _ = self._parent(args)
        j = Jungle(parent)
        print j.status()
        
    def help_prune(self):
        print
        print "Delete old items from the symlink farm. ensure we don't delete what is"
        print "pointed to by current. It has 2 options, by age or by the number of iterations"
        print "(i.e. versions) to keep"
        print
        print "Usage:"
        print
        print "    jungle prune [--age N] [--iterations N] [pathname]"
        
    def opts_prune(self, p):
        p.add_option("--age", default=None, action="store", type="int", help="age in days to preserve")
        p.add_option("--iterations", default=None, action="store", type="int", help="iterations to preserve")
    
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
            
    def help_delete(self):
        print
        print "Delete the specified version. Will not delete the current version even if you ask it to."
        print
        print "Usage:"
        print
        print "    jungle delete <version>"
    
    def do_delete(self, opts, args):
        parent, r = self._parent(args, argc=2)
        j = Jungle(parent)
        version = r[0]
        j.delete(version)
    
    def do_help(self, opts, args):
        if len(args) == 0:
            print "Help!"
        elif len(args) == 1:
            helpfunc = getattr(self, "help_" + args[0], None)
            if helpfunc is not None:
                helpfunc()
            else:
                print "Command %s not known" % args[0]
                raise SystemExit(-1)
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
    import wingdbstub

    func, opts, args = parse_command(sys.argv[1:])
    try:
        func(opts, args)
    except OSError, e:
        print str(e)
        raise SystemExit(-1)