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
}

_RC_PATHS = (
    "~/.config/jan-pona-mute/login",
    "~/.config/.jan-pona-mute",
    "~/.jan-pona-mute"
)

_PAGERS = (
    "mdcat",
    "fold",
    "cat"
)

# Init file finder
def get_rcfile():
    for rc_path in _RC_PATHS:
        rcfile = os.path.expanduser(rc_path)
        if os.path.exists(rcfile):
            return rcfile
    return None

# Pager finder
def get_pager():
    for cmd in _PAGERS:
        pager = shutil.which(cmd)
        if pager != None:
            return pager

class DiasporaClient(cmd.Cmd):

    prompt = "\x1b[38;5;255m" + "> " + "\x1b[0m"
    intro = "Welcome to Diaspora! Use the intro command for a quick introduction."

    header_format = "\x1b[1;38;5;255m" + "%s" + "\x1b[0m"

    username = None
    pod = None
    password = None
    pager = None

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

    def do_password(self, password):
        """Set the password."""
        self.password = (None if self.password == "" else password)
        print("Password %s" % ("unset" if self.password == "" else "set"))

    def do_save(self, line):
        """Save your login information to the init file."""
        if self.username == None or self.pod == None:
            print("Use the 'account' command to set username and pod")
        elif self.password == None:
            print("Use the 'password' command")
        else:
            rcfile = get_rcfile()
            if rcfile == None:
                rfile = first(_RC_PATHS)
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
            print("Use the 'account' command to set username and pod")
        elif self.password == None:
            print("Use the 'password' command")
        else:
            self.connection = diaspy.connection.Connection(
                pod = "https://%s" % self.pod, username = self.username, password = self.password)
            try:
                self.connection.login()
                self.onecmd("notifications")
            except diaspy.errors.LoginError:
                print("Login failed")

    def do_pager(self, pager):
        """Set the pager, e.g. to cat"""
        self.pager = pager
        print("Pager set: %s" % self.pager)

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
            print("The 'show' command takes a notification number")
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
            print("Retrieved post from the cache")
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
                print("The 'comments' command takes a number as its argument, or 'all'")
                print("The default is to show the last 5 comments")
                return

        if n != None:
            comments = comments[-n:]

        if comments:
            for n, comment in enumerate(comments):
                print()
                print(self.header("%2d. %s %s") % (n+1, comment.when(), comment.author()))
                print()
                self.show(comment)
        else:
            print("There are no comments on the selected post.")

    def do_comment(self, line):
        """Leave a comment on the current post."""
        if self.post == None:
            print("Use the 'show' command to show a post, first.")
            return
        comment = self.post.comment(line)
        self.post.comments.add(comment)
        self.undo.append("delete comment %s from %s" % (comment.id, self.id))
        print("Comment posted.")

    def do_delete(self, line):
        """Delete a comment."""
        words = line.strip().split()
        if words:
            if words[0] == "comment":
                if self.post == None:
                    print("Use the 'show' command to show a post, first.")
                    return
                if len(words) != 4:
                    print("Deleting a comment requires a comment id and a post id.")
                    print("delete comment <comment id> from <post id>")
                    return
                self.post_cache[words[3]].delete_comment(words[1])
                print("Comment deleted.")
            else:
                print("Deleting '%s' is not supported." % words[0])
                return
        else:
            print("Delete what?")

    def do_undo(self, line):
        """Undo an action."""
        if line != "":
            print("Undo does not take an argument.")
            return
        if not self.undo:
            print("There is nothing to undo.")
            return
        return self.onecmd(self.undo.pop())

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
        else:
            print("Use the 'save' command to save your login sequence to an init file")

    if not seen_pager:
        # prepend
        c.cmdqueue.insert(0, "pager %s" % get_pager())

    # Endless interpret loop
    while True:
        try:
            c.cmdloop()
        except KeyboardInterrupt:
            print("")

if __name__ == '__main__':
    main()
