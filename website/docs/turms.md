---
sidebar_position: 5
sidebar_label: "Rath ❤️ Turms"
---

# Rath ❤️ Turms

### What is turms?

Turms is a graphql-codegen inspired code generator for pyhton that generates fully typed and
serialized operations from your graphql schema. Just define your query in standard graphql syntax
and let turms create fully typed queries/mutation and subscriptions, that you can use in your favourite
IDE.

### Design

Rath and Turms are developed independently, but are completely interoperable.

Consider this query

```graphql title="/graphql/get_capsules.graphql"
query get_capsules {
  capsules {
    id
    missions {
      flight
      name
    }
  }
}
```

On running (in your terminal)

```bash
turms gen
```

Turms generates automatically this pydantic schema for you

```python title="/schema/api.py"

class Get_capsulesQueryCapsulesMissions(GraphQLObject):
    typename: Optional[Literal["CapsuleMission"]] = Field(alias="__typename")
    flight: Optional[int]
    name: Optional[str]


class Get_capsulesQueryCapsules(GraphQLObject):
    typename: Optional[Literal["Capsule"]] = Field(alias="__typename")
    id: Optional[str]
    missions: Optional[List[Optional[Get_capsulesQueryCapsulesMissions]]]


class Get_capsulesQuery(GraphQLQuery):
    capsules: Optional[List[Optional[Get_capsulesQueryCapsules]]]

    class Meta:
        domain = "default"
        document = "query get_capsules {\n  capsules {\n    id\n    missions {\n      flight\n      name\n    }\n  }\n}"

```

Which you can than use easily in your rath code

```python
from rath import Rath
from schema.api import Get_capsulesQuery

rath = Rath(...)

typed_answer = GetcapuslesQuery(**rath.execute(GetcapuslesQuery.Meta.document).data) # fully tpyed

```

Also when using the Turms Operation Func plugin the turms generated
automatically registers fully typed utilify functions:

```python title="/schema/api.py"
def get_capsules() -> List[Get_capsulesQueryCapsules]:
    """get_capsules



    Arguments:

    Returns:
        Get_capsulesQueryCapsules: The returned Mutation"""
    return Get_capsulesQuery.execute({}).capsules

```

Isn't this lovely?
