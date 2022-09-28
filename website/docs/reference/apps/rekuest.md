---
sidebar_label: rekuest
title: apps.rekuest
---

## RekuestApp Objects

```python
class RekuestApp(HerreApp)
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

#### rekuest

The mikro layer that is used for the datalayer and
api client

