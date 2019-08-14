#!/usr/bin/env python3
# Copyright (C) 2019  Alex Schroeder <alex@gnu.org>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>.

import diaspy
import subprocess
import argparse
import shutil
import cmd
import sys
import os

# Command abbreviations
_ABBREVS = {
    "q":    "quit",
    "p":    "print",
    "c":    "comments",
    "r":    "reload",
    "n":    "notifications",
    "e":    "edit",
}

_RC_PATHS = (
    "~/.config/jan-pona-mute/login",
    "~/.jan-pona-mute.d/login"
    "~/.jan-pona-mute"
)

_NOTE_DIRS = (
    "~/.config/jan-pona-mute/notes",
    "~/.jan-pona-mute.d/notes"
)

_PAGERS = (
    os.getenv("PAGER"),
    "mdcat",
    "fold",
    "cat"
)

_EDITORS = (
    os.getenv("EDITOR"),
    "vi",
    "ed"
)

def get_rcfile():
    """Init file finder"""
    for path in _RC_PATHS:
        path = os.path.expanduser(path)
        if os.path.exists(path):
            return path
    return None

def get_notes_dir():
    """Notes directory finder"""
    dir = None
    for path in _NOTE_DIRS:
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            dir = path
            break
    if dir == None:
        dir = os.path.expanduser(_NOTE_DIRS[0])
    if not os.path.isdir(dir):
        os.makedirs(dir)
    return dir

def get_binary(list):
    for cmd in list:
        if cmd != None:
            bin = shutil.which(cmd)
            if bin != None:
                return bin

def get_pager():
    """Pager finder"""
    return get_binary(_PAGERS)

def get_editor():
    """Editor finder"""
    return get_binary(_EDITORS)

