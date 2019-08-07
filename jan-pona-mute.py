#!/usr/bin/env perl
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
import argparse
import cmd
import sys
import os

# Command abbreviations
_ABBREVS = {
    "q":    "quit",
}

# Config file finder
def get_rcfile():
    rc_paths = ("~/.config/jan-pona-mute/login", "~/.config/.jan-pona-mute", "~/.jan-pona-mute")
    for rc_path in rc_paths:
        rcfile = os.path.expanduser(rc_path)
        if os.path.exists(rcfile):
            return rcfile
    return None

class DiasporaClient(cmd.Cmd):

    prompt = "\x1b[38;5;255m" + "> " + "\x1b[0m"
    intro = "Welcome to Diaspora!"

    username = None
    pod = None
    password = None

    connection = None
    notifications = None

    # dict mapping user ids to usernames
    users = {}

    def get_username(self, guid):
        if guid in self.users:
            return self.users[guid]
        else:
            user = diaspy.people.User(connection = self.connection, guid = guid)
            self.users[guid] = user.handle()
            return self.users[guid]

    def __init__(self, account):
        cmd.Cmd.__init__(self)
        self.onecmd("account " + account)

    def do_account(self, account):
        """Set username and pod using the format username@pod."""
        try:
            (self.username, self.pod) = account.split('@')
        except ValueError:
            print("The account must contain an @ character, e.g. kensanata@pluspora.com.")
            print("Use the account comand to set the account.")

    def do_info(self, line):
        """Get some info about things. By default, it is info about yourself."""
        print("Info about yourself:")
        print("Username: " + self.username)
        print("Password: " + ("unset" if self.password == None else "set"))
        print("Pod:      " + self.pod)

    def do_password(self, password):
        """Set the password."""
        self.password = (None if self.password == "" else password)
        print("Password " + ("unset" if self.password == "" else "set"))

    def do_login(self, line):
        """Login."""
        if line != "":
            self.onecmd("account " + line)
        if self.password == "":
            print("Use the password command to set a password for " + self.username)
            return
        self.connection = diaspy.connection.Connection(
            pod = "https://" + self.pod, username = self.username, password = self.password)
        self.connection.login()
        self.onecmd("notifications")

    def do_notifications(self, line):
        """Show notifications."""
        if self.connection == None:
            print("Use the login command, first.")
            return
        self.notifications = diaspy.notifications.Notifications(self.connection).last()
        for n, notification in enumerate(self.notifications):
            print("%2d. %s %s" % (n+1, notification.when(), notification))

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

# Main function
def main():

    # Parse args
    parser = argparse.ArgumentParser(description='A command line Diaspora client.')
    parser.add_argument('account',
                        help='your account, e.g. kensanata@pluspora.com')
    args = parser.parse_args()

    # Instantiate client
    c = DiasporaClient(args.account)

    # Process config file
    rcfile = get_rcfile()
    if rcfile:
        print("Using config %s" % rcfile)
        with open(rcfile, "r") as fp:
            for line in fp:
                line = line.strip()
                c.cmdqueue.append(line)

    # Endless interpret loop
    while True:
        try:
            c.cmdloop()
        except KeyboardInterrupt:
            print("")

if __name__ == '__main__':
    main()
