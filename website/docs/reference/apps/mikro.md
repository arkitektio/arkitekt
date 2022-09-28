---
sidebar_label: mikro
title: apps.mikro
---

This modules provides the main app. It is responsible for setting up the connection to the mikro-server and
handling authentification and setting up the configuration. Mikro handles the creation of the datalayer and
the graphql client.

You can compose this app together with other apps to create a full fledged app. (Like combining with
arkitekt to enable to call functions that you define on the app)

**Example**:

  
  A simple app that takes it configuraiton from basic.fakts and connects to the mikro-server.
  You can define all of the logic within the context manager
  
  ```python
  from mikro.app import MikroApp
  
  app = MikroApp(fakts=Fakts(subapp=&quot;basic&quot;))
  
  with app:
  # do stuff
  
  ```
  
  Async Usage:
  
  
  ```python
  from mikro.app import MikroApp
  
  app = MikroApp(fakts=Fakts(subapp=&quot;basic&quot;))
  
  async with app:
  # do stuff
  
  ```

## MikroApp Objects

```python
class MikroApp(HerreApp)
```

Mikro App

It is responsible for setting up the connection to the mikro-server and
handling authentification and setting up the configuration. Mikro handles the creation of the datalayer and
the graphql client.

You can compose this app together with other apps to create a full fledged app. (Like combining with
arkitekt to enable to call functions that you define on the app). See the example in the docstring.

**Attributes**:

- `fakts` _Fakts_ - The fakts instance to use.
- `mikro` _Mikro_ - The mikro instance to use.
- `herre` _Herre_ - The herre instance to use.

