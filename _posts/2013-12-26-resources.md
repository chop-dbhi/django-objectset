---
layout: page
title: "Resources"
category: ref
---

_Added in 0.2.2_

django-objectset has support for defining RESTful resources using [restlib2](https://github.com/bruth/restlib2) and [django-preserialize](https://github.com/bruth/django-preserialize).

All resource representations are encoded as JSON and require the `Accept: application/json` header to be present. Likewise the `Content-Type: application/json` must be present for accepting request body's in `POST` and `PUT` requests.

### SetsResource

- `GET` - return an array of set instances
- `POST` - creates a new set instance

### SetResource

- `GET` - return a set instance for the specified primary key
- `PUT` - update an existing set instance
- `DELETE` - delete an existing set instance

### SetObjectsResource

- `GET` - returns the objects contained in a particular set

Here is an example JSON representation of a set resource:

```javascript
{
    "count": 3,
    "created": "2013-12-26T10:14:30",
    "modified": "2013-12-26T10:14:30",

    // other fields defined on the subclass..

    "_links": {
        "self": {
            "href": "http://example.com/sets/1/",
        },
        "parent": {
            "href": "http://example.com/sets/",
        },
        "objects": {
            "href": "http://example.com/sets/1/objects/",
        }
    }
}
```

## Usage

Here is an example from the test suite.

```python
from objectset.resources import get_url_patterns
from tests.models import RecordSet

urlpatterns = get_url_patterns(RecordSet)
```

`get_url_patterns` handles subclassing the above resource classes for `RecordSet` and setting up URL patterns for those resources. This can be appended to the urls in `ROOT_URLCONF`.
