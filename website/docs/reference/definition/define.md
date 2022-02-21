---
sidebar_label: define
title: definition.define
---

#### convert\_arg\_to\_argport

```python
def convert_arg_to_argport(cls, registry: StructureRegistry, widget=None, key=None) -> ArgPortInput
```

Convert a class to an ArgPort

#### convert\_kwarg\_to\_kwargport

```python
def convert_kwarg_to_kwargport(cls, registry: StructureRegistry, widget=None, key=None, default=None) -> ArgPortInput
```

Convert a class to an ArgPort

#### convert\_return\_to\_returnport

```python
def convert_return_to_returnport(cls, registry: StructureRegistry, key=None, default=None) -> ReturnPortInput
```

Convert a class to an ArgPort

#### prepare\_definition

```python
def prepare_definition(function: Callable, widgets={}, allow_empty_doc=False, interfaces=[], structure_registry: StructureRegistry = None) -> DefinitionInput
```

Define

Define a functions in the context of arnheim and
return it as a Node. Attention this node is not yet
hosted on Arkitekt (doesn&#x27;t have an id). So make sure
to save this node before calling it anywhere

**Arguments**:

  function (): The function you want to define

