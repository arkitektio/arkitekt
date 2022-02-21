---
sidebar_label: utils
title: actors.utils
---

#### log

```python
def log(message: str, level: str = "info")
```

Logs a message

Depending on both the configuration of Arkitekt and the overwrite set on the
Assignment, this logging will be sent (and persisted) on the Arkitekt server

**Arguments**:

- `message` _sr_ - The Message you want to send
- `level` _DebugLevel, optional_ - The level of the log. Defaults to DebugLevel.INFO.
  

**Returns**:

- `[Future]` - Returns a future if currently running in an event loop

