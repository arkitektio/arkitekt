---
sidebar_position: 3
sidebar_label: "First Reservation (unactive provision)"
---

# First Reservation of unactive provision

### Scenario

In this scenario you or somebody else has already caused arkitekt to
create a provision of a specific node. Now you want to reserve that provision
with a specific set of parameters.

```mermaid
sequenceDiagram
    autonumber
    participant Postman
    participant Postbox
    participant Waiter
    participant Agent
    Postman->>Postbox: Reservation
    Postbox->>Postbox: Check if active
    Note right of Postbox: False
    Postbox->>Postman: Reservation Pending
```

Later after Agent connects

```mermaid
sequenceDiagram
    autonumber
    participant Postman
    participant Postbox
    participant Waiter
    participant Agent
    Waiter->>Agent: Provisions
    Agent->>Waiter: Provide Done
    Waiter->>Waiter: Check if active
    Note right of Postbox: True
    Waiter->>Postbox: Reserve Done
    Postbox->>Postman: Reservation Done
```
