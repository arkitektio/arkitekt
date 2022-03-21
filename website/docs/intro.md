---
sidebar_position: 1
sidebar_label: "Introduction"
---

# Quick Start

Let's discover **Arkitekt in less than 5 minutes**.

### Core Ideas

Arkitekt tries to establish a protocol and implementation for the **reliable distribution** of tasks among **unsteady** workers.

### The why?

We developed arkitekt and the surrounding framework for our needs that arose in the context of
scientific image processing. We set out to design a workflow orchestration tool that can span multiple
image analysis tools on multiple participating computers. As a integral part of this we needed a solution
the distribution of this tasks to the participating tools. This is arkitekt. It establishes an API for a remote procedure
call (RPC) interface that has the following features:

- **Workers are Clients**: Workers are Clients (see Arkitekt vs other RPCs)
- **Workers are authenticated** Workers are Applications in the OAuth sense, that means they authenticate by User and Scope
- **Tasks are futures** Focussing on async programming, tasks are fully featured Futures (Tasks), that means you can also cancel (on another computer)
- **Tasks are abstract** Tasks can share the same logic (signature), but be implemented by different workers
- **Tasks are distributed** Tasks are automatically distributed amongst apps that share the same implementation

### Inspiration

Arkitekt tries to help in the automation of complex analysis pipelines. It is designed for task
distribution amongst **untrusted** and **unsteady** workes. What do we mean by this?

#### Arkitekt vs Celery

Arkitekt takes heavy inspiration from RPC Frameworks like Celery but has a completely different approach.
Whereas Celery tries to offload tasks on workers in the background of a server. Arkitekt tries to schedule
work on the clients conneted to said worker.

**Celery**:

```mermaid
flowchart LR;
    id0(Client)-->|Request|id2(Server)
    id1(Client2)-->|Request|id2(Server)
    id2(Server)-->|Task|id6(Worker)
    id2(Server)-->|Task|id3(Worker)
    id2(Server)-->|Task|id4(Worker)
    id2(Server)-->|Task|id5(Worker)
```

**Arkitekt**:

```mermaid
flowchart LR;
    id0(Client)-->|Request|id10(Arkitekt)
    id10(Arkitekt)-->|Task|id0(Client)
    id1(Client2)-->|Request|id10(Arkitekt)
    id10(Arkitekt)-->|Task|id1(Client2)
    id2(Client2)-->|Request|id10(Arkitekt)
    id10(Arkitekt)-->|Task|id2(Client3)

```

### Trust Issues

With this sort of layout comes one essential problem.. **Trust!**

### Installation

```bash
pip install rath
```

## Initilization

```python
from rath.links.aiohttp import AioHttpLink

link = AioHttpLink(url="https://api.spacex.land/graphql/")


rath = Rath(link=link)

query = """query TestQuery {
  capsules {
    id
    missions {
      flight
    }
  }
}
"""

result = rath.execute(query)
```
