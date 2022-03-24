---
sidebar_position: 1
sidebar_label: "Design"
---

# Design

Arkitekt provides to major abstractions for your clients.
**Provisions** and **Reservation**

## Reservations

**Reservations** are contracts that you have with arkitekt. They describe
which node you want to use with what parallelization strategy.

#### For example:

You have a connected app that _provides_ a node to convolve an image. In order
to use it you first _reserve_ that node and then you can _assign_ tasks to it.

## Provisions

**Provisions** are contracts that you need to fullfill as a client app.
If you register to be able to provide for a nodeyou need to listen to the waiter endpoint and accept provisions and mark them active.

:::tip
You can of course decide to never register templates and use the
app as a pure client. But if you do, you should make sure you fullfill your
provisions.
:::

## Decision Tree for Protocol

```mermaid
flowchart TD
    A[Start]-->B[Agent online]
    B--->|Yes| C[Provided Before]
    B--->|No| D[Provided Before]
    C--->|Yes| E[Reserved Before]
    C--->|No| F[Reserved Before]
    D--->|Yes| G[Reserved Before]
    D--->|No| H[Reserved Before]
    E--->|Yes| I[Clickme]
    E--->|No| J[Clickme]
    F--->|Yes| K[Clickme]
    F--->|No| L[Clickme]
    G--->|Yes| M[Clickme]
    G--->|No| N[Clickme]
    H--->|Yes| O[Clickme]
    H--->|No| P[Clickme]


    click I href "/arkitekt/docs/protocol/reserve/no_provision"
    click J href "/arkitekt/docs/protocol/reserve/no_provision"
    click K href "/arkitekt/docs/protocol/reserve/no_provision"
    click L href "/arkitekt/docs/protocol/reserve/no_provision"
    click M href "/arkitekt/docs/protocol/reserve/no_provision"
    click N href "/arkitekt/docs/protocol/reserve/no_provision"
    click O href "/arkitekt/docs/protocol/reserve/no_provision"
    click P href "/arkitekt/docs/protocol/reserve/no_provision"

```
