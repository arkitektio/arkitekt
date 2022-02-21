---
sidebar_label: waitfor
title: cli.prod.waitfor
---

#### wait\_for\_connection

```python
async def wait_for_connection(modules: List[str])
```

Wits for connection

Import required Modules for this instance to run and tries to
connect to the wards.

TODO: The wards are not checked if alive at the same time
at the end

**Arguments**:

- `modules` _List[str]_ - The imported modules

