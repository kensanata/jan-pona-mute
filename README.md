Jan Pona Mute
=============

The name is Toki Pona and means "many friends".

This is a very simple command line client for Diaspora that helps me
deal with my specific use-cases:

- I want to check Diaspora for new comment on my threads
- I want to leave new comments on my threads
- I want to delete comments I left by mistake

It's *very* limited but it's helping me get started using the
[https://github.com/marekjm/diaspy diaspy] Python library.

Installation
------------

We need the [https://github.com/marekjm/diaspy diaspy] library.

```text
$ git clone https://github.com/marekjm/diaspy.git
$ cd diaspy
$ pip3 install .
```

This gives me version 0.6.0. when I use `pip3 install diaspy` I get
version 0.3.0 which doesn't work.

Quickstart
==========

```text
$ python3 jan-pona-mute.py
Welcome to Diaspora! Use the intro command for a quick introduction.
Pager set: /usr/bin/fold
> account kensanata@pluspora.com
Username and pod set: kensanata@pluspora.com
> password *secret*
Password set
> login
 1. 2019-08-13T19:40:17.000Z Joe Doe has liked your post I've started writing...
 2. 2019-08-13T17:59:23.000Z Joe Doe commented on your post Please help me wi...
 3. 2019-08-13T17:03:45.000Z Jane Doe has liked your post I've started writin...
 4. 2019-08-13T15:02:50.000Z June Doe commented on your post I don't like Mon...
 5. 2019-08-13T14:48:51.000Z John Doe liked your post Monday again! What am I...
Enter a number to select the notification.
> 1
2019-08-13T19:40:17.000Z Joe Doe has liked your post I've started writing...
Loading...

I've started writing a Diaspora client for the command line. It's called Jan Pona
Mute which means as much as "many friends" in English. It's written in Python and
doesn't do much.
> comments
There are no comments on the selected post.
> comment This is me leaving a comment.
Comment posted
> comments

 1. 2019-08-13T20:04:35.000Z Alex Schroeder

Alex Schroeder (e3bd7110b2ee013620f200505608f9fe): This is me leaving a comment.
> quit
Be safe!
```

Next Step
---------

Use the `save` command to save the login information (including the
password!) to an init file.

The init files searched are:

1. `~/.config/jan-pona-mute/login`
2. `~/.jan-pona-mute.d/login`
3. `~/.jan-pona-mute`

If one of them exists while starting up, that's the file that gets
written. If none exists, the first one is going to be created by the
`save` command.

Any further commands you put into the file are simple executed as if
you were to type them every time you start the program.

Notes
-----

One thing I care about is editing comments with my favourite editor
and previewing them. This works really well if you have `mdcat` as it
renders Markdown. Here's the workflow:

1. check notifications
2. pick a post
3. show latest comments
4. compose a note
5. preview note
6. leave a comment with that note

This is what it looks like, assuming your editor is `ed`:

```text
> notifications
...
> 1
...
> comments
...
> note nice
/home/alex/.config/jan-pona-mute/notes/nice: No such file or directory
a
OK, I like this. Thanks!
.
w
25
q
 1. nice
Use 'edit' to create a note.
> preview 1
OK, I like this. Thanks!
> comment 1
```

Reference
---------

So much is still in flux. Please use the `help` command to learn more.