class DiasporaClient(cmd.Cmd):

    prompt = "\x1b[38;5;255m" + "> " + "\x1b[0m"
    intro = "Welcome to Diaspora! Use the intro command for a quick introduction."

    header_format = "\x1b[1;38;5;255m" + "%s" + "\x1b[0m"

    username = None
    pod = None
    password = None
    pager = None
    editor = None

    connection = None
    notifications = []
    index = None
    post = None
    post_cache = {} # key is self.post.uid, and notification.id

    undo = []


    # dict mapping user ids to usernames
    users = {}

    def get_username(self, guid):
        if guid in self.users:
            return self.users[guid]
        else:
            user = diaspy.people.User(connection = self.connection, guid = guid)
            self.users[guid] = user.handle()
            return self.users[guid]

    def do_intro(self, line):
        """Start here."""
        print("""
Use the 'account' and 'password' commands to set up your connection,
then use the 'login' command to log in. If everything works as
intended, use the 'save' command to save these commands to an init
file.

Once you've listed things such as notifications, enter a number to
select the corresponding item.
""")

    def do_account(self, account):
        """Set username and pod using the format username@pod."""
        try:
            (self.username, self.pod) = account.split('@')
            print("Username and pod set: %s@%s" % (self.username, self.pod))
        except ValueError:
            print("The account must contain an @ character, e.g. kensanata@pluspora.com.")
            print("Use the account comand to set the account.")

    def do_info(self, line):
        """Get some info about things. By default, it is info about yourself."""
        print("Info about yourself:")
        print("Username: %s" % self.username)
        print("Password: %s" % ("None" if self.password == None else "set"))
        print("Pod:      %s" % self.pod)
        print("Pager:    %s" % self.pager)
        print("Editor:   %s" % self.editor)

    def do_password(self, password):
        """Set the password."""
        self.password = (None if self.password == "" else password)
        print("Password %s" % ("unset" if self.password == "" else "set"))

    def do_save(self, line):
        """Save your login information to the init file."""
        if self.username == None or self.pod == None:
            print("Use the 'account' command to set username and pod.")
        elif self.password == None:
            print("Use the 'password' command.")
        else:
            rcfile = get_rcfile()
            if rcfile == None:
                rfile = _RC_PATHS[0]
            seen_account = False
            seen_password = False
            seen_login = False
            changed = False
            file = []
            with open(rcfile, "r") as fp:
                for line in fp:
                    words = line.strip().split()
                    if words:
                        if words[0] == "account":
                            seen_account = True
                            account = "%s@%s" % (self.username, self.pod)
                            if len(words) > 1 and words[1] != account:
                                line = "account %s\n" % account
                                changed = True
                        elif words[0] == "password":
                            seen_password = True
                            if len(words) > 1 and words[1] != self.password:
                                line = "password %s\n" % self.password
                                changed = True
                        elif words[0] == "login":
                            if seen_account and seen_password:
                                seen_login = True
                            else:
                                # skip login if no account or no password given
                                line = None
                                changed = True
                    if line != None:
                        file.append(line)
                if not seen_account:
                    file.append("account %s@%s\n" % (self.username, self.pod))
                    changed = True
                if not seen_password:
                    file.append("password %s\n" % self.password)
                    changed = True
                if not seen_login:
                    file.append("login\n")
                    changed = True
            if changed:
                if os.path.isfile(rcfile):
                    os.rename(rcfile, rcfile + "~")
                if not os.path.isdir(os.path.dirname(rcfile)):
                    os.makedirs(os.path.dirname(rcfile))
                with open(rcfile, "w") as fp:
                    fp.write("".join(file))
                print("Wrote %s" % rcfile)
            else:
                print("No changes made, %s left unchanged" % rcfile)

    def do_login(self, line):
        """Login."""
        if line != "":
            self.onecmd("account %s" % line)
        if self.username == None or self.pod == None:
            print("Use the 'account' command to set username and pod.")
        elif self.password == None:
            print("Use the 'password' command.")
        else:
            self.connection = diaspy.connection.Connection(
                pod = "https://%s" % self.pod, username = self.username, password = self.password)
            try:
                self.connection.login()
                self.onecmd("notifications")
            except diaspy.errors.LoginError:
                print("Login failed.")

    def do_pager(self, pager):
        """Set the pager, e.g. to cat"""
        self.pager = pager
        print("Pager set: %s" % self.pager)

    def do_editor(self, editor):
        """Set the editor, e.g. to ed"""
        self.editor = editor
        print("Editor set: %s" % self.editor)

    def header(self, line):
        """Wrap line in header format."""
        return self.header_format % line

    def do_notifications(self, line):
        """List notifications. Use 'notifications reload' to reload them."""
        if line == "" and self.notifications:
            print("Redisplaying the notifications in the cache.")
            print("Use the 'reload' argument to reload them.")
        elif line == "reload" or not self.notifications:
            if self.connection == None:
                print("Use the 'login' command, first.")
                return
            self.notifications = diaspy.notifications.Notifications(self.connection).last()
        else:
            print("The 'notifications' command only takes the optional argument 'reload'.")
            return
        if self.notifications:
            for n, notification in enumerate(self.notifications):
                print(self.header("%2d. %s %s") % (n+1, notification.when(), notification))
            print("Enter a number to select the notification.")
        else:
            print("There are no notifications. 😢")

    ### The end!
    def do_quit(self, *args):
        """Exit jan-pona-mute."""
        print("Be safe!")
        sys.exit()

    def default(self, line):
        if line.strip() == "EOF":
            return self.onecmd("quit")

        # Expand abbreviated commands
        first_word = line.split()[0].strip()
        if first_word in _ABBREVS:
            full_cmd = _ABBREVS[first_word]
            expanded = line.replace(first_word, full_cmd, 1)
            return self.onecmd(expanded)

        # Finally, see if it's a notification and show it
        self.do_show(line)

    def do_show(self, line):
        """Show the post given by the index number.
The index number must refer to the current list of notifications."""
        if not self.notifications:
            print("No notifications were loaded.")
            return
        if line == "":
            print("The 'show' command takes a notification number.")
            return
        try:
            n = int(line.strip())
            notification = self.notifications[n-1]
            self.index = n
        except ValueError:
            print("The 'show' command takes a notification number but '%s' is not a number" % line)
            return
        except IndexError:
            print("Index too high!")
            return

        self.show(notification)
        self.load(notification.about())

        print()
        self.show(self.post)

        if(self.post.comments):
            print()
            if len(self.post.comments) == 1:
                print("There is 1 comment.")
            else:
                print("There are %d comments." % len(self.post.comments))
            print("Use the 'comments' command to list the latest comments.")

    def load(self, id):
        """Load the post belonging to the id (from a notification),
or get it from the cache."""
        if id in self.post_cache:
            self.post = self.post_cache[id]
            print("Retrieved post from the cache.")
        else:
            print("Loading...")
            self.post = diaspy.models.Post(connection = self.connection, id = id)
            self.post_cache[id] = self.post
        return self.post

    def do_reload(self, line):
        """Reload the current post."""
        if self.post == None:
            print("Use the 'show' command to show a post, first.")
            return
        print("Reloading...")
        self.post = diaspy.models.Post(connection = self.connection, id = self.post.id)
        self.post_cache[id] = self.post

    def show(self, item):
        """Show the current item."""
        if self.pager:
            subprocess.run(self.pager, input = str(item), text = True)
        else:
            print(str(item))

    def do_comments(self, line):
        """Show the comments for the current post.
Use the 'all' argument to show them all. Use a numerical argument to
show that many. The default is to load the last five."""
        if self.post == None:
            print("Use the 'show' command to show a post, first.")
            return
        if self.post.comments == None:
            print("The current post has no comments.")
            return

        n = 5
        comments = self.post.comments

        if line == "all":
            n = None
        elif line != "":
            try:
                n = int(line.strip())
            except ValueError:
                print("The 'comments' command takes a number as its argument, or 'all'.")
                print("The default is to show the last 5 comments.")
                return

        if n == None:
            start = 0
        else:
            # n is from the back
            start = max(len(comments) - n, 0)

        if comments:
            for n, comment in enumerate(comments[start:], start):
                print()
                print(self.header("%2d. %s %s") % (n+1, comment.when(), comment.author()))
                print()
                self.show(comment)
        else:
            print("There are no comments on the selected post.")

    def do_comment(self, line):
        """Leave a comment on the current post.
If you just use a number as your comment, it will refer to a note.
Use the 'edit' command to edit notes."""
        if self.post == None:
            print("Use the 'show' command to show a post, first.")
            return
        try:
            # if the comment is just a number, use a note to post
            n = int(line.strip())
            notes = self.get_notes()
            if notes:
                try:
                    line = self.read_note(notes[n-1])
                    print("Using note #%d: %s" % (n, notes[n-1]))
                except IndexError:
                    print("Use the 'list notes' command to list valid numbers.")
                    return
            else:
                print("There are no notes to use.")
                return
        except ValueError:
            # in which case we'll simply comment with the line
            pass
        comment = self.post.comment(line)
        self.post.comments.add(comment)
        self.undo.append("delete comment %s from %s" % (comment.id, self.post.id))
        print("Comment posted.")

    def do_delete(self, line):
        """Delete a comment."""
        words = line.strip().split()
        if words:
            if words[0] == "comment":
                if len(words) == 4:
                    post = self.post_cache[words[3]]
                    post.delete_comment(words[1])
                    comments = [c.id for c in post.comments if c.id != id]
                    post.comments = diaspy.models.Comments(comments)
                    print("Comment deleted.")
                    return
                if self.post == None:
                    print("Use the 'show' command to show a post, first.")
                    return
                if len(words) == 2:
                    try:
                        n = int(words[1])
                        comment = self.post.comments[n-1]
                        id = comment.id
                    except ValueError:
                        print("Deleting a comment requires an integer.")
                        return
                    except IndexError:
                        print("Use the 'comments' command to find valid comment numbers.")
                        return
                    # not catching any errors from diaspy
                    self.post.delete_comment(id)
                    # there is no self.post.comments.remove(id)
                    comments = [c.id for c in self.post.comments if c.id != id]
                    self.post.comments = diaspy.models.Comments(comments)
                    print("Comment deleted.")
                    return
                else:
                    print("Deleting a comment requires a comment id and a post id, or a number.")
                    print("delete comment <comment id> from <post id>")
                    print("delete comment 5")
                    return
            if words[0] == "note":
                if len(words) != 2:
                    print("Deleting a note requires a number.")
                    return
                try:
                    n = int(words[1])
                except ValueError:
                    print("Deleting a note requires an integer.")
                    return
                notes = self.get_notes()
                if notes:
                    try:
                        os.unlink(self.get_note_path(notes[n-1]))
                        print("Deleted note #%d: %s" % (n, notes[n-1]))
                    except IndexError:
                        print("Use the 'list notes' command to list valid numbers.")
                else:
                    print("There are no notes to delete.")
            else:
                print("Things to delete: comment, note.")
                return
        else:
            print("Delete what?")

    def do_undo(self, line):
        """Undo an action."""
        if line != "":
            print("The 'undo' command does not take an argument.")
            return
        if not self.undo:
            print("There is nothing to undo.")
            return
        return self.onecmd(self.undo.pop())

    def do_edit(self, line):
        """Edit a note with a given name."""
        if line == "":
            print("Edit takes the name of a note as an argument.")
            return
        file = self.get_note_path(line)
        if self.editor:
            subprocess.run([self.editor, file])
            self.onecmd("notes")
        else:
            print("Use the 'editor' command to set an editor.")

    def do_notes(self, line):
        """List notes"""
        if line != "":
            print("The 'notes' command does not take an argument.")
            return
        notes = self.get_notes()
        if notes:
            for n, note in enumerate(notes):
                print(self.header("%2d. %s") % (n+1, note))
            else:
                print("Use 'edit' to create a note.")
        else:
            print("Things to list: notes.")

    def get_notes(self):
        """Get the list of notes."""
        return os.listdir(get_notes_dir())

    def get_note_path(self, filename):
        """Get the correct path for a note."""
        return os.path.join(get_notes_dir(), filename)

    def read_note(self, filename):
        """Get text of a note."""
        with open(self.get_note_path(filename), mode = 'r', encoding = 'utf-8') as fp:
            return fp.read()

# Main function
def main():

    # Parse args
    parser = argparse.ArgumentParser(description='A command line Diaspora client.')
    parser.add_argument('--no-init-file', dest='init_file', action='store_const',
                        const=False, default=True, help='Do not load a init file')
    args = parser.parse_args()

    # Instantiate client
    c = DiasporaClient()

    # Process init file
    seen_pager = False
    seen_editor = False
    if args.init_file:
        rcfile = get_rcfile()
        if rcfile:
            print("Using init file %s" % rcfile)
            with open(rcfile, "r") as fp:
                for line in fp:
                    line = line.strip()
                    if line != "":
                        c.cmdqueue.append(line)
                    if not seen_pager:
                        seen_pager = line.startswith("pager ");
                    if not seen_editor:
                        seen_editor = line.startswith("editor ");
        else:
            print("Use the 'save' command to save your login sequence to an init file.")

    if not seen_pager:
        # prepend
        c.cmdqueue.insert(0, "pager %s" % get_pager())
    if not seen_editor:
        # prepend
        c.cmdqueue.insert(0, "editor %s" % get_editor())

    # Endless interpret loop
    while True:
        try:
            c.cmdloop()
        except KeyboardInterrupt:
            print("")

if __name__ == '__main__':
    main()
