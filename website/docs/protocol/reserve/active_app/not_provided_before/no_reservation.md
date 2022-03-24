---
sidebar_position: 1
sidebar_label: "First Reservation"
---

# First Reservation no provision active app

### Scenario

In this scenario arktitekt is as vanilla as it gets. You just
started an app (and started listening for provide requests (by running
the agent). Nobody has ever created a provision and somebody
tries to reserve this app.

### Checklist

- [ ] Reserved before
- [ ] Provided before
- [x] Active App

#### Scenario I (First Reservation (no provision))

```mermaid
sequenceDiagram
    autonumber
    participant Postman
    participant Postbox
    participant Waiter
    participant Agent
    Postman->>Postbox: Reservation
    Postbox->>Postbox: Check if Reservation viable
    Note right of Postbox: False
    Postbox->>Waiter: Provide and Reserve Provision
    Postbox->>Postman: Reservation Pending
    Waiter->>Agent: Provide Provision
    Agent->>Waiter: Provide Done
    Waiter->>Waiter: Check if Reservations viable
    Note right of Waiter: True
    Waiter->>Postbox: Reserve Done
    Postbox->>Postman: Reservation Active
```
