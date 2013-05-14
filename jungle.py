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
            
    def exists(self, version):
        p = self.path(str(version))
        return os.path.isdir(p)
            
    def head(self):
        return max(self.versions())
     
    def path(self, path):
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
        self.set(self.head())
        
    def set(self, version):
        if not isinstance(version, StrictVersion):
            version = StrictVersion(version)
        if not self.exists(version):
            raise KeyError("Version %s does not exist" % version)
        if os.path.exists(self.path("current")):
            os.unlink(self.path("current"))
        os.symlink(str(version), self.path("current"))


class Cmd:
    
    def do_init(self, opts, args):
        if len(args) == 0:
            tld = os.getcwd()
        elif len(args) == 1:
            tld = args[0]
        else:
            print >>stderr, "Too many arguments to init"
            raise SystemExit(-1)
        if not os.path.isdir(tld):
            print >>stderr, "Jungle directory %r does not exist" % tld
            raise SystemExit(-1)
        print "Initialising jungle in", tld
        j = Jungle(tld)
        j.initialise()
    
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
    