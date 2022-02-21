---
sidebar_label: errors
title: agents.transport.errors
---

## AgentTransportException Objects

```python
class AgentTransportException(AgentException)
```

Base class for all exceptions raised by the Agent Transport.

## ProvisionListDeniedError Objects

```python
class ProvisionListDeniedError(AgentTransportException)
```

Raised when the backend is not able to list the provisions.

## AssignationListDeniedError Objects

```python
class AssignationListDeniedError(AgentTransportException)
```

Raised when the backend is not able to list the assignations.

