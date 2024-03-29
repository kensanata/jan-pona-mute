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
import re

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

shortcuts = {
    "q":    "quit",
    "p":    "preview",
    "prev": "previous",
    "c":    "comments",
    "r":    "reload",
    "n":    "notifications",
    "m":    "notifications more",
    "g":    "notifications update",
    "e":    "edit",
    "d":    "delete",
}

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
    home = None
    numbers_refer_to = None
    last_number = None
    post = None
    post_cache = {} # key is self.post.uid, and notification.id
    last_comments = None

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

Once you've listed things such as notifications or the home stream,
enter a number to select the corresponding item.
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
        print(self.header("Info"))
        print("Username: %s" % self.username)
        print("Password: %s" % ("None" if self.password == None else "set"))
        print("Pod:      %s" % self.pod)
        print("Pager:    %s" % self.pager)
        print("Editor:   %s" % self.editor)
        print("Cache:    %s posts" % len(self.post_cache))

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
            print("Setting up a connection...")
            self.connection = diaspy.connection.Connection(
                pod = "https://%s" % self.pod, username = self.username, password = self.password)
            try:
                print("Logging in...")
                self.connection.login()
            except diaspy.errors.LoginError:
                print("Login failed.")

    def do_pager(self, pager):
        """Set the pager, e.g. to 'fold -w 72'.
The command line can contain options and arguments."""
        self.pager = pager
        print("Pager set: %s" % self.pager)

    def do_editor(self, editor):
        """Set the editor, e.g. to ed.
The command line can contain options and arguments.
The filename is appended at the end."""
        self.editor = editor
        print("Editor set: %s" % self.editor)

    def header(self, line):
        """Wrap line in header format."""
        return self.header_format % line

    def do_notifications(self, line):
        """List notifications.
Use 'notifications update' to fetch the latest five.
Use 'notifications more' to fetch five more."""
        if not self.notifications:
            if self.connection == None:
                print("Use the 'login' command, first.")
                return
            self.notifications = diaspy.notifications.Notifications(self.connection)
        if line == "":
            print("Redisplaying the notifications in the cache.")
            print("Use 'notifications update' to load new ones.")
        elif line == "update":
            self.notifications.update()
        elif line == "more":
            self.notifications.more()
        else:
            print("The 'notifications' command only takes one of the following argument:")
            print("- 'reload' fetches the last five notifications")
            print("- 'more' fetches five earlier notifications")
            return
        # print notifications
        if len(self.notifications) > 0:
            for n, notification in enumerate(self.notifications):
                if notification.unread:
                    print(self.header("%2d. %s %s") % (n+1, notification.when(), notification))
                else:
                    print("%2d. %s %s" % (n+1, notification.when(), notification))
            print("Enter a number to select the notification.")
            self.numbers_refer_to = 'notifications'
        else:
            print("There are no notifications. 😢")

    def do_quit(self, *args):
        """Exit jan-pona-mute."""
        print("Be safe!")
        sys.exit()

    def emptyline(self):
        """Go to the next notification or post."""
        return self.onecmd("next")

    def do_previous(self, line):
        """Go to the previous notification or post."""
        if self.last_number and self.last_number > 1:
            print("Previous...")
            return self.onecmd("show %d" % (self.last_number - 1))

    def do_next(self, line):
        """Go to the next notification or post."""
        if self.last_number:
            print("Next...")
            return self.onecmd("show %d" % (self.last_number + 1))

    def default(self, line):
        if line.strip() == "EOF":
            return self.onecmd("quit")

        # Expand abbreviated commands
        first_word = line.split()[0].strip()
        if first_word in shortcuts:
            full_cmd = shortcuts[first_word]
            expanded = line.replace(first_word, full_cmd, 1)
            return self.onecmd(expanded)

        # Finally, see if it's a notification and it
        self.do_show(line)

    def do_show(self, line):
        """Show the post given by the index number.
The index number must refer to the current list of notifications
or the home stream. If no index number is given, show the current
post again."""
        if not self.notifications and not self.home:
            print("Use the 'notifications' command to load notifications.")
            return
        if line == "" and self.post == None:
            print("Please specify a number.")
            return
        n = 0
        if line != "":
            try:
                n = int(line.strip())
                if self.numbers_refer_to == 'notifications':
                    notification = self.notifications[n-1]
                    self.last_number = n; # doesn't matter if we can't load it later
                    self.show(notification)
                    if not self.load(str(notification.about())): # elsewhere, id is a string
                        return
                elif self.numbers_refer_to == 'home':
                    posts = sorted(self.home, key=lambda x: x.data()["created_at"])
                    self.post = posts[n-1]
                    self.last_number = n;
                else:
                    print("Internal error: not sure what numbers '%s' refer to." % self.numbers_refer_to)
                    return
            except ValueError:
                print("The 'show' command takes a notification number but '%s' is not a number" % line)
                return
            except IndexError:
                print("Index too high!")
                return

        print()
        if n:
            print(self.header("%2d. %s %s") % (n, self.post.data()["created_at"], self.post.author()))
        else:
            print(self.header("%s %s") % (self.post.data()["created_at"], self.post.author()))
        print()
        self.show(self.post)
        print()

        if(self.post.comments):
            print("%d comment%s" % (len(self.post.comments), "s" if len(self.post.comments) != 1 else ""))
            print("Use the 'comments' command to list the latest comments.")
        print("Use the 'comment' command to leave a comment.")

    def load(self, id):
        """Load the post belonging to the id (from a notification),
or get it from the cache."""
        if id in self.post_cache:
            self.post = self.post_cache[id]
            print("Retrieved post from the cache.")
        else:
            print("Loading...")
            try:
                self.post = diaspy.models.Post(connection = self.connection, id = id)
                self.post_cache[id] = self.post
            except diaspy.errors.PostError as e:
                print("Cannot load this post: %s" % e)
                return None
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
            try:
                subprocess.run(self.pager.split(), input = str(item), text = True)
            except FileNotFoundError:
                print("Could not execute '%s'. Use the 'pager' command to change the pager." % self.pager)
        else:
            print(str(item))

    def do_comments(self, line):
        """Show the comments for the current post.
Use the 'all' argument to show them all. Use a numerical argument to
show that many, e.g. '5' (this is the default). Use a range to show
those comments, e.g. '1-5'. Use 'previous' to show comments further
up, use 'next' to show comments further down."""
        if self.post == None:
            print("Use the 'show' command to show a post, first.")
            return
        if self.post.comments == None:
            print("The current post has no comments.")
            return

        n = 5
        comments = self.post.comments
        end = len(comments)
        start = end - n

        if re.fullmatch('\d+', line):
            start = end - int(line)
        elif re.fullmatch('\d+-\d+', line):
            (start, end) = [int(s)-1 for s in line.split('-')]
            end += 1
        elif line == "all":
            start = 0
        elif line == "previous":
            if self.last_comments != None:
                n = self.last_comments[1] - self.last_comments[0]
                (start, end) = [x - n for x in self.last_comments]
        elif line == "next":
            if self.last_comments != None:
                n = self.last_comments[1] - self.last_comments[0]
                (start, end) = [x + n for x in self.last_comments]
        elif line != "":
            print("The 'comments' command takes the following arguments (the default is '5'):")
            print("- a number, shows this many comments, counting from the end, e.g. 10")
            print("- a range, shows these comments, counting from the start, e.g. 1-5")
            print("- 'all' shows all the comments")
            return

        # set window if reasonable
        if end > 0 and start < len(comments):
            self.last_comments = [start, end]

        # sanity check to avoid index errors
        start = max(start, 0)
        start = min(start, len(comments))
        end = max(end, start)
        end = min(end, len(comments))

        if comments:
            for n, comment in enumerate(comments[start:end], start):
                print()
                print(self.header("%2d. %s %s") % (n+1, comment.when(), comment.author()))
                print()
                self.show(comment)
            print()
        else:
            print("There are no comments on the selected post.")
        print("Use the 'comment' command to post a comment.")

    def complete_comments(self, text, line, begidx, endidx):
        """Complete comments"""
        match = re.fullmatch("comments (\d+)-\d*", line)
        if (match):
            start = int(match.group(1))
            completions = [str(n + 1) for n in range(len(self.post.comments)) if n >= start]
            return [s for s in completions if s.startswith(text)]
        completions = ["all", "next", "previous"]
        completions.extend([str(n + 1) for n in range(len(self.post.comments))])
        return [s for s in completions if s.startswith(text)]

    def do_comment(self, line):
        """Leave a comment on the current post.
If you just use a number as your comment, it will refer to a note.
Use the 'edit' command to edit notes."""
        if self.post == None:
            print("Use the 'show' command to show a post, first.")
            return
        notes = self.get_notes()
        if line in notes:
            print("Using note '%s'" % line)
            line = self.read_note(line)
        comment = self.post.comment(line)
        self.post.comments.add(comment)
        self.undo.append("delete comment %s from %s" % (comment.id, self.post.id))
        print("Comment posted.")

    def complete_comment(self, text, line, begidx, endidx):
        """Complete on filenames of notes"""
        notes = self.get_notes()
        return [note for note in notes if note.startswith(text)]

    def do_post(self, line):
        """Write a post on the current stream.
If you just use a number as your post, it will refer to a note.
Use the 'edit' command to edit notes."""
        if line == "":
            print("Post what?")
            return
        if self.home == None:
            print("Loading...")
            self.home = diaspy.streams.Stream(self.connection)
        notes = self.get_notes()
        if line in notes:
            print("Using note '%s'" % line)
            line = self.read_note(line)
        self.post = self.home.post(text = line)
        self.post_cache[self.post.id] = self.post
        self.undo.append("delete post %s" % self.post.id)
        print("Posted. Use the 'show' command to show it. Use the 'undo' command to undo this.")

    def do_delete(self, line):
        """Delete a comment."""
        words = line.strip().split(maxsplit = 1)
        if words:
            if words[0] == "post":
                if len(words) > 1:
                    print("Deleting a post takes no argument. It always deletes the selected post.")
                    return
                if not self.post:
                    print("Use the 'show' command to select a post.")
                    return
                if self.home and self.post in self.home:
                    self.home._stream.remove(self.post)
                if self.post.id in self.post_cache:
                    self.post_cache.pop(self.post.id)
                self.post.delete()
                print("Post deleted.")
                return
            if words[0] == "comment":
                words = line.strip().split()
                if len(words) == 4:
                    post = self.post_cache[words[3]]
                    post.delete_comment(words[1])
                    comments = [c.id for c in post.comments if c.id != words[1]]
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
                if len(words) == 1:
                    print("Deleting which note?")
                    return
                notes = self.get_notes()
                if words[1] in notes:
                    os.unlink(self.get_note_path(words[1]))
                    print("Deleted note '%s'." % words[1])
                else:
                    print("There is no such note.")
            else:
                print("Things to delete: post, comment, note.")
                return
        else:
            print("Delete what?")

    def complete_delete(self, text, line, begidx, endidx):
        """Complete on actions and names of notes"""
        if begidx == len("delete "):
            return [cmd for cmd in ["post", "comment ", "note "] if cmd.startswith(text)]
        if begidx == len("delete note "):
            notes = self.get_notes()
            return [note for note in notes if note.startswith(text)]
        if begidx == len("delete comment "):
            numbers = [str(n + 1) for n in range(len(self.post.comments))]
            return [s for s in numbers if s.startswith(text)]

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
            command = self.editor.split()
            command.append(file)
            try:
                subprocess.run(command)
                self.onecmd("notes")
            except FileNotFoundError:
                print("Could not execute '%s'. Use the 'editor' command to change the editor." % self.editor)
        else:
            print("Use the 'editor' command to set an editor.")

    def complete_edit(self, text, line, begidx, endidx):
        """Complete on filenames of notes"""
        notes = self.get_notes()
        return [note for note in notes if note.startswith(text)]

    def do_notes(self, line):
        """List notes"""
        if line != "":
            print("The 'notes' command does not take an argument.")
            return
        notes = self.get_notes()
        if notes:
            for note in notes:
                print(self.header(note))
            print("Use the 'edit' command to edit a note.")
            print("Use the 'preview' command to look at a note.")
            print("Use the 'post' command to post a note.")
            print("Use the 'comment' command to post a comment.")
        else:
            print("Use 'edit' to create a note.")

    def get_notes(self):
        """Get the list of notes."""
        return sorted([dir for dir in os.listdir(get_notes_dir()) if not dir.endswith("~")])

    def get_note_path(self, filename):
        """Get the correct path for a note."""
        return os.path.join(get_notes_dir(), filename)

    def read_note(self, filename):
        """Get text of a note."""
        with open(self.get_note_path(filename), mode = 'r', encoding = 'utf-8') as fp:
            return fp.read()

    def do_preview(self, line):
        """Preview a note using your pager.
Use the 'pager' command to set your pager to something like 'mdcat'."""
        if line == "":
            print("The 'preview' command takes a note as an argument.")
            print("Use the 'notes' command to list all your notes.")
            return
        notes = self.get_notes()
        if line in notes:
            self.show(self.read_note(line))
        else:
            print("There is no such note.")

    def complete_preview(self, text, line, begidx, endidx):
        """Complete on filenames of notes"""
        return(self.complete_edit(text, line, begidx, endidx))

    def do_home(self, line):
        """Show the main stream containing the combined posts of the
followed users and tags and the community spotlights posts if
the user enabled those."""
        if line == "":
            if self.home:
                print("Redisplaying the cached statuses of the home stream.")
                print("Use the 'reload' argument to reload them.")
                print("Use the 'all' argument to show them all.")
                print("Use a number to show only that many.")
                print("The default is 5.")
            else:
                print("Loading...")
                self.home = diaspy.streams.Stream(self.connection)
                self.home.fill()
                for post in self.home:
                    if post.id not in self.post_cache:
                        self.post_cache[post.id] = post
        elif line == "reload":
            if self.connection == None:
                print("Use the 'login' command, first.")
                return
            if self.home:
                print("Reloading...")
                self.home.update()
                line = ""
            else:
                self.home = diaspy.streams.Stream(self.connection)
                self.home.fill()

        n = 5
        posts = sorted(self.home, key=lambda x: x.data()["created_at"])

        if line == "all":
            n = None
        elif line != "":
            try:
                n = int(line.strip())
            except ValueError:
                print("The 'home' command takes a number as its argument, or 'reload' or 'all'.")
                print("The default is to show the last 5 posts.")
                return

        if n == None:
            start = 0
        else:
            # n is from the back
            start = max(len(posts) - n, 0)

        if posts:
            for n, post in enumerate(posts[start:], start):
                print()
                print(self.header("%2d. %s %s") % (n+1, post.data()["created_at"], post.author()))
                print()
                self.show(post)
                print()
                print("%d comment%s" % (len(post.comments), "s" if len(post.comments) != 1 else ""))

            print()
            print("Enter a number to select the post.")
            self.numbers_refer_to = 'home'
        else:
            print("The people you follow have nothing to say.")
            print("The tags you follow are empty. 😢")

    def do_shortcuts(self, line):
        """List all shortcuts."""
        if line != "":
            print("The 'shortcuts' command does not take an argument.")
            return
        print(self.header("Shortcuts"))
        for shortcut in sorted(shortcuts):
            print("%s\t%s" % (shortcut, shortcuts[shortcut]))
        print("Use the 'shortcut' command to change or add shortcuts.")

    def do_shortcut(self, line):
        """Define a new shortcut."""
        words = line.strip().split(maxsplit = 1)
        if len(words) == 0:
            return self.onecmd("shortcuts")
        elif len(words) == 1:
            shortcut = words[0]
            if shortcut in shortcuts:
                print("%s\t%s" % (shortcut, shortcuts[shortcut]))
            else:
                print("%s is not a shortcut" % shortcut)
        else:
            shortcuts[words[0]] = words[1]

    def do_debug(self, line):
        """Debug notifications, posts, or comments."""
        words = line.strip().split()
        if len(words) != 2:
            print("Debug takes two arguments: what to debug, and a number.")
            return
        if words[0] == "post":
            items = self.home
        elif words[0] == "notification":
            items = self.notifications
        elif words[0] == "comments":
            if self.post == None:
                print("Use the 'show' command to show a post, first.")
                return
            items = self.post.comments
        try:
            n = int(words[1])
            item = items[n-1]
        except ValueError:
            print("Debugging a %s requires an integer." % words[0])
            return
        except IndexError:
            print("There is no %s #%d" % n)
            return
        print(self.header("Debug %s #%d" % (words[0], n)))
        print(item.__dict__)

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
