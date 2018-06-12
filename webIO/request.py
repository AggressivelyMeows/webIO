"""
Basic request class/object
to handle translating to and from 
the server and any middleware/hooks
that are defined
"""
from contextlib import contextmanager


class Request():
    def __init__(self, *args, **kwargs):
        self.resolved = False # for when the request is done

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        # turn into dict
        # for require checking
        for k in (x for x in dir(self) if not x.startswith('__')):
            yield k, getattr(self, k)
