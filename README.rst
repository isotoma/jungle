======
jungle
======

Maintain a symlink farm for fast software rollbacks.

Terminology
===========

  Release Directory
    The directory containing the version directories.
    
  Parent
    The directory containing the release directory.
    
  Head
    The most recent version present in the parent.
    
  Head-1
    The penultimate version present in the parent.
    
  Current
    The version currently pointed to by the "current" symlink. This is the version that should be used. There must always be a current, and it must point to an existing directory, for this to be a valid jungle.
    
  Degrade
    To set the version to Head-1.
  
  Upgrade
    To set the version to Head.

Directory structure
===================

The directory structure jungle maintains looks like::

    parent/
        releases/1.0/
            1.1/
            2.0/
            2.2/
            3.0/
        current -> releases/3.0
    
You are expected to have other files in this parent directory, for example:
    
    parent/
        bin -> current/bin
        current -> releases/3.0
        eggs/
        releases/
        var/

Version numbers
===============

Version numbers MUST be compliant with the requirements of
`distutils.version.StrictVersion`, or they will not be accepted. The
following is from the distutils documentation.

Version numbering for meticulous retentive and software idealists.
Implements the standard interface for version number classes as
described above.  A version number consists of two or three
dot-separated numeric components, with an optional "pre-release" tag
on the end.  The pre-release tag consists of the letter 'a' or 'b'
followed by a number.  If the numeric components of two version
numbers are equal, then one with a pre-release tag will always
be deemed earlier (lesser) than one without.

The following are valid version numbers (shown in the order that
would be obtained by sorting according to the supplied cmp function)::

    0.4       0.4.0  (these two are equivalent)
    0.4.1
    0.5a1
    0.5b3
    0.5
    0.9.6
    1.0
    1.0.4a3
    1.0.4b1
    1.0.4

The following are examples of invalid version numbers::

    1
    2.7.2.2
    1.3.a4
    1.3pl1
    1.3c4

Usage
=====

Jungle is invoked with the form::

    jungle [-v] <command> [options] [<parent>]

    -v    verbose
    
If `parent` is omitted the current working directory is used.
    
Commands
========

init
----

Initialise a new jungle. This will return an error if run on an existing
jungle, or if there are no software versions present::

    jungle init [<pathname>]
    
set
---

Set the specified version as the current version::

    jungle set [<pathname>] <version>

upgrade
-------

Set the current to the most recent version present (Head)::

    jungle upgrade [<pathname>]
    
degrade
-------

Set the current to the second from most recent version present (Head-1) and print the version chosen.::

    jungle degrade [--dry-run] [<pathname>]

If the `dry-run` option is used then the degrade is not performed, but the
version that would be used is still printed.
    
current
-------

Print the current version::

    jungle current [<pathname>]

status
------

Print "current" if current is at head or "degraded" otherwise::

    jungle status [<pathname>]

prune
-----

Delete old items from the symlink farm. ensure we don't delete what is
pointed to by current. It has 2 options, by age or by the number of iterations
(i.e. versions) to keep::

    jungle prune [--age N days] [--iterations N] [<pathname>]

delete
------

Delete the specified version. Will not delete the current version::

    jungle delete [<pathname>] <version>
    
