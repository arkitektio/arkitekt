---
sidebar_label: registry
title: definition.registry
---

#### register

```python
def register(widgets: Dict[str, WidgetInput] = {}, interfaces: List[str] = [], on_provide=None, on_unprovide=None, definition_registry: DefinitionRegistry = None, structure_registry: StructureRegistry = None, **params)
```

Take a function and register it as a node.

This function is used to register a node. Use it as a decorator. You can specify
specific widgets for every paramer in a dictionary {argument_key: widget}. By default
this function will use the default defintion registry to store the nodes inputdata.
This definition registry will then be used by an agent to create, and provide the node.

If your function has specific inputs that need custom rules for expansion and shrinking
, you can pass a structure registry to the function. This registry will then be used.

This decorator is non intrusive. You can still call this function as a normal function from
your code

**Arguments**:

- `widgets` _Dict[str, WidgetInput], optional_ - _description_. Defaults to {}.
- `interfaces` _List[str], optional_ - _description_. Defaults to [].
- `on_provide` __type_, optional_ - _description_. Defaults to None.
- `on_unprovide` __type_, optional_ - _description_. Defaults to None.
- `definition_registry` _DefinitionRegistry, optional_ - _description_. Defaults to None.
- `structure_registry` _StructureRegistry, optional_ - _description_. Defaults to None.
  

**Returns**:

- `Callable` - A wrapped function that just returns the original function.

