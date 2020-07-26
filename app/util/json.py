try:
    import ujson
    import json
except ImportError:
    import json


if not ujson:
    ujson = json


def loads(data):
    return ujson.loads(data)


def dumps(data, default_parser=None):
    if default_parser:
        return json.dumps(data, default=default_parser)

    return ujson.dumps(data)


def parser(obj):

    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        msg = (
            'Object of type {} with value of {} is'
            ' not JSON serializable'
        ).format(type(obj), repr(obj))
        raise TypeError(msg)
