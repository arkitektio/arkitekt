---
sidebar_label: schema
title: api.schema
---

## NodeType Objects

```python
class NodeType(str,  Enum)
```

An enumeration.

#### GENERATOR

Generator

#### FUNCTION

Function

## LokAppGrantType Objects

```python
class LokAppGrantType(str,  Enum)
```

An enumeration.

#### CLIENT\_CREDENTIALS

Backend (Client Credentials)

#### IMPLICIT

Implicit Grant

#### AUTHORIZATION\_CODE

Authorization Code

#### PASSWORD

Password

#### SESSION

Django Session

## RepositoryType Objects

```python
class RepositoryType(str,  Enum)
```

An enumeration.

#### APP

Repository that is hosted by an App

#### MIRROR

Repository mirrors online Repository

## ProvisionMode Objects

```python
class ProvisionMode(str,  Enum)
```

An enumeration.

#### DEBUG

Debug Mode (Node might be constantly evolving)

#### PRODUCTION

Production Mode (Node might be constantly evolving)

## ReservationStatus Objects

```python
class ReservationStatus(str,  Enum)
```

An enumeration.

#### ROUTING

Routing (Reservation has been requested but no Topic found yet)

#### PROVIDING

Providing (Reservation required the provision of a new worker)

#### WAITING

Waiting (We are waiting for any assignable Topic to come online)

#### REROUTING

Rerouting (State of provisions this reservation connects to have changed and require Retouring)

#### DISCONNECTED

Disconnect (State of provisions this reservation connects to have changed and require Retouring)

#### DISCONNECT

Disconnect (State of provisions this reservation connects to have changed and require Retouring)

#### CANCELING

Cancelling (Reervation is currently being cancelled)

#### ACTIVE

