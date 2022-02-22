---
sidebar_position: 1
sidebar_label: "Introduction"
---

# Quick Start

Let's discover **Arkitekt in less than 5 minutes**.

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
