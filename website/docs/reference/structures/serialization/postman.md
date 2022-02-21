---
sidebar_label: postman
title: structures.serialization.postman
---

#### shrink\_inputs

```python
async def shrink_inputs(node: NodeFragment, args: List[Any], kwargs: Dict[str, Any], structure_registry: StructureRegistry) -> List[Any]
```

Shrinks args and kwargs

Shrinks the inputs according to the Node Definition

**Arguments**:

- `node` _Node_ - The Node
  

**Raises**:

- `ShrinkingError` - If args are not Shrinkable
- `ShrinkingError` - If kwargs are not Shrinkable
  

**Returns**:

  Tuple[List[Any], Dict[str, Any]]: Parsed Args as a List, Parsed Kwargs as a dict

#### expand\_outputs

```python
async def expand_outputs(node: NodeFragment, returns: List[Any], structure_registry: StructureRegistry) -> List[Any]
```

Expands Returns

Expands the Returns according to the Node definition


**Arguments**:

- `node` _Node_ - Node definition
- `returns` _List[any]_ - The returns
  

**Raises**:

- `ExpandingError` - if they are not expandable
  

**Returns**:

- `List[Any]` - The Expanded Returns