Active (Reservation is active and accepts assignments

#### ERROR

Error (Reservation was not able to be performed (See StatusMessage)

#### ENDED

Ended (Reservation was ended by the the Platform and is no longer active)

#### CANCELLED

Cancelled (Reservation was cancelled by user and is no longer active)

#### CRITICAL

Critical (Reservation failed with an Critical Error)

## WaiterStatus Objects

```python
class WaiterStatus(str,  Enum)
```

An enumeration.

#### ACTIVE

Active

#### DISCONNECTED

Disconnected

#### VANILLA

Complete Vanilla Scenario after a forced restart of

## AssignationStatus Objects

```python
class AssignationStatus(str,  Enum)
```

An enumeration.

#### PENDING

Pending

#### ACKNOWLEDGED

Acknowledged

#### RETURNED

Assignation Returned (Only for Functions)

#### DENIED

Denied (Assingment was rejected)

#### ASSIGNED

Was able to assign to a pod

#### PROGRESS

Progress (Assignment has current Progress)

#### RECEIVED

Received (Assignment was received by an agent)

#### ERROR

Error (Retrieable)

#### CRITICAL

Critical Error (No Retries available)

#### CANCEL

Assinment is beeing cancelled

#### CANCELING

Cancelling (Assingment is currently being cancelled)

#### CANCELLED

Assignment has been cancelled.

#### YIELD

Assignment yielded a value (only for Generators)

#### DONE

Assignment has finished

## AssignationLogLevel Objects

```python
class AssignationLogLevel(str,  Enum)
```

An enumeration.

#### CRITICAL

CRITICAL Level

#### INFO

INFO Level

#### DEBUG

DEBUG Level

#### ERROR

ERROR Level

#### WARN

WARN Level

#### YIELD

YIELD Level

#### CANCEL

Cancel Level

#### RETURN

YIELD Level

#### DONE

Done Level

#### EVENT

Event Level (only handled by plugins)

## LogLevelInput Objects

```python
class LogLevelInput(str,  Enum)
```

An enumeration.

#### CRITICAL

CRITICAL Level

#### INFO

INFO Level

#### DEBUG

DEBUG Level

#### ERROR

ERROR Level

#### WARN

WARN Level

#### YIELD

YIELD Level

#### CANCEL

Cancel Level

#### RETURN

YIELD Level

#### DONE

Done Level

#### EVENT

Event Level (only handled by plugins)

## ReservationLogLevel Objects

```python
class ReservationLogLevel(str,  Enum)
```

An enumeration.

#### CRITICAL

CRITICAL Level

#### INFO

INFO Level

#### DEBUG

DEBUG Level

#### ERROR

ERROR Level

#### WARN

WARN Level

#### YIELD

YIELD Level

#### CANCEL

Cancel Level

#### RETURN

YIELD Level

#### DONE

Done Level

#### EVENT

Event Level (only handled by plugins)

## AgentStatus Objects

```python
class AgentStatus(str,  Enum)
```

An enumeration.

#### ACTIVE

Active

#### DISCONNECTED

Disconnected

#### VANILLA

Complete Vanilla Scenario after a forced restart of

## ProvisionAccess Objects

```python
class ProvisionAccess(str,  Enum)
```

An enumeration.

#### EXCLUSIVE

This Topic is Only Accessible linkable for its creating User

#### EVERYONE

Everyone can link to this Topic

## ProvisionStatus Objects

```python
class ProvisionStatus(str,  Enum)
```

An enumeration.

#### PENDING

Pending (Request has been created and waits for its initial creation)

#### BOUND

Bound (Provision was bound to an Agent)

#### PROVIDING

Providing (Request has been send to its Agent and waits for Result

#### ACTIVE

Active (Provision is currently active)

#### INACTIVE

Inactive (Provision is currently not active)

#### CANCELING

Cancelling (Provisions is currently being cancelled)

#### LOST

Lost (Subscribers to this Topic have lost their connection)

#### RECONNECTING

Reconnecting (We are trying to Reconnect to this Topic)

#### DENIED

Denied (Provision was rejected for this User)

#### ERROR

Error (Reservation was not able to be performed (See StatusMessage)

#### CRITICAL

Critical (Provision resulted in an critical system error)

#### ENDED

Ended (Provision was cancelled by the Platform and will no longer create Topics)

#### CANCELLED

Cancelled (Provision was cancelled by the User and will no longer create Topics)

## ProvisionLogLevel Objects

```python
class ProvisionLogLevel(str,  Enum)
```

An enumeration.

#### CRITICAL

CRITICAL Level

#### INFO

INFO Level

#### DEBUG

DEBUG Level

#### ERROR

ERROR Level

#### WARN

WARN Level

#### YIELD

YIELD Level

#### CANCEL

Cancel Level

#### RETURN

YIELD Level

#### DONE

Done Level

#### EVENT

Event Level (only handled by plugins)

## AssignationStatusInput Objects

```python
class AssignationStatusInput(str,  Enum)
```

An enumeration.

#### PENDING

Pending

#### ACKNOWLEDGED

Acknowledged

#### RETURNED

Assignation Returned (Only for Functions)

#### DENIED

Denied (Assingment was rejected)

#### ASSIGNED

Was able to assign to a pod

#### PROGRESS

Progress (Assignment has current Progress)

#### RECEIVED

Received (Assignment was received by an agent)

#### ERROR

Error (Retrieable)

#### CRITICAL

Critical Error (No Retries available)

#### CANCEL

Assinment is beeing cancelled

#### CANCELING

Cancelling (Assingment is currently being cancelled)

#### CANCELLED

Assignment has been cancelled.

#### YIELD

Assignment yielded a value (only for Generators)

#### DONE

Assignment has finished

## ProvisionStatusInput Objects

```python
class ProvisionStatusInput(str,  Enum)
```

An enumeration.

#### PENDING

Pending (Request has been created and waits for its initial creation)

#### BOUND

Bound (Provision was bound to an Agent)

#### PROVIDING

Providing (Request has been send to its Agent and waits for Result

#### ACTIVE

Active (Provision is currently active)

#### INACTIVE

Inactive (Provision is currently not active)

#### CANCELING

Cancelling (Provisions is currently being cancelled)

#### DISCONNECTED

Lost (Subscribers to this Topic have lost their connection)

#### RECONNECTING

Reconnecting (We are trying to Reconnect to this Topic)

#### DENIED

Denied (Provision was rejected for this User)

#### ERROR

Error (Reservation was not able to be performed (See StatusMessage)

#### CRITICAL

Critical (Provision resulted in an critical system error)

#### ENDED

Ended (Provision was cancelled by the Platform and will no longer create Topics)

#### CANCELLED

Cancelled (Provision was cancelled by the User and will no longer create Topics)

## NodeTypeInput Objects

```python
class NodeTypeInput(str,  Enum)
```

An enumeration.

#### GENERATOR

Generator

#### FUNCTION

Function

## AgentStatusInput Objects

```python
class AgentStatusInput(str,  Enum)
```

An enumeration.

#### ACTIVE

Active

#### DISCONNECTED

Disconnected

#### VANILLA

Complete Vanilla Scenario after a forced restart of

## StructureBound Objects

```python
class StructureBound(str,  Enum)
```

An enumeration.

#### AGENT

Bound to one Agent (Instance Dependented)

#### REGISTRY

Registry (User Dependent)

#### APP

Bound to one Application (User independent)

#### GLOBAL

Unbound and usable for every application

## ReservationStatusInput Objects

```python
class ReservationStatusInput(str,  Enum)
```

An enumeration.

#### ROUTING

Routing (Reservation has been requested but no Topic found yet)

#### PROVIDING

Providing (Reservation required the provision of a new worker)

#### WAITING

Waiting (We are waiting for any assignable Topic to come online)

#### REROUTING

Rerouting (State of provisions this reservation connects to have changed and require Retouring)

#### DISCONNECTED

Disconnect (State of provisions this reservation connects to have changed and require Retouring)

#### DISCONNECT

Disconnect (State of provisions this reservation connects to have changed and require Retouring)

#### CANCELING

Cancelling (Reervation is currently being cancelled)

#### ACTIVE

Active (Reservation is active and accepts assignments

#### ERROR

Error (Reservation was not able to be performed (See StatusMessage)

#### ENDED

Ended (Reservation was ended by the the Platform and is no longer active)

#### CANCELLED

Cancelled (Reservation was cancelled by user and is no longer active)

#### CRITICAL

Critical (Reservation failed with an Critical Error)

## BoundTypeInput Objects

```python
class BoundTypeInput(str,  Enum)
```

An enumeration.

#### AGENT

Bound to one Agent (Instance Dependented)

#### REGISTRY

Registry (User Dependent)

#### APP

Bound to one Application (User independent)

#### GLOBAL

Unbound and usable for every application

## ArgPortInput Objects

```python
class ArgPortInput(BaseModel)
```

#### key

The Key

#### type

the type of input

#### typename

the type of input

#### description

A description for this Port

#### label

The Label of this inport

#### identifier

The corresponding Model

#### widget

Which Widget to use to render Port in User Interfaces

#### bound

Where should this be bound to (only Structures

#### child

The Child of this

#### transpile

The corresponding Model

#### options

Options for an Enum

## WidgetInput Objects

```python
class WidgetInput(BaseModel)
```

#### typename

type

#### query

Do we have a possible

#### dependencies

The dependencies of this port

#### max

Max value for int widget

#### min

Max value for int widget

#### placeholder

Placeholder for any widget

## KwargPortInput Objects

```python
class KwargPortInput(BaseModel)
```

#### key

The Key

#### type

the type of input

#### typename

the type of input

#### description

A description for this Port

#### label

The Label of this inport

#### defaultDict

Does this field have a specific value

#### defaultOption

Does this field have a specific value

#### defaultInt

Does this field have a specific value

#### defaultBool

Does this field have a specific value

#### defaultFloat

Does this field have a specific value

#### defaultID

Does this field have a specific value

#### defaultString

Does this field have a specific value

#### defaultList

Does this field have a specific value

#### identifier

The corresponding Model

#### widget

Which Widget to use to render Port in User Interfaces

#### bound

Where should this be bound to (only Structures

#### child

The Child of this

#### transpile

The corresponding Model

#### options

Options for an Enum

## ReturnPortInput Objects

```python
class ReturnPortInput(BaseModel)
```

#### key

The Key

#### type

the type of input

#### typename

the type of input

#### description

A description for this Port

#### bound

Where should this be bound to (only Structures

#### label

The Label of this Outport

#### identifier

The corresponding Model

#### child

The Child of this

#### transpile

The corresponding Model

## DefinitionInput Objects

```python
class DefinitionInput(BaseModel)
```

A definition for a node

#### description

A description for the Node

#### name

The name of this template

#### args

The Args

#### kwargs

The Kwargs

#### returns

The Returns

#### interfaces

The Interfaces this node provides [eg. bridge, filter]

#### type

The variety

#### interface

The Interface

#### package

The Package

## ReserveParamsInput Objects

```python
class ReserveParamsInput(BaseModel)
```

#### autoProvide

Do you want to autoprovide

#### autoUnprovide

Do you want to auto_unprovide

#### registries

Registry thar are allowed

#### agents

Agents that are allowed

#### templates

Templates that can be selected

#### desiredInstances

The desired amount of Instances

#### minimalInstances

The minimal amount of Instances

## AssignationFragment Objects

```python
class AssignationFragment(GraphQLObject)
```

#### parent

The Assignations parent

#### status

Current lifecycle of Assignation

#### statusmessage

Clear Text status of the Assignation as for now

## TranscriptFragmentPostman Objects

```python
class TranscriptFragmentPostman(GraphQLObject)
```

#### type

The communication protocol

#### kwargs

kwargs for your postman

## StructureArgPortFragment Objects

```python
class StructureArgPortFragment(StructureExpander,  GraphQLObject)
```

#### identifier

The identifier of this Model

## ListArgPortFragmentChildStructureArgPortFragment Objects

```python
class ListArgPortFragmentChildStructureArgPortFragment(
    StructureExpander,  ListArgPortFragmentChildBase)
```

#### identifier

The identifier of this Model

## ListArgPortFragment Objects

```python
class ListArgPortFragment(ListExpander,  GraphQLObject)
```

#### child

The child

## DictArgPortFragmentChildStructureArgPortFragment Objects

```python
class DictArgPortFragmentChildStructureArgPortFragment(
    StructureExpander,  DictArgPortFragmentChildBase)
```

#### identifier

The identifier of this Model

## DictArgPortFragment Objects

```python
class DictArgPortFragment(DictExpander,  GraphQLObject)
```

#### child

The child

## DictKwargPortFragmentChildStructureKwargPortFragment Objects

```python
class DictKwargPortFragmentChildStructureKwargPortFragment(
    StructureExpander,  DictKwargPortFragmentChildBase)
```

#### identifier

The identifier of this Model

## DictKwargPortFragment Objects

```python
class DictKwargPortFragment(DictExpander,  GraphQLObject)
```

#### defaultDict

TheList

#### child

The child

## BoolKwargPortFragment Objects

```python
class BoolKwargPortFragment(BoolExpander,  GraphQLObject)
```

#### defaultBool

Default value

## IntKwargPortFragment Objects

```python
class IntKwargPortFragment(IntExpander,  GraphQLObject)
```

#### defaultInt

Default value

## StringKwargPortFragment Objects

```python
class StringKwargPortFragment(StringExpander,  GraphQLObject)
```

#### defaultString

Default value

## ListKwargPortFragmentChildStructureKwargPortFragment Objects

```python
class ListKwargPortFragmentChildStructureKwargPortFragment(
    StructureExpander,  ListKwargPortFragmentChildBase)
```

#### identifier

The identifier of this Model

## ListKwargPortFragment Objects

```python
class ListKwargPortFragment(ListExpander,  GraphQLObject)
```

#### child

The child

#### defaultList

TheList

## ListReturnPortFragmentChildStructureReturnPortFragment Objects

```python
class ListReturnPortFragmentChildStructureReturnPortFragment(
    StructureExpander,  ListReturnPortFragmentChildBase)
```

#### identifier

The identifier of this Model

## ListReturnPortFragment Objects

```python
class ListReturnPortFragment(ListExpander,  GraphQLObject)
```

#### child

The child

## StructureReturnPortFragment Objects

```python
class StructureReturnPortFragment(StructureExpander,  GraphQLObject)
```

#### identifier

The identifier of this Model

## ReservationFragmentNode Objects

```python
class ReservationFragmentNode(Reserve,  GraphQLObject)
```

#### pure

Is this function pure. e.g can we cache the result?

## ReservationFragment Objects

```python
class ReservationFragment(GraphQLObject)
```

#### statusmessage

Clear Text status of the Provision as for now

#### status

Current lifecycle of Reservation

#### node

The node this reservation connects

## NodeFragment Objects

```python
class NodeFragment(Reserve,  GraphQLObject)
```

#### name

The cleartext name of this Node

#### interface

Interface (think Function)

#### package

Package (think Module)

#### description

A description for the Node

#### type

Function, generator? Check async Programming Textbook

## TemplateFragmentRegistryUser Objects

```python
class TemplateFragmentRegistryUser(GraphQLObject)
```

#### username

Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.

## TemplateFragmentRegistry Objects

```python
class TemplateFragmentRegistry(GraphQLObject)
```

#### name

DEPRECATED Will be replaced in the future: : None

#### app

The Associated App

#### user

The Associated App

## TemplateFragment Objects

```python
class TemplateFragment(GraphQLObject)
```

#### registry

The associated registry for this Template

#### node

The node this template is implementatig

## Get\_provisionQueryProvisionTemplateNode Objects

```python
class Get_provisionQueryProvisionTemplateNode(Reserve,  GraphQLObject)
```

#### name

The cleartext name of this Node

## Get\_provisionQueryProvisionTemplateRegistry Objects

```python
class Get_provisionQueryProvisionTemplateRegistry(GraphQLObject)
```

#### app

The Associated App

## Get\_provisionQueryProvisionTemplate Objects

```python
class Get_provisionQueryProvisionTemplate(GraphQLObject)
```

#### node

The node this template is implementatig

#### registry

The associated registry for this Template

#### extensions

The extentions of this template

## Get\_provisionQueryProvisionBoundRegistry Objects

```python
class Get_provisionQueryProvisionBoundRegistry(GraphQLObject)
```

#### name

DEPRECATED Will be replaced in the future: : None

## Get\_provisionQueryProvisionBound Objects

```python
class Get_provisionQueryProvisionBound(GraphQLObject)
```

#### registry

The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users

#### name

This providers Name

## Get\_provisionQueryProvisionReservationsCreator Objects

```python
class Get_provisionQueryProvisionReservationsCreator(GraphQLObject)
```

#### username

Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.

## Get\_provisionQueryProvisionReservations Objects

```python
class Get_provisionQueryProvisionReservations(GraphQLObject)
```

#### reference

The Unique identifier of this Assignation

#### creator

This Reservations creator

#### app

This Reservations app

## Get\_provisionQueryProvision Objects

```python
class Get_provisionQueryProvision(GraphQLObject)
```

#### template

The Template for this Provision

#### bound

Is this Provision bound to a certain Agent?

#### reservations

The Provisions this reservation connects

## Get\_reservationQueryReservationTemplateRegistry Objects

```python
class Get_reservationQueryReservationTemplateRegistry(GraphQLObject)
```

#### app

The Associated App

#### user

The Associated App

## Get\_reservationQueryReservationTemplate Objects

```python
class Get_reservationQueryReservationTemplate(GraphQLObject)
```

#### registry

The associated registry for this Template

## Get\_reservationQueryReservationProvisions Objects

```python
class Get_reservationQueryReservationProvisions(GraphQLObject)
```

#### status

Current lifecycle of Provision

## Get\_reservationQueryReservationNode Objects

```python
class Get_reservationQueryReservationNode(Reserve,  GraphQLObject)
```

#### type

Function, generator? Check async Programming Textbook

#### name

The cleartext name of this Node

## Get\_reservationQueryReservation Objects

```python
class Get_reservationQueryReservation(GraphQLObject)
```

#### template

The template this reservation connects

#### provisions

The Provisions this reservation connects

#### title

A Short Hand Way to identify this reservation for you

#### status

Current lifecycle of Reservation

#### reference

The Unique identifier of this Assignation

#### node

The node this reservation connects

## Get\_agentQueryAgentRegistry Objects

```python
class Get_agentQueryAgentRegistry(GraphQLObject)
```

#### name

DEPRECATED Will be replaced in the future: : None

## Get\_agentQueryAgent Objects

```python
class Get_agentQueryAgent(GraphQLObject)
```

#### registry

The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users

#### name

This providers Name

#### atodos

```python
async def atodos(identifier: str, arkitekt: Arkitekt = None) -> AsyncIterator[TodosSubscriptionTodos]
```

todos



**Arguments**:

- `identifier` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TodosSubscriptionTodos` - The returned Mutation

#### todos

```python
def todos(identifier: str, arkitekt: Arkitekt = None) -> Iterator[TodosSubscriptionTodos]
```

todos



**Arguments**:

- `identifier` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TodosSubscriptionTodos` - The returned Mutation

#### awaiter

```python
async def awaiter(identifier: str, arkitekt: Arkitekt = None) -> AsyncIterator[WaiterSubscriptionReservations]
```

waiter



**Arguments**:

- `identifier` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `WaiterSubscriptionReservations` - The returned Mutation

#### waiter

```python
def waiter(identifier: str, arkitekt: Arkitekt = None) -> Iterator[WaiterSubscriptionReservations]
```

waiter



**Arguments**:

- `identifier` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `WaiterSubscriptionReservations` - The returned Mutation

#### atodolist

```python
async def atodolist(appGroup: str = None, arkitekt: Arkitekt = None) -> List[AssignationFragment]
```

todolist



**Arguments**:

- `appGroup` _ID, Optional_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `AssignationFragment` - The returned Mutation

#### todolist

```python
def todolist(appGroup: str = None, arkitekt: Arkitekt = None) -> List[AssignationFragment]
```

todolist



**Arguments**:

- `appGroup` _ID, Optional_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `AssignationFragment` - The returned Mutation

#### aget\_provision

```python
async def aget_provision(reference: str, arkitekt: Arkitekt = None) -> Get_provisionQueryProvision
```

get_provision



**Arguments**:

- `reference` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Get_provisionQueryProvision` - The returned Mutation

#### get\_provision

```python
def get_provision(reference: str, arkitekt: Arkitekt = None) -> Get_provisionQueryProvision
```

get_provision



**Arguments**:

- `reference` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Get_provisionQueryProvision` - The returned Mutation

#### aget\_reservation

```python
async def aget_reservation(reference: str, arkitekt: Arkitekt = None) -> Get_reservationQueryReservation
```

get_reservation



**Arguments**:

- `reference` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Get_reservationQueryReservation` - The returned Mutation

#### get\_reservation

```python
def get_reservation(reference: str, arkitekt: Arkitekt = None) -> Get_reservationQueryReservation
```

get_reservation



**Arguments**:

- `reference` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Get_reservationQueryReservation` - The returned Mutation

#### awaitlist

```python
async def awaitlist(appGroup: str = None, arkitekt: Arkitekt = None) -> List[ReservationFragment]
```

waitlist



**Arguments**:

- `appGroup` _ID, Optional_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `ReservationFragment` - The returned Mutation

#### waitlist

```python
def waitlist(appGroup: str = None, arkitekt: Arkitekt = None) -> List[ReservationFragment]
```

waitlist



**Arguments**:

- `appGroup` _ID, Optional_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `ReservationFragment` - The returned Mutation

#### afind

```python
async def afind(id: str = None, package: str = None, interface: str = None, template: str = None, q: QString = None, arkitekt: Arkitekt = None) -> NodeFragment
```

find

Asss

Is A query for all of these specials in the world


**Arguments**:

- `id` _ID, Optional_ - ID
- `package` _String, Optional_ - String
- `interface` _String, Optional_ - String
- `template` _ID, Optional_ - ID
- `q` _QString, Optional_ - QString
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `NodeFragment` - The returned Mutation

#### find

```python
def find(id: str = None, package: str = None, interface: str = None, template: str = None, q: QString = None, arkitekt: Arkitekt = None) -> NodeFragment
```

find

Asss

Is A query for all of these specials in the world


**Arguments**:

- `id` _ID, Optional_ - ID
- `package` _String, Optional_ - String
- `interface` _String, Optional_ - String
- `template` _ID, Optional_ - ID
- `q` _QString, Optional_ - QString
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `NodeFragment` - The returned Mutation

#### aget\_template

```python
async def aget_template(id: str, arkitekt: Arkitekt = None) -> TemplateFragment
```

get_template



**Arguments**:

- `id` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TemplateFragment` - The returned Mutation

#### get\_template

```python
def get_template(id: str, arkitekt: Arkitekt = None) -> TemplateFragment
```

get_template



**Arguments**:

- `id` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TemplateFragment` - The returned Mutation

#### aget\_agent

```python
async def aget_agent(id: str, arkitekt: Arkitekt = None) -> Get_agentQueryAgent
```

get_agent



**Arguments**:

- `id` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Get_agentQueryAgent` - The returned Mutation

#### get\_agent

```python
def get_agent(id: str, arkitekt: Arkitekt = None) -> Get_agentQueryAgent
```

get_agent



**Arguments**:

- `id` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Get_agentQueryAgent` - The returned Mutation

#### aassign

```python
async def aassign(reservation: str, args: List[Dict], kwargs: Dict = None, arkitekt: Arkitekt = None) -> AssignationFragment
```

assign



**Arguments**:

- `reservation` _ID_ - ID
- `args` _List[GenericScalar]_ - GenericScalar
- `kwargs` _GenericScalar, Optional_ - GenericScalar
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `AssignationFragment` - The returned Mutation

#### assign

```python
def assign(reservation: str, args: List[Dict], kwargs: Dict = None, arkitekt: Arkitekt = None) -> AssignationFragment
```

assign



**Arguments**:

- `reservation` _ID_ - ID
- `args` _List[GenericScalar]_ - GenericScalar
- `kwargs` _GenericScalar, Optional_ - GenericScalar
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `AssignationFragment` - The returned Mutation

#### aunassign

```python
async def aunassign(assignation: str, arkitekt: Arkitekt = None) -> AssignationFragment
```

unassign



**Arguments**:

- `assignation` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `AssignationFragment` - The returned Mutation

#### unassign

```python
def unassign(assignation: str, arkitekt: Arkitekt = None) -> AssignationFragment
```

unassign



**Arguments**:

- `assignation` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `AssignationFragment` - The returned Mutation

#### anegotiate

```python
async def anegotiate(arkitekt: Arkitekt = None) -> TranscriptFragment
```

negotiate

Create Node according to the specifications

**Arguments**:

- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TranscriptFragment` - The returned Mutation

#### negotiate

```python
def negotiate(arkitekt: Arkitekt = None) -> TranscriptFragment
```

negotiate

Create Node according to the specifications

**Arguments**:

- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TranscriptFragment` - The returned Mutation

#### areserve

```python
async def areserve(node: str = None, template: str = None, params: ReserveParamsInput = None, title: str = None, callbacks: List[str] = None, creator: str = None, appGroup: str = None, arkitekt: Arkitekt = None) -> ReservationFragment
```

reserve



**Arguments**:

- `node` _ID, Optional_ - ID
- `template` _ID, Optional_ - ID
- `params` _ReserveParamsInput, Optional_ - ReserveParamsInput
- `title` _String, Optional_ - String
- `callbacks` _List[Callback], Optional_ - Callback
- `creator` _ID, Optional_ - ID
- `appGroup` _ID, Optional_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `ReservationFragment` - The returned Mutation

#### reserve

```python
def reserve(node: str = None, template: str = None, params: ReserveParamsInput = None, title: str = None, callbacks: List[str] = None, creator: str = None, appGroup: str = None, arkitekt: Arkitekt = None) -> ReservationFragment
```

reserve



**Arguments**:

- `node` _ID, Optional_ - ID
- `template` _ID, Optional_ - ID
- `params` _ReserveParamsInput, Optional_ - ReserveParamsInput
- `title` _String, Optional_ - String
- `callbacks` _List[Callback], Optional_ - Callback
- `creator` _ID, Optional_ - ID
- `appGroup` _ID, Optional_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `ReservationFragment` - The returned Mutation

#### aunreserve

```python
async def aunreserve(id: str, arkitekt: Arkitekt = None) -> ReservationFragment
```

unreserve



**Arguments**:

- `id` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `ReservationFragment` - The returned Mutation

#### unreserve

```python
def unreserve(id: str, arkitekt: Arkitekt = None) -> ReservationFragment
```

unreserve



**Arguments**:

- `id` _ID_ - ID
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `ReservationFragment` - The returned Mutation

#### acreate\_node

```python
async def acreate_node(name: str, interface: str, args: List[ArgPortInput] = None, arkitekt: Arkitekt = None) -> NodeFragment
```

create_node

Create Node according to the specifications

**Arguments**:

- `name` _String_ - String
- `interface` _String_ - String
- `args` _List[ArgPortInput], Optional_ - ArgPortInput
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `NodeFragment` - The returned Mutation

#### create\_node

```python
def create_node(name: str, interface: str, args: List[ArgPortInput] = None, arkitekt: Arkitekt = None) -> NodeFragment
```

create_node

Create Node according to the specifications

**Arguments**:

- `name` _String_ - String
- `interface` _String_ - String
- `args` _List[ArgPortInput], Optional_ - ArgPortInput
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `NodeFragment` - The returned Mutation

#### adefine

```python
async def adefine(definition: DefinitionInput, arkitekt: Arkitekt = None) -> NodeFragment
```

define

Defines a node according to is definition

**Arguments**:

- `definition` _DefinitionInput_ - DefinitionInput
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `NodeFragment` - The returned Mutation

#### define

```python
def define(definition: DefinitionInput, arkitekt: Arkitekt = None) -> NodeFragment
```

define

Defines a node according to is definition

**Arguments**:

- `definition` _DefinitionInput_ - DefinitionInput
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `NodeFragment` - The returned Mutation

#### areset\_repository

```python
async def areset_repository(arkitekt: Arkitekt = None) -> Reset_repositoryMutationResetrepository
```

reset_repository

Create Repostiory

**Arguments**:

- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Reset_repositoryMutationResetrepository` - The returned Mutation

#### reset\_repository

```python
def reset_repository(arkitekt: Arkitekt = None) -> Reset_repositoryMutationResetrepository
```

reset_repository

Create Repostiory

**Arguments**:

- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `Reset_repositoryMutationResetrepository` - The returned Mutation

#### acreate\_template

```python
async def acreate_template(node: str, params: Dict = None, extensions: List[str] = None, version: str = None, arkitekt: Arkitekt = None) -> TemplateFragment
```

create_template



**Arguments**:

- `node` _ID_ - ID
- `params` _GenericScalar, Optional_ - GenericScalar
- `extensions` _List[String], Optional_ - String
- `version` _String, Optional_ - String
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TemplateFragment` - The returned Mutation

#### create\_template

```python
def create_template(node: str, params: Dict = None, extensions: List[str] = None, version: str = None, arkitekt: Arkitekt = None) -> TemplateFragment
```

create_template



**Arguments**:

- `node` _ID_ - ID
- `params` _GenericScalar, Optional_ - GenericScalar
- `extensions` _List[String], Optional_ - String
- `version` _String, Optional_ - String
- `arkitekt` _arkitekt.arkitekt.Arkitekt_ - The client we want to use (defaults to the currently active client)
  

**Returns**:

- `TemplateFragment` - The returned Mutation

