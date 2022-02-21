---
sidebar_label: base
title: agents.transport.base
---

## AgentTransport Objects

```python
class AgentTransport()
```

Agent Transport

A Transport is a means of communicating with an Agent. It is responsible for sending
and receiving messages from the backend. It needs to implement the following methods:

list_provision: Getting the list of active provisions from the backend. (depends on the backend)
list_assignation: Getting the list of active assignations from the backend. (depends on the backend)

change_assignation: Changing the status of an assignation. (depends on the backend)
change_provision: Changing the status of an provision. (depends on the backend)

broadcast: Configuring the callbacks for the transport on new assignation, unassignation provision and unprovison.

if it is a stateful connection it can also implement the following methods:

aconnect
adisconnect

