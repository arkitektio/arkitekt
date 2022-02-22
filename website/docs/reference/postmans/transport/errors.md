---
sidebar_label: errors
title: postmans.transport.errors
---

## PostmanTransportException Objects

```python
class PostmanTransportException(PostmanException)
```

Base class for all exceptions raised by the Agent Transport.

## ReservationListDeniedError Objects

```python
class ReservationListDeniedError(PostmanTransportException)
```

Raised when the backend is not able to list the provisions.

## AssignationListDeniedError Objects

```python
class AssignationListDeniedError(PostmanTransportException)
```

Raised when the backend is not able to list the assignations.

## AssignDeniedError Objects

```python
class AssignDeniedError(PostmanTransportException)
```

Raised when the backend is not able to list the provisions.

## ReserveDeniedError Objects

```python
class ReserveDeniedError(PostmanTransportException)
```

Raised when the backend is not able to list the assignations.

