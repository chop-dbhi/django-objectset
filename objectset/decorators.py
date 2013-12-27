from functools import wraps


def cached_property(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        key = '_{0}_cache'.format(func.__name__)
        if not hasattr(self, key):
            setattr(self, key, func(self, *args, **kwargs))
        return getattr(self, key)
    return property(inner)
