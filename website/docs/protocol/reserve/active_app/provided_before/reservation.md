---
sidebar_position: 2
sidebar_label: "Renewed Reservation"
---

# First Reservation no provision active app

### Scenario

In this scenario you have already reserved a node before and the app is active

### Checklist

- [x] Reserved before
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
    Note right of Postbox: Active
    Postbox->>Postman: Reservation Active
```
