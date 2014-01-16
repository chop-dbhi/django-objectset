class cached_property(object):
    """Decorator that converts a method with a single self argument into a
    property cached on the instance.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        result = self.func(instance)
        instance.__dict__[self.func.__name__] = result
        return result
