---
layout: default
title: "django-objectset"
---

## Install

```bash
pip install django-objectset
```

## Define

```python
from django.contrib.auth.models import User
from objectset.models import ObjectSet

class Group(ObjectSet):
    users = models.ManyToManyField(User)
```

## Use

_Sets created using operators must be saved manually._

```python
>>> group1 = Group([user1, user2, user3], save=True)
>>> group2 = Group([user3, user4, user5, user6], save=True)
>>> len(group1)
3

>>> group1 & group2
Group([user3])

>>> group1 | group2
Group([user1, user2, user3, user4, user5, user6])

>>> group1 ^ group2
Group([user1, user2, user4, user5, user6])

>>> group1 - group2
Group([user4, user5, user6])
```
