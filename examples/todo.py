# Todo list based on bitdb

# in ~/.bitdb_todo a bunch of things are stored:

# username:api_key
# latest_revision
# latest_revision^1
# latest_revision^2
# latest_revision^N

# Essentially, in each of these revisions:

#  {'tag': 'todo-snapshot',
#   'parent': 'key',
#   'items': ['key1', 'key2', 'key3', 'keyN']}

# Each item is stored as:
  
#  {'tag': 'todo-item',
#   'text': 'go to the store'}

# When marking an item as "done," it's simply a matter of
# removing it from the index and creating a new index ('revision') 

# Locally, in ~/.bitdb_todo_cache/ we store all the objects
# to avoid hitting bit.ly too too often, but if we refer to
# them and they don't exist, we refresh.

# Objects, are always a one time store.

# Essentially, we should be able to recreate the entire database
# from the latest revision since we always store a revision's parent, though
# this app does not expose that, and therefore I don't know if it actually 
# works. :)

from __future__ import with_statement
from contextlib import closing

import os
import sys
import bitdb

LOG_FILE = os.path.expanduser('~/.bitdb_todo')


class TodoList(object):
    
    def __init__(self, log):
        if log.startswith('~'):
            self._log = os.path.expanduser(log)
        else:
            self._log = log
        self._revisions = []
        self._current_items = []
        self._current_revision = 'ROOT'
        self._api_user = None
        self._api_key = None

        self._init_log()

        self._database = bitdb.BitlyDB(self._api_user, self._api_key)

        self._init_items()

    def _init_items(self):
        if self._current_revision != 'ROOT':
            items = self._load_list(self._current_revision)
            self._current_items = [k for k, _ in items]

    def _init_log(self):
        """Reads the log to determine revision history etc.
        """
        try:
            lines = []
            with closing(open(self._log)) as f:
                lines = f.readlines()

            if len(lines) >= 1:
                self._api_user, self._api_key = [b.strip() for b in 
                                                 lines[0].split(':', 2)]
            self._revisions = [line.strip() for line in lines[1:]]
            if len(self._revisions):
                self._current_revision = self._revisions[0]
            else:
                self._current_revision = 'ROOT'
        except Exception, e:
            print e, 'WTF'
            pass

    def _write_log(self):
        with closing(open(self._log, 'w')) as f:
            f.write('%s:%s\n' % (self._api_user, self._api_key))
            f.writelines(rev + '\n' for rev in self._revisions)

    def _load_list(self, rev):
        revision = self._database.get(rev)
        if not revision:
            print sys>>stderr, "Unknown revision requested."
            return None

        theitems = self._database.getmulti(revision['items'])
        if theitems:
            return [(k, theitems[k]) for k in revision['items']]

    def _new_revision(self, parent=None):
        """Returns the revision id
        """
        data = {'tag': 'todo-snapshot',
                'parent': parent or self._current_revision,
                'items': self._current_items}
        rev = self._database.put(data)
        if rev:
            self._revisions.insert(0, rev)
            self._write_log()
        return rev

    def add(self, item):
        """Returns the HEAD revision after putting item in the database
        """
        data = {'tag': 'todo-item',
                'text': item}
        key = self._database.put(data)
        if not key:
            return None

        self._current_items.append(key)
        return self._new_revision()
        
    def list(self, rev=None):
        """List the items in the todo list
        """
        if not rev:
            rev = self._current_revision

        return self._load_list(rev)

    def log(self):
        """Returns the list of revisions"""
        return self._revisions

    def done(self, key):
        """Returns a new revision after removing an item
        """
        try:
            self._current_items.remove(key)
            return self._new_revision()
        except:
            return None

def help():
    print """todo.py - a simple cloud based todo list

usage: todo.py [command] <arg>

Commands:
   add "text"          Add text as a todo
   list <rev>          List the current todos at revision (optional arg)
   done [item]         Mark item as done
   log                 Get a list of all the revisions
   config [user] [key] Get a list of all the revisions
   help                This message
"""

def done(tl, key):
    rev = tl.done(key)
    if rev:
        print "Marked %s as done.\n" % key
        list_(tl, rev)
    else:
        print >>sys.stderr, "ERROR: Couldn't mark %s as done." % key

def add(tl, text):
    rev = tl.add(text)
    if rev:
        print "'%s' added to the list.\n" % key
        list_(tl, rev)
    else:
        print >>sys.stderr, "ERROR: Couldn't add '%s' to the list." % text

def log(tl):
    revs = tl.log()
    if revs:
        for rev in revs:
            print rev
    else:
        print >>sys.stderr, "No revisions"

def list_(tl, rev):
    items = tl.list(rev)
    if items:
        for key, item in items:
            print "%-10s - %s" % (key, item['text'])
    else:
        print >>sys.stderr, "ERROR: Couldn't obtain the list for rev '%s'."\
            % rev

def config(tl, user, key):
    tl._api_user = user
    tl._api_key = key
    tl._write_log()

def main(argv):
    if len(argv) == 1 or not argv[1] in ('add', 'list', 'log', 
                                         'done', 'config'):
        help()
        sys.exit(1)

    length = len(argv)

    tl = TodoList(LOG_FILE)
    if argv[1] == 'add' and length == 3:
        tl.add(argv[2])
    elif argv[1] == 'list':
        list_(tl, None if length == 2 else argv[2])
    elif argv[1] == 'log':
        log(tl)
    elif argv[1] == 'done' and length == 3:
        done(tl, argv[2])
    elif argv[1] == 'config' and length == 4:
        config(tl, argv[2], argv[3])

if __name__ == '__main__':
    main(sys.argv)
