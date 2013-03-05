class ObjectSetError(Exception):
    def __init__(self, msg=None):
        if msg is None:
            msg = 'ObjectSet instance needs to have a primary key ' \
                'before set operations can be used.'
        Exception.__init__(self, msg)
