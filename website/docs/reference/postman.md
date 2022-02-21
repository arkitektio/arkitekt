---
sidebar_label: postman
title: postman
---

## Postman Objects

```python
class Postman()
```

#### stream\_replies\_to\_queue

```python
async def stream_replies_to_queue(message: MessageModel)
```

Creates a queue for this referenced message
and forwards every message on a reply channel to the return queue

**Arguments**:

- `message` _MessageModel_ - [description]
  

**Returns**:

- `asyncio.Queue` - The Reply Queue

