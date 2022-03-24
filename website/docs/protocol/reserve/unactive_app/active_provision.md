---
sidebar_position: 2
sidebar_label: "First Reservation of active provision"
---

# First Reservation no provision active app

### Scenario

In this scenario you or somebody else has already caused arkitekt to
create a provision of a specific node. Now you want to reserve that provision
with a specific set of parameters.

### Checklist

- [ ] Reserved before
- [x] Provided before
- [x] Active App

#### Scenario I (First Reservation (already active provision))

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
    Postbox->>Waiter: Reserve Provision
    Waiter->>Waiter: Check if Reservations viable
    Note right of Postbox: True
    Waiter->>Postbox: Reserve Done
    Postbox->>Postman: Reservation Active
```
