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
        print("""
Use the account and password commands to set up your connection, then
use the login command to log in. If everything works as intended, use
the save command to save these commands to an init file.

Once you've listed things such as notifications, enter a number to
select the corresponding item. Use the print command to see more.
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
        if self.username == None or self.pod == None:
            print("Use the account command to set username and pod")
        elif self.password == None:
            print("Use the password command")
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
            print("Use the account command to set username and pod")
        elif self.password == None:
            print("Use the password command")
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
        """List notifications."""
        if self.connection == None:
            print("Use the login command, first.")
            return
        self.notifications = diaspy.notifications.Notifications(self.connection).last()
        for n, notification in enumerate(self.notifications):
            print(self.header("%2d. %s %s") % (n+1, notification.when(), notification))
        print("Enter a number to select the notification.")

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

        try:
            n = int(line.strip())
            # Finally, see if it's a notification and show it
            self.do_show(n)
        except ValueError:
            print("Use the help command to show available commands")

    def do_show(self, n):
        """Show the post given by the index number.
The index number must refer to the current list of notifications."""
        try:
            notification = self.notifications[n-1]
            self.index = n
        except IndexError:
            print("Index too high!")
            return

        self.show(notification)

        print("Loading...")
        self.post = diaspy.models.Post(connection = self.connection, id = notification.about())

        print()
        self.show(self.post)

    def show(self, item):
        """Show the current item."""
        if self.pager:
            subprocess.run(self.pager, input = repr(item), text = True)
        else:
            print(repr(item))

    def do_comments(self, line):
        """Show the comments for the current post."""
        if self.post == None:
            print("Use the show command to show a post, first.")
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
                print("The comments command takes a number as its argument, or 'all'")
                print("The default is to show the last 5 comments")
                return

        if n != None:
            comments = comments[-n:]

        for n, comment in enumerate(comments):
            print()
            print(self.header("%2d. %s %s") % (n+1, comment.when(), comment.author()))
            print()
            self.show(comment)

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
            print("Use the save command to save your login sequence to an init file")

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
