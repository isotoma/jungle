======
jungle
======

Maintain a symlink farm for fast software rollbacks.

Directory structure
===================

The directory structure it maintains looks like::

    1.0
    2.0
    3.0
    current -> 1.0

Invocation
==========

invoke with:

jungle init [<pathname>] - set current to HEAD, error if current exists

jungle set [<pathname>] <version>

This sets up the symlinks as required by creating current.new and then moving it over the top of current.

jungle prune [--age N days] [--iterations 3] [--size 40M] [<pathname>]

delete old items from the symlink farm. ensure we don't delete what is pointed to by current.

jungle delete [<pathname>] <version> - delete the specified version

jungle latest [<pathname>] - set to HEAD, error if current does not exist

jungle rollback [<pathname>] - idempotent rollback to HEAD - 1

jungle current [<pathname>] - prints the latest version

jungle status [<pathname>] - print "current" or "degraded"

jungle rollback --dry-run <pathname> - prints the version number that would be rolled back to, or an error


Using with buildout
===================


buildouted stuff would look like:

/var/local/sites/<sitename>/var
/var/local/sites/<sitename>/eggs
/var/local/sites/<sitename>/1.0
/var/local/sites/<sitename>/1.0/bin
/var/local/sites/<sitename>/1.0/lib
/var/local/sites/<sitename>/current -> 1.0

