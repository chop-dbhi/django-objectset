---
layout: page
title: "Operations"
category: ref
date: 2013-06-10 22:43:48
---

The `ObjectSet` model has support for common set operations. For the examples below, consider the two sets (we can assume the numbers are primary keys to objects):

```python
>>> set1 = Set([1, 2, 3, 5, 8, 13])
>>> set2 = Set([2, 5, 8, 11, 14])
```

_Note: all new sets or in-place changes must be saved after the operations have been applied._

#### Logical AND (conjunction)

```python
>>> set1 & set2
Set([2, 5, 8])
```

#### Logical OR (disjunction)

```python
>>> set1 | set2
Set([1, 2, 3, 5, 8, 11, 13, 14])
```

#### Logical XOR (exclusive disjunction)

```python
>>> set1 ^ set2
Set([1, 3, 11, 13, 14])
```

#### Difference (substraction)

```python
>>> set1 - set2
Set([1, 3, 13])

# reverse
>>> set2 - set1
Set([11, 14])
```

Of course, set operations can be chained:

```python
>>> set2 - set1 ^ set1 - set2 & set1
Set([1, 3, 11, 13, 14])

# equivalent
>>> set2 - (set1 ^ (set1 - (set2 & set1)))
Set([1, 3, 11, 13, 14])
```

### In-place Operations

All operations above can also be performed _in-place_ for the left operand by adding a `=` suffix to the operator:

```python
>>> set1 &= set2
>>> set1 |= set2
>>> set1 ^= set2
>>> set1 -= set2
```
