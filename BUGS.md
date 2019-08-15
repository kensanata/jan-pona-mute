Bugs
====

- `undo` a comment post results in an error:

```
  File "/home/alex/bin/jan-pona-mute", line 495, in do_delete
    post = self.post_cache[words[3]]
KeyError: '1869713'
```
  
