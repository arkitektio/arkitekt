---
sidebar_position: 5
sidebar_label: "Arkitekt ❤️ Fluss"
---

# Arkitekt ❤️ Fluss

### What is Fluss?

Fluss is a reactive task scheduler for the arkitekt framework. While arkitekt takes care of discovering
and calling your apps in a reliable and reusable manner. Fluss plays a role in orchestrating these tasks

### Design

Fluss enables you to construct workflows in a graphical manner like the one below, utilizing nodes that you
define within arkitekt

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
