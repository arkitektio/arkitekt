from enum import Enum
from typing_extensions import Literal
from typing import Optional, Dict, Any, Iterator, AsyncIterator, List
from arkitekt.funcs import execute, aexecute, asubscribe, subscribe
from arkitekt.traits.node import Reserve
from pydantic import Field, BaseModel
from arkitekt.scalars import QString
from rath.scalars import ID
from arkitekt.rath import ArkitektRath


class AgentStatus(str, Enum):
    """An enumeration."""

    ACTIVE = "ACTIVE"
    "Active"
    DISCONNECTED = "DISCONNECTED"
    "Disconnected"
    VANILLA = "VANILLA"
    "Complete Vanilla Scenario after a forced restart of"


class LokAppGrantType(str, Enum):
    """An enumeration."""

    CLIENT_CREDENTIALS = "CLIENT_CREDENTIALS"
    "Backend (Client Credentials)"
    IMPLICIT = "IMPLICIT"
    "Implicit Grant"
    AUTHORIZATION_CODE = "AUTHORIZATION_CODE"
    "Authorization Code"
    PASSWORD = "PASSWORD"
    "Password"
    SESSION = "SESSION"
    "Django Session"


class NodeType(str, Enum):
    """An enumeration."""

    GENERATOR = "GENERATOR"
    "Generator"
    FUNCTION = "FUNCTION"
    "Function"


class PortType(str, Enum):
    INT = "INT"
    STRING = "STRING"
    STRUCTURE = "STRUCTURE"
    LIST = "LIST"
    BOOL = "BOOL"
    ENUM = "ENUM"
    DICT = "DICT"


class ProvisionMode(str, Enum):
    """An enumeration."""

    DEBUG = "DEBUG"
    "Debug Mode (Node might be constantly evolving)"
    PRODUCTION = "PRODUCTION"
    "Production Mode (Node might be constantly evolving)"


class ReservationStatus(str, Enum):
    """An enumeration."""

    ROUTING = "ROUTING"
    "Routing (Reservation has been requested but no Topic found yet)"
    PROVIDING = "PROVIDING"
    "Providing (Reservation required the provision of a new worker)"
    WAITING = "WAITING"
    "Waiting (We are waiting for any assignable Topic to come online)"
    REROUTING = "REROUTING"
    "Rerouting (State of provisions this reservation connects to have changed and require Retouring)"
    DISCONNECTED = "DISCONNECTED"
    "Disconnect (State of provisions this reservation connects to have changed and require Retouring)"
    DISCONNECT = "DISCONNECT"
    "Disconnect (State of provisions this reservation connects to have changed and require Retouring)"
    CANCELING = "CANCELING"
    "Cancelling (Reervation is currently being cancelled)"
    ACTIVE = "ACTIVE"
    "Active (Reservation is active and accepts assignments"
    ERROR = "ERROR"
    "Error (Reservation was not able to be performed (See StatusMessage)"
    ENDED = "ENDED"
    "Ended (Reservation was ended by the the Platform and is no longer active)"
    CANCELLED = "CANCELLED"
    "Cancelled (Reservation was cancelled by user and is no longer active)"
    CRITICAL = "CRITICAL"
    "Critical (Reservation failed with an Critical Error)"


class WaiterStatus(str, Enum):
    """An enumeration."""

    ACTIVE = "ACTIVE"
    "Active"
    DISCONNECTED = "DISCONNECTED"
    "Disconnected"
    VANILLA = "VANILLA"
    "Complete Vanilla Scenario after a forced restart of"


class AssignationStatus(str, Enum):
    """An enumeration."""

    PENDING = "PENDING"
    "Pending"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    "Acknowledged"
    RETURNED = "RETURNED"
    "Assignation Returned (Only for Functions)"
    DENIED = "DENIED"
    "Denied (Assingment was rejected)"
    ASSIGNED = "ASSIGNED"
    "Was able to assign to a pod"
    PROGRESS = "PROGRESS"
    "Progress (Assignment has current Progress)"
    RECEIVED = "RECEIVED"
    "Received (Assignment was received by an agent)"
    ERROR = "ERROR"
    "Error (Retrieable)"
    CRITICAL = "CRITICAL"
    "Critical Error (No Retries available)"
    CANCEL = "CANCEL"
    "Assinment is beeing cancelled"
    CANCELING = "CANCELING"
    "Cancelling (Assingment is currently being cancelled)"
    CANCELLED = "CANCELLED"
    "Assignment has been cancelled."
    YIELD = "YIELD"
    "Assignment yielded a value (only for Generators)"
    DONE = "DONE"
    "Assignment has finished"


class AssignationLogLevel(str, Enum):
    """An enumeration."""

    CRITICAL = "CRITICAL"
    "CRITICAL Level"
    INFO = "INFO"
    "INFO Level"
    DEBUG = "DEBUG"
    "DEBUG Level"
    ERROR = "ERROR"
    "ERROR Level"
    WARN = "WARN"
    "WARN Level"
    YIELD = "YIELD"
    "YIELD Level"
    CANCEL = "CANCEL"
    "Cancel Level"
    RETURN = "RETURN"
    "YIELD Level"
    DONE = "DONE"
    "Done Level"
    EVENT = "EVENT"
    "Event Level (only handled by plugins)"


class LogLevelInput(str, Enum):
    """An enumeration."""

    CRITICAL = "CRITICAL"
    "CRITICAL Level"
    INFO = "INFO"
    "INFO Level"
    DEBUG = "DEBUG"
    "DEBUG Level"
    ERROR = "ERROR"
    "ERROR Level"
    WARN = "WARN"
    "WARN Level"
    YIELD = "YIELD"
    "YIELD Level"
    CANCEL = "CANCEL"
    "Cancel Level"
    RETURN = "RETURN"
    "YIELD Level"
    DONE = "DONE"
    "Done Level"
    EVENT = "EVENT"
    "Event Level (only handled by plugins)"


class ReservationLogLevel(str, Enum):
    """An enumeration."""

    CRITICAL = "CRITICAL"
    "CRITICAL Level"
    INFO = "INFO"
    "INFO Level"
    DEBUG = "DEBUG"
    "DEBUG Level"
    ERROR = "ERROR"
    "ERROR Level"
    WARN = "WARN"
    "WARN Level"
    YIELD = "YIELD"
    "YIELD Level"
    CANCEL = "CANCEL"
    "Cancel Level"
    RETURN = "RETURN"
    "YIELD Level"
    DONE = "DONE"
    "Done Level"
    EVENT = "EVENT"
    "Event Level (only handled by plugins)"


class ProvisionAccess(str, Enum):
    """An enumeration."""

    EXCLUSIVE = "EXCLUSIVE"
    "This Topic is Only Accessible linkable for its creating User"
    EVERYONE = "EVERYONE"
    "Everyone can link to this Topic"


class ProvisionStatus(str, Enum):
    """An enumeration."""

    PENDING = "PENDING"
    "Pending (Request has been created and waits for its initial creation)"
    BOUND = "BOUND"
    "Bound (Provision was bound to an Agent)"
    PROVIDING = "PROVIDING"
    "Providing (Request has been send to its Agent and waits for Result"
    ACTIVE = "ACTIVE"
    "Active (Provision is currently active)"
    INACTIVE = "INACTIVE"
    "Inactive (Provision is currently not active)"
    CANCELING = "CANCELING"
    "Cancelling (Provisions is currently being cancelled)"
    LOST = "LOST"
    "Lost (Subscribers to this Topic have lost their connection)"
    RECONNECTING = "RECONNECTING"
    "Reconnecting (We are trying to Reconnect to this Topic)"
    DENIED = "DENIED"
    "Denied (Provision was rejected for this User)"
    ERROR = "ERROR"
    "Error (Reservation was not able to be performed (See StatusMessage)"
    CRITICAL = "CRITICAL"
    "Critical (Provision resulted in an critical system error)"
    ENDED = "ENDED"
    "Ended (Provision was cancelled by the Platform and will no longer create Topics)"
    CANCELLED = "CANCELLED"
    "Cancelled (Provision was cancelled by the User and will no longer create Topics)"


class ProvisionLogLevel(str, Enum):
    """An enumeration."""

    CRITICAL = "CRITICAL"
    "CRITICAL Level"
    INFO = "INFO"
    "INFO Level"
    DEBUG = "DEBUG"
    "DEBUG Level"
    ERROR = "ERROR"
    "ERROR Level"
    WARN = "WARN"
    "WARN Level"
    YIELD = "YIELD"
    "YIELD Level"
    CANCEL = "CANCEL"
    "Cancel Level"
    RETURN = "RETURN"
    "YIELD Level"
    DONE = "DONE"
    "Done Level"
    EVENT = "EVENT"
    "Event Level (only handled by plugins)"


class AssignationStatusInput(str, Enum):
    """An enumeration."""

    PENDING = "PENDING"
    "Pending"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    "Acknowledged"
    RETURNED = "RETURNED"
    "Assignation Returned (Only for Functions)"
    DENIED = "DENIED"
    "Denied (Assingment was rejected)"
    ASSIGNED = "ASSIGNED"
    "Was able to assign to a pod"
    PROGRESS = "PROGRESS"
    "Progress (Assignment has current Progress)"
    RECEIVED = "RECEIVED"
    "Received (Assignment was received by an agent)"
    ERROR = "ERROR"
    "Error (Retrieable)"
    CRITICAL = "CRITICAL"
    "Critical Error (No Retries available)"
    CANCEL = "CANCEL"
    "Assinment is beeing cancelled"
    CANCELING = "CANCELING"
    "Cancelling (Assingment is currently being cancelled)"
    CANCELLED = "CANCELLED"
    "Assignment has been cancelled."
    YIELD = "YIELD"
    "Assignment yielded a value (only for Generators)"
    DONE = "DONE"
    "Assignment has finished"


class ProvisionStatusInput(str, Enum):
    """An enumeration."""

    PENDING = "PENDING"
    "Pending (Request has been created and waits for its initial creation)"
    BOUND = "BOUND"
    "Bound (Provision was bound to an Agent)"
    PROVIDING = "PROVIDING"
    "Providing (Request has been send to its Agent and waits for Result"
    ACTIVE = "ACTIVE"
    "Active (Provision is currently active)"
    INACTIVE = "INACTIVE"
    "Inactive (Provision is currently not active)"
    CANCELING = "CANCELING"
    "Cancelling (Provisions is currently being cancelled)"
    DISCONNECTED = "DISCONNECTED"
    "Lost (Subscribers to this Topic have lost their connection)"
    RECONNECTING = "RECONNECTING"
    "Reconnecting (We are trying to Reconnect to this Topic)"
    DENIED = "DENIED"
    "Denied (Provision was rejected for this User)"
    ERROR = "ERROR"
    "Error (Reservation was not able to be performed (See StatusMessage)"
    CRITICAL = "CRITICAL"
    "Critical (Provision resulted in an critical system error)"
    ENDED = "ENDED"
    "Ended (Provision was cancelled by the Platform and will no longer create Topics)"
    CANCELLED = "CANCELLED"
    "Cancelled (Provision was cancelled by the User and will no longer create Topics)"


class RepositoryType(str, Enum):
    """An enumeration."""

    APP = "APP"
    "Repository that is hosted by an App"
    MIRROR = "MIRROR"
    "Repository mirrors online Repository"


class AgentStatusInput(str, Enum):
    """An enumeration."""

    ACTIVE = "ACTIVE"
    "Active"
    DISCONNECTED = "DISCONNECTED"
    "Disconnected"
    VANILLA = "VANILLA"
    "Complete Vanilla Scenario after a forced restart of"


class NodeTypeInput(str, Enum):
    """An enumeration."""

    GENERATOR = "GENERATOR"
    "Generator"
    FUNCTION = "FUNCTION"
    "Function"


class ReservationStatusInput(str, Enum):
    """An enumeration."""

    ROUTING = "ROUTING"
    "Routing (Reservation has been requested but no Topic found yet)"
    PROVIDING = "PROVIDING"
    "Providing (Reservation required the provision of a new worker)"
    WAITING = "WAITING"
    "Waiting (We are waiting for any assignable Topic to come online)"
    REROUTING = "REROUTING"
    "Rerouting (State of provisions this reservation connects to have changed and require Retouring)"
    DISCONNECTED = "DISCONNECTED"
    "Disconnect (State of provisions this reservation connects to have changed and require Retouring)"
    DISCONNECT = "DISCONNECT"
    "Disconnect (State of provisions this reservation connects to have changed and require Retouring)"
    CANCELING = "CANCELING"
    "Cancelling (Reervation is currently being cancelled)"
    ACTIVE = "ACTIVE"
    "Active (Reservation is active and accepts assignments"
    ERROR = "ERROR"
    "Error (Reservation was not able to be performed (See StatusMessage)"
    ENDED = "ENDED"
    "Ended (Reservation was ended by the the Platform and is no longer active)"
    CANCELLED = "CANCELLED"
    "Cancelled (Reservation was cancelled by user and is no longer active)"
    CRITICAL = "CRITICAL"
    "Critical (Reservation failed with an Critical Error)"


class AvailableModels(str, Enum):
    FACADE_AGENT = "FACADE_AGENT"
    FACADE_ASSIGNATION = "FACADE_ASSIGNATION"
    FACADE_NODE = "FACADE_NODE"
    FACADE_PROVISION = "FACADE_PROVISION"
    FACADE_REGISTRY = "FACADE_REGISTRY"
    FACADE_REPOSITORY = "FACADE_REPOSITORY"
    FACADE_RESERVATION = "FACADE_RESERVATION"
    FACADE_APPREPOSITORY = "FACADE_APPREPOSITORY"
    FACADE_MIRRORREPOSITORY = "FACADE_MIRRORREPOSITORY"
    FACADE_WAITER = "FACADE_WAITER"
    FACADE_TEMPLATE = "FACADE_TEMPLATE"
    FACADE_STRUCTURE = "FACADE_STRUCTURE"
    FACADE_RESERVATIONLOG = "FACADE_RESERVATIONLOG"
    FACADE_PROVISIONLOG = "FACADE_PROVISIONLOG"
    FACADE_ASSIGNATIONLOG = "FACADE_ASSIGNATIONLOG"


class PortTypeInput(str, Enum):
    INT = "INT"
    STRING = "STRING"
    STRUCTURE = "STRUCTURE"
    LIST = "LIST"
    BOOL = "BOOL"
    ENUM = "ENUM"
    DICT = "DICT"


class DefinitionInput(BaseModel):
    """A definition for a node"""

    description: Optional[str]
    "A description for the Node"
    name: str
    "The name of this template"
    args: Optional[List[Optional["ArgPortInput"]]]
    "The Args"
    kwargs: Optional[List[Optional["KwargPortInput"]]]
    "The Kwargs"
    returns: Optional[List[Optional["ReturnPortInput"]]]
    "The Returns"
    interfaces: Optional[List[Optional[str]]]
    "The Interfaces this node provides [eg. bridge, filter]"
    type: NodeTypeInput
    "The variety"
    interface: str
    "The Interface"
    package: Optional[str]
    "The Package"


class ArgPortInput(BaseModel):
    identifier: Optional[str]
    "The identifier"
    key: str
    "The key of the arg"
    name: Optional[str]
    "The name of this argument"
    label: Optional[str]
    "The name of this argument"
    type: PortTypeInput
    "The type of this argument"
    description: Optional[str]
    "The description of this argument"
    child: Optional["ChildPortInput"]
    "The child of this argument"
    widget: Optional["WidgetInput"]
    "The child of this argument"


class ChildPortInput(BaseModel):
    identifier: Optional[str]
    "The identifier"
    name: Optional[str]
    "The name of this port"
    type: Optional[str]
    "The type of this port"
    description: Optional[str]
    "The description of this port"


class WidgetInput(BaseModel):
    typename: str
    "type"
    query: Optional[str]
    "Do we have a possible"
    dependencies: Optional[List[Optional[str]]]
    "The dependencies of this port"
    max: Optional[int]
    "Max value for int widget"
    min: Optional[int]
    "Max value for int widget"
    placeholder: Optional[str]
    "Placeholder for any widget"


class KwargPortInput(BaseModel):
    identifier: Optional[str]
    "The identifier"
    key: str
    "The key of the arg"
    default: Optional[Any]
    "The key of the arg"
    label: Optional[str]
    "The name of this argument"
    name: Optional[str]
    "The name of this argument"
    type: PortTypeInput
    "The type of this argument"
    description: Optional[str]
    "The description of this argument"
    child: Optional[ChildPortInput]
    "The child of this argument"
    widget: Optional[WidgetInput]
    "The child of this argument"


class ReturnPortInput(BaseModel):
    identifier: Optional[str]
    "The identifier"
    key: str
    "The key of the arg"
    name: Optional[str]
    "The name of this argument"
    label: Optional[str]
    "The name of this argument"
    type: PortTypeInput
    "The type of this argument"
    description: Optional[str]
    "The description of this argument"
    child: Optional[ChildPortInput]
    "The child of this argument"
    widget: Optional["ReturnWidgetInput"]
    "The child of this argument"


class ReturnWidgetInput(BaseModel):
    typename: str
    "type"
    query: Optional[str]
    "Do we have a possible"


class ReserveParamsInput(BaseModel):
    auto_provide: Optional[bool] = Field(alias="autoProvide")
    "Do you want to autoprovide"
    auto_unprovide: Optional[bool] = Field(alias="autoUnprovide")
    "Do you want to auto_unprovide"
    registries: Optional[List[Optional[ID]]]
    "Registry thar are allowed"
    agents: Optional[List[Optional[ID]]]
    "Agents that are allowed"
    templates: Optional[List[Optional[ID]]]
    "Templates that can be selected"
    desired_instances: Optional[int] = Field(alias="desiredInstances")
    "The desired amount of Instances"
    minimal_instances: Optional[int] = Field(alias="minimalInstances")
    "The minimal amount of Instances"


class GroupAssignmentInput(BaseModel):
    permissions: List[Optional[str]]
    group: ID


class UserAssignmentInput(BaseModel):
    permissions: List[Optional[str]]
    user: str
    "The user email"


class AssignationFragmentParent(BaseModel):
    typename: Optional[Literal["Assignation"]] = Field(alias="__typename")
    id: ID


class AssignationFragment(BaseModel):
    typename: Optional[Literal["Assignation"]] = Field(alias="__typename")
    args: Optional[List[Optional[Any]]]
    kwargs: Optional[Dict]
    id: ID
    parent: Optional[AssignationFragmentParent]
    "The Assignations parent"
    id: ID
    status: AssignationStatus
    "Current lifecycle of Assignation"
    statusmessage: str
    "Clear Text status of the Assignation as for now"


class ProvisionFragmentTemplate(BaseModel):
    typename: Optional[Literal["Template"]] = Field(alias="__typename")
    id: ID
    node: "NodeFragment"
    "The node this template is implementatig"
    params: Optional[Dict]


class ProvisionFragment(BaseModel):
    typename: Optional[Literal["Provision"]] = Field(alias="__typename")
    id: ID
    status: ProvisionStatus
    "Current lifecycle of Provision"
    template: Optional[ProvisionFragmentTemplate]
    "The Template for this Provision"


class ChildPortNestedFragmentChild(BaseModel):
    typename: Optional[Literal["ChildPort"]] = Field(alias="__typename")
    type: Optional[PortType]
    "the type of input"


class ChildPortNestedFragment(BaseModel):
    typename: Optional[Literal["ChildPort"]] = Field(alias="__typename")
    type: Optional[PortType]
    "the type of input"
    child: Optional[ChildPortNestedFragmentChild]
    "The child"


class ChildPortFragment(BaseModel):
    typename: Optional[Literal["ChildPort"]] = Field(alias="__typename")
    type: Optional[PortType]
    "the type of input"
    identifier: Optional[str]
    "The corresponding Model"
    child: Optional[ChildPortNestedFragment]
    "The child"


class ArgPortFragment(BaseModel):
    typename: Optional[Literal["ArgPort"]] = Field(alias="__typename")
    key: str
    label: Optional[str]
    nullable: Optional[bool]
    description: Optional[str]
    "A description for this Port"
    type: Optional[PortType]
    "the type of input"
    identifier: Optional[str]
    "The corresponding Model"
    child: Optional[ChildPortFragment]
    "The child"


class KwargPortFragment(BaseModel):
    typename: Optional[Literal["KwargPort"]] = Field(alias="__typename")
    key: str
    label: Optional[str]
    type: Optional[PortType]
    "the type of input"
    description: Optional[str]
    "A description for this Port"
    nullable: Optional[bool]
    default: Optional[Any]
    identifier: Optional[str]
    "The corresponding Model"
    child: Optional[ChildPortFragment]
    "The child"


class ReturnPortFragment(BaseModel):
    typename: Optional[Literal["ReturnPort"]] = Field(alias="__typename")
    label: Optional[str]
    key: str
    nullable: Optional[bool]
    description: Optional[str]
    "A description for this Port"
    identifier: Optional[str]
    "The corresponding Model"
    type: Optional[PortType]
    "the type of input"
    child: Optional[ChildPortFragment]
    "The child"


class ReserveParamsFragment(BaseModel):
    typename: Optional[Literal["ReserveParams"]] = Field(alias="__typename")
    registries: Optional[List[Optional[ID]]]
    "Registry thar are allowed"
    minimal_instances: Optional[int] = Field(alias="minimalInstances")
    "The minimal amount of Instances"
    desired_instances: Optional[int] = Field(alias="desiredInstances")
    "The desired amount of Instances"


class ReservationFragmentNode(Reserve, BaseModel):
    typename: Optional[Literal["Node"]] = Field(alias="__typename")
    id: ID
    pure: bool
    "Is this function pure. e.g can we cache the result?"


class ReservationFragment(BaseModel):
    typename: Optional[Literal["Reservation"]] = Field(alias="__typename")
    id: ID
    statusmessage: str
    "Clear Text status of the Provision as for now"
    status: ReservationStatus
    "Current lifecycle of Reservation"
    node: Optional[ReservationFragmentNode]
    "The node this reservation connects"
    params: Optional[ReserveParamsFragment]


class NodeFragment(Reserve, BaseModel):
    typename: Optional[Literal["Node"]] = Field(alias="__typename")
    name: str
    "The cleartext name of this Node"
    interface: str
    "Interface (think Function)"
    package: str
    "Package (think Module)"
    description: str
    "A description for the Node"
    type: NodeType
    "Function, generator? Check async Programming Textbook"
    id: ID
    args: Optional[List[Optional[ArgPortFragment]]]
    kwargs: Optional[List[Optional[KwargPortFragment]]]
    returns: Optional[List[Optional[ReturnPortFragment]]]


class TemplateFragmentRegistryApp(BaseModel):
    typename: Optional[Literal["LokApp"]] = Field(alias="__typename")
    name: str


class TemplateFragmentRegistryUser(BaseModel):
    """A reflection on the real User"""

    typename: Optional[Literal["User"]] = Field(alias="__typename")
    username: str
    "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."


class TemplateFragmentRegistry(BaseModel):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    name: Optional[str]
    "DEPRECATED Will be replaced in the future: : None "
    app: Optional[TemplateFragmentRegistryApp]
    "The Associated App"
    user: Optional[TemplateFragmentRegistryUser]
    "The Associated App"


class TemplateFragment(BaseModel):
    typename: Optional[Literal["Template"]] = Field(alias="__typename")
    id: ID
    registry: TemplateFragmentRegistry
    "The associated registry for this Template"
    node: NodeFragment
    "The node this template is implementatig"
    params: Optional[Dict]


class TodosSubscriptionTodos(BaseModel):
    typename: Optional[Literal["TodoEvent"]] = Field(alias="__typename")
    create: Optional[AssignationFragment]
    update: Optional[AssignationFragment]
    delete: Optional[ID]


class TodosSubscription(BaseModel):
    todos: Optional[TodosSubscriptionTodos]

    class Arguments(BaseModel):
        identifier: ID

    class Meta:
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nsubscription todos($identifier: ID!) {\n  todos(identifier: $identifier) {\n    create {\n      ...Assignation\n    }\n    update {\n      ...Assignation\n    }\n    delete\n  }\n}"


class WaiterSubscriptionReservations(BaseModel):
    typename: Optional[Literal["ReservationsEvent"]] = Field(alias="__typename")
    create: Optional[ReservationFragment]
    update: Optional[ReservationFragment]
    delete: Optional[ID]


class WaiterSubscription(BaseModel):
    reservations: Optional[WaiterSubscriptionReservations]

    class Arguments(BaseModel):
        identifier: ID

    class Meta:
        document = "fragment ReserveParams on ReserveParams {\n  registries\n  minimalInstances\n  desiredInstances\n}\n\nfragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n  params {\n    ...ReserveParams\n  }\n}\n\nsubscription waiter($identifier: ID!) {\n  reservations(identifier: $identifier) {\n    create {\n      ...Reservation\n    }\n    update {\n      ...Reservation\n    }\n    delete\n  }\n}"


class TodolistQuery(BaseModel):
    todolist: Optional[List[Optional[AssignationFragment]]]

    class Arguments(BaseModel):
        app_group: Optional[ID] = None

    class Meta:
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nquery todolist($appGroup: ID) {\n  todolist(appGroup: $appGroup) {\n    ...Assignation\n  }\n}"


class Get_provisionQuery(BaseModel):
    provision: Optional[ProvisionFragment]

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "fragment ChildPortNested on ChildPort {\n  type\n  child {\n    type\n  }\n}\n\nfragment ChildPort on ChildPort {\n  type\n  identifier\n  child {\n    ...ChildPortNested\n  }\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  label\n  nullable\n  description\n  type\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  label\n  key\n  nullable\n  description\n  identifier\n  type\n  child {\n    ...ChildPort\n  }\n}\n\nfragment KwargPort on KwargPort {\n  key\n  label\n  type\n  description\n  nullable\n  default\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nfragment Provision on Provision {\n  id\n  status\n  template {\n    id\n    node {\n      ...Node\n    }\n    params\n  }\n}\n\nquery get_provision($id: ID!) {\n  provision(id: $id) {\n    ...Provision\n  }\n}"


class Get_reservationQueryReservationTemplateRegistryApp(BaseModel):
    typename: Optional[Literal["LokApp"]] = Field(alias="__typename")
    id: ID
    name: str


class Get_reservationQueryReservationTemplateRegistryUser(BaseModel):
    """A reflection on the real User"""

    typename: Optional[Literal["User"]] = Field(alias="__typename")
    id: ID
    email: str


class Get_reservationQueryReservationTemplateRegistry(BaseModel):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    app: Optional[Get_reservationQueryReservationTemplateRegistryApp]
    "The Associated App"
    user: Optional[Get_reservationQueryReservationTemplateRegistryUser]
    "The Associated App"


class Get_reservationQueryReservationTemplate(BaseModel):
    typename: Optional[Literal["Template"]] = Field(alias="__typename")
    id: ID
    registry: Get_reservationQueryReservationTemplateRegistry
    "The associated registry for this Template"


class Get_reservationQueryReservationProvisions(BaseModel):
    typename: Optional[Literal["Provision"]] = Field(alias="__typename")
    id: ID
    status: ProvisionStatus
    "Current lifecycle of Provision"


class Get_reservationQueryReservationNode(Reserve, BaseModel):
    typename: Optional[Literal["Node"]] = Field(alias="__typename")
    id: ID
    type: NodeType
    "Function, generator? Check async Programming Textbook"
    name: str
    "The cleartext name of this Node"


class Get_reservationQueryReservation(BaseModel):
    typename: Optional[Literal["Reservation"]] = Field(alias="__typename")
    id: ID
    template: Optional[Get_reservationQueryReservationTemplate]
    "The template this reservation connects"
    provisions: List[Get_reservationQueryReservationProvisions]
    "The Provisions this reservation connects"
    title: Optional[str]
    "A Short Hand Way to identify this reservation for you"
    status: ReservationStatus
    "Current lifecycle of Reservation"
    id: ID
    reference: str
    "The Unique identifier of this Assignation"
    node: Optional[Get_reservationQueryReservationNode]
    "The node this reservation connects"


class Get_reservationQuery(BaseModel):
    reservation: Optional[Get_reservationQueryReservation]

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "query get_reservation($id: ID!) {\n  reservation(id: $id) {\n    id\n    template {\n      id\n      registry {\n        app {\n          id\n          name\n        }\n        user {\n          id\n          email\n        }\n      }\n    }\n    provisions {\n      id\n      status\n    }\n    title\n    status\n    id\n    reference\n    node {\n      id\n      type\n      name\n    }\n  }\n}"


class WaitlistQuery(BaseModel):
    waitlist: Optional[List[Optional[ReservationFragment]]]

    class Arguments(BaseModel):
        app_group: Optional[ID] = None

    class Meta:
        document = "fragment ReserveParams on ReserveParams {\n  registries\n  minimalInstances\n  desiredInstances\n}\n\nfragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n  params {\n    ...ReserveParams\n  }\n}\n\nquery waitlist($appGroup: ID) {\n  waitlist(appGroup: $appGroup) {\n    ...Reservation\n  }\n}"


class FindQuery(BaseModel):
    node: Optional[NodeFragment]
    "Asss\n\n    Is A query for all of these specials in the world\n    "

    class Arguments(BaseModel):
        id: Optional[ID] = None
        package: Optional[str] = None
        interface: Optional[str] = None
        template: Optional[ID] = None
        q: Optional[QString] = None

    class Meta:
        document = "fragment ChildPortNested on ChildPort {\n  type\n  child {\n    type\n  }\n}\n\nfragment ChildPort on ChildPort {\n  type\n  identifier\n  child {\n    ...ChildPortNested\n  }\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  label\n  nullable\n  description\n  type\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment KwargPort on KwargPort {\n  key\n  label\n  type\n  description\n  nullable\n  default\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  label\n  key\n  nullable\n  description\n  identifier\n  type\n  child {\n    ...ChildPort\n  }\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nquery find($id: ID, $package: String, $interface: String, $template: ID, $q: QString) {\n  node(\n    id: $id\n    package: $package\n    interface: $interface\n    template: $template\n    q: $q\n  ) {\n    ...Node\n  }\n}"


class Get_templateQuery(BaseModel):
    template: Optional[TemplateFragment]

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "fragment ChildPortNested on ChildPort {\n  type\n  child {\n    type\n  }\n}\n\nfragment ChildPort on ChildPort {\n  type\n  identifier\n  child {\n    ...ChildPortNested\n  }\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  label\n  nullable\n  description\n  type\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  label\n  key\n  nullable\n  description\n  identifier\n  type\n  child {\n    ...ChildPort\n  }\n}\n\nfragment KwargPort on KwargPort {\n  key\n  label\n  type\n  description\n  nullable\n  default\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nfragment Template on Template {\n  id\n  registry {\n    name\n    app {\n      name\n    }\n    user {\n      username\n    }\n  }\n  node {\n    ...Node\n  }\n  params\n}\n\nquery get_template($id: ID!) {\n  template(id: $id) {\n    ...Template\n  }\n}"


class Get_agentQueryAgentRegistry(BaseModel):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    id: ID
    name: Optional[str]
    "DEPRECATED Will be replaced in the future: : None "


class Get_agentQueryAgent(BaseModel):
    typename: Optional[Literal["Agent"]] = Field(alias="__typename")
    registry: Optional[Get_agentQueryAgentRegistry]
    "The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users"
    name: str
    "This providers Name"
    identifier: str


class Get_agentQuery(BaseModel):
    agent: Optional[Get_agentQueryAgent]

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "query get_agent($id: ID!) {\n  agent(id: $id) {\n    registry {\n      id\n      name\n    }\n    name\n    identifier\n  }\n}"


class AssignMutation(BaseModel):
    assign: Optional[AssignationFragment]

    class Arguments(BaseModel):
        reservation: ID
        args: List[Optional[Dict]]
        kwargs: Optional[Dict] = None

    class Meta:
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nmutation assign($reservation: ID!, $args: [GenericScalar]!, $kwargs: GenericScalar) {\n  assign(reservation: $reservation, args: $args, kwargs: $kwargs) {\n    ...Assignation\n  }\n}"


class UnassignMutation(BaseModel):
    unassign: Optional[AssignationFragment]

    class Arguments(BaseModel):
        assignation: ID

    class Meta:
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nmutation unassign($assignation: ID!) {\n  unassign(assignation: $assignation) {\n    ...Assignation\n  }\n}"


class ReserveMutation(BaseModel):
    reserve: Optional[ReservationFragment]

    class Arguments(BaseModel):
        node: Optional[ID] = None
        template: Optional[ID] = None
        params: Optional[ReserveParamsInput] = None
        title: Optional[str] = None
        creator: Optional[ID] = None
        app_group: Optional[ID] = None

    class Meta:
        document = "fragment ReserveParams on ReserveParams {\n  registries\n  minimalInstances\n  desiredInstances\n}\n\nfragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n  params {\n    ...ReserveParams\n  }\n}\n\nmutation reserve($node: ID, $template: ID, $params: ReserveParamsInput, $title: String, $creator: ID, $appGroup: ID) {\n  reserve(\n    node: $node\n    template: $template\n    params: $params\n    title: $title\n    creator: $creator\n    appGroup: $appGroup\n  ) {\n    ...Reservation\n  }\n}"


class UnreserveMutation(BaseModel):
    unreserve: Optional[ReservationFragment]

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "fragment ReserveParams on ReserveParams {\n  registries\n  minimalInstances\n  desiredInstances\n}\n\nfragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n  params {\n    ...ReserveParams\n  }\n}\n\nmutation unreserve($id: ID!) {\n  unreserve(id: $id) {\n    ...Reservation\n  }\n}"


class DefineMutation(BaseModel):
    define: Optional[NodeFragment]
    "Defines a node according to is definition"

    class Arguments(BaseModel):
        definition: DefinitionInput

    class Meta:
        document = "fragment ChildPortNested on ChildPort {\n  type\n  child {\n    type\n  }\n}\n\nfragment ChildPort on ChildPort {\n  type\n  identifier\n  child {\n    ...ChildPortNested\n  }\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  label\n  nullable\n  description\n  type\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment KwargPort on KwargPort {\n  key\n  label\n  type\n  description\n  nullable\n  default\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  label\n  key\n  nullable\n  description\n  identifier\n  type\n  child {\n    ...ChildPort\n  }\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nmutation define($definition: DefinitionInput!) {\n  define(definition: $definition) {\n    ...Node\n  }\n}"


class Reset_repositoryMutationResetrepository(BaseModel):
    typename: Optional[Literal["ResetRepositoryReturn"]] = Field(alias="__typename")
    ok: Optional[bool]


class Reset_repositoryMutation(BaseModel):
    reset_repository: Optional[Reset_repositoryMutationResetrepository] = Field(
        alias="resetRepository"
    )
    "Create Repostiory"

    class Arguments(BaseModel):
        pass

    class Meta:
        document = "mutation reset_repository {\n  resetRepository {\n    ok\n  }\n}"


class Create_templateMutation(BaseModel):
    create_template: Optional[TemplateFragment] = Field(alias="createTemplate")

    class Arguments(BaseModel):
        node: ID
        params: Optional[Dict] = None
        extensions: Optional[List[Optional[str]]] = None
        version: Optional[str] = None

    class Meta:
        document = "fragment ChildPortNested on ChildPort {\n  type\n  child {\n    type\n  }\n}\n\nfragment ChildPort on ChildPort {\n  type\n  identifier\n  child {\n    ...ChildPortNested\n  }\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  label\n  nullable\n  description\n  type\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  label\n  key\n  nullable\n  description\n  identifier\n  type\n  child {\n    ...ChildPort\n  }\n}\n\nfragment KwargPort on KwargPort {\n  key\n  label\n  type\n  description\n  nullable\n  default\n  identifier\n  child {\n    ...ChildPort\n  }\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nfragment Template on Template {\n  id\n  registry {\n    name\n    app {\n      name\n    }\n    user {\n      username\n    }\n  }\n  node {\n    ...Node\n  }\n  params\n}\n\nmutation create_template($node: ID!, $params: GenericScalar, $extensions: [String], $version: String) {\n  createTemplate(\n    node: $node\n    params: $params\n    extensions: $extensions\n    version: $version\n  ) {\n    ...Template\n  }\n}"


class SlateMutation(BaseModel):
    slate: Optional[List[Optional[ID]]]

    class Arguments(BaseModel):
        identifier: str

    class Meta:
        document = "mutation slate($identifier: String!) {\n  slate(identifier: $identifier)\n}"


async def atodos(
    identifier: ID, rath: ArkitektRath = None
) -> AsyncIterator[Optional[TodosSubscriptionTodos]]:
    """todos



    Arguments:
        identifier (ID): identifier
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[TodosSubscriptionTodos]"""
    async for event in asubscribe(
        TodosSubscription, {"identifier": identifier}, rath=rath
    ):
        yield event.todos


def todos(
    identifier: ID, rath: ArkitektRath = None
) -> Iterator[Optional[TodosSubscriptionTodos]]:
    """todos



    Arguments:
        identifier (ID): identifier
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[TodosSubscriptionTodos]"""
    for event in subscribe(TodosSubscription, {"identifier": identifier}, rath=rath):
        yield event.todos


async def awaiter(
    identifier: ID, rath: ArkitektRath = None
) -> AsyncIterator[Optional[WaiterSubscriptionReservations]]:
    """waiter



    Arguments:
        identifier (ID): identifier
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[WaiterSubscriptionReservations]"""
    async for event in asubscribe(
        WaiterSubscription, {"identifier": identifier}, rath=rath
    ):
        yield event.reservations


def waiter(
    identifier: ID, rath: ArkitektRath = None
) -> Iterator[Optional[WaiterSubscriptionReservations]]:
    """waiter



    Arguments:
        identifier (ID): identifier
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[WaiterSubscriptionReservations]"""
    for event in subscribe(WaiterSubscription, {"identifier": identifier}, rath=rath):
        yield event.reservations


async def atodolist(
    app_group: Optional[ID] = None, rath: ArkitektRath = None
) -> Optional[List[Optional[AssignationFragment]]]:
    """todolist



    Arguments:
        app_group (Optional[ID], optional): appGroup.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[List[Optional[AssignationFragment]]]"""
    return (await aexecute(TodolistQuery, {"appGroup": app_group}, rath=rath)).todolist


def todolist(
    app_group: Optional[ID] = None, rath: ArkitektRath = None
) -> Optional[List[Optional[AssignationFragment]]]:
    """todolist



    Arguments:
        app_group (Optional[ID], optional): appGroup.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[List[Optional[AssignationFragment]]]"""
    return execute(TodolistQuery, {"appGroup": app_group}, rath=rath).todolist


async def aget_provision(
    id: ID, rath: ArkitektRath = None
) -> Optional[ProvisionFragment]:
    """get_provision



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[ProvisionFragment]"""
    return (await aexecute(Get_provisionQuery, {"id": id}, rath=rath)).provision


def get_provision(id: ID, rath: ArkitektRath = None) -> Optional[ProvisionFragment]:
    """get_provision



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[ProvisionFragment]"""
    return execute(Get_provisionQuery, {"id": id}, rath=rath).provision


async def aget_reservation(
    id: ID, rath: ArkitektRath = None
) -> Optional[Get_reservationQueryReservation]:
    """get_reservation



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[Get_reservationQueryReservation]"""
    return (await aexecute(Get_reservationQuery, {"id": id}, rath=rath)).reservation


def get_reservation(
    id: ID, rath: ArkitektRath = None
) -> Optional[Get_reservationQueryReservation]:
    """get_reservation



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[Get_reservationQueryReservation]"""
    return execute(Get_reservationQuery, {"id": id}, rath=rath).reservation


async def awaitlist(
    app_group: Optional[ID] = None, rath: ArkitektRath = None
) -> Optional[List[Optional[ReservationFragment]]]:
    """waitlist



    Arguments:
        app_group (Optional[ID], optional): appGroup.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[List[Optional[ReservationFragment]]]"""
    return (await aexecute(WaitlistQuery, {"appGroup": app_group}, rath=rath)).waitlist


def waitlist(
    app_group: Optional[ID] = None, rath: ArkitektRath = None
) -> Optional[List[Optional[ReservationFragment]]]:
    """waitlist



    Arguments:
        app_group (Optional[ID], optional): appGroup.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[List[Optional[ReservationFragment]]]"""
    return execute(WaitlistQuery, {"appGroup": app_group}, rath=rath).waitlist


async def afind(
    id: Optional[ID] = None,
    package: Optional[str] = None,
    interface: Optional[str] = None,
    template: Optional[ID] = None,
    q: Optional[QString] = None,
    rath: ArkitektRath = None,
) -> Optional[NodeFragment]:
    """find



    Arguments:
        id (Optional[ID], optional): id.
        package (Optional[str], optional): package.
        interface (Optional[str], optional): interface.
        template (Optional[ID], optional): template.
        q (Optional[QString], optional): q.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[NodeFragment]"""
    return (
        await aexecute(
            FindQuery,
            {
                "id": id,
                "package": package,
                "interface": interface,
                "template": template,
                "q": q,
            },
            rath=rath,
        )
    ).node


def find(
    id: Optional[ID] = None,
    package: Optional[str] = None,
    interface: Optional[str] = None,
    template: Optional[ID] = None,
    q: Optional[QString] = None,
    rath: ArkitektRath = None,
) -> Optional[NodeFragment]:
    """find



    Arguments:
        id (Optional[ID], optional): id.
        package (Optional[str], optional): package.
        interface (Optional[str], optional): interface.
        template (Optional[ID], optional): template.
        q (Optional[QString], optional): q.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[NodeFragment]"""
    return execute(
        FindQuery,
        {
            "id": id,
            "package": package,
            "interface": interface,
            "template": template,
            "q": q,
        },
        rath=rath,
    ).node


async def aget_template(
    id: ID, rath: ArkitektRath = None
) -> Optional[TemplateFragment]:
    """get_template



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[TemplateFragment]"""
    return (await aexecute(Get_templateQuery, {"id": id}, rath=rath)).template


def get_template(id: ID, rath: ArkitektRath = None) -> Optional[TemplateFragment]:
    """get_template



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[TemplateFragment]"""
    return execute(Get_templateQuery, {"id": id}, rath=rath).template


async def aget_agent(
    id: ID, rath: ArkitektRath = None
) -> Optional[Get_agentQueryAgent]:
    """get_agent



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[Get_agentQueryAgent]"""
    return (await aexecute(Get_agentQuery, {"id": id}, rath=rath)).agent


def get_agent(id: ID, rath: ArkitektRath = None) -> Optional[Get_agentQueryAgent]:
    """get_agent



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[Get_agentQueryAgent]"""
    return execute(Get_agentQuery, {"id": id}, rath=rath).agent


async def aassign(
    reservation: ID,
    args: List[Optional[Dict]],
    kwargs: Optional[Dict] = None,
    rath: ArkitektRath = None,
) -> Optional[AssignationFragment]:
    """assign



    Arguments:
        reservation (ID): reservation
        args (List[Optional[Dict]]): args
        kwargs (Optional[Dict], optional): kwargs.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[AssignationFragment]"""
    return (
        await aexecute(
            AssignMutation,
            {"reservation": reservation, "args": args, "kwargs": kwargs},
            rath=rath,
        )
    ).assign


def assign(
    reservation: ID,
    args: List[Optional[Dict]],
    kwargs: Optional[Dict] = None,
    rath: ArkitektRath = None,
) -> Optional[AssignationFragment]:
    """assign



    Arguments:
        reservation (ID): reservation
        args (List[Optional[Dict]]): args
        kwargs (Optional[Dict], optional): kwargs.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[AssignationFragment]"""
    return execute(
        AssignMutation,
        {"reservation": reservation, "args": args, "kwargs": kwargs},
        rath=rath,
    ).assign


async def aunassign(
    assignation: ID, rath: ArkitektRath = None
) -> Optional[AssignationFragment]:
    """unassign



    Arguments:
        assignation (ID): assignation
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[AssignationFragment]"""
    return (
        await aexecute(UnassignMutation, {"assignation": assignation}, rath=rath)
    ).unassign


def unassign(
    assignation: ID, rath: ArkitektRath = None
) -> Optional[AssignationFragment]:
    """unassign



    Arguments:
        assignation (ID): assignation
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[AssignationFragment]"""
    return execute(UnassignMutation, {"assignation": assignation}, rath=rath).unassign


async def areserve(
    node: Optional[ID] = None,
    template: Optional[ID] = None,
    params: Optional[ReserveParamsInput] = None,
    title: Optional[str] = None,
    creator: Optional[ID] = None,
    app_group: Optional[ID] = None,
    rath: ArkitektRath = None,
) -> Optional[ReservationFragment]:
    """reserve



    Arguments:
        node (Optional[ID], optional): node.
        template (Optional[ID], optional): template.
        params (Optional[ReserveParamsInput], optional): params.
        title (Optional[str], optional): title.
        creator (Optional[ID], optional): creator.
        app_group (Optional[ID], optional): appGroup.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[ReservationFragment]"""
    return (
        await aexecute(
            ReserveMutation,
            {
                "node": node,
                "template": template,
                "params": params,
                "title": title,
                "creator": creator,
                "appGroup": app_group,
            },
            rath=rath,
        )
    ).reserve


def reserve(
    node: Optional[ID] = None,
    template: Optional[ID] = None,
    params: Optional[ReserveParamsInput] = None,
    title: Optional[str] = None,
    creator: Optional[ID] = None,
    app_group: Optional[ID] = None,
    rath: ArkitektRath = None,
) -> Optional[ReservationFragment]:
    """reserve



    Arguments:
        node (Optional[ID], optional): node.
        template (Optional[ID], optional): template.
        params (Optional[ReserveParamsInput], optional): params.
        title (Optional[str], optional): title.
        creator (Optional[ID], optional): creator.
        app_group (Optional[ID], optional): appGroup.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[ReservationFragment]"""
    return execute(
        ReserveMutation,
        {
            "node": node,
            "template": template,
            "params": params,
            "title": title,
            "creator": creator,
            "appGroup": app_group,
        },
        rath=rath,
    ).reserve


async def aunreserve(
    id: ID, rath: ArkitektRath = None
) -> Optional[ReservationFragment]:
    """unreserve



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[ReservationFragment]"""
    return (await aexecute(UnreserveMutation, {"id": id}, rath=rath)).unreserve


def unreserve(id: ID, rath: ArkitektRath = None) -> Optional[ReservationFragment]:
    """unreserve



    Arguments:
        id (ID): id
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[ReservationFragment]"""
    return execute(UnreserveMutation, {"id": id}, rath=rath).unreserve


async def adefine(
    definition: DefinitionInput, rath: ArkitektRath = None
) -> Optional[NodeFragment]:
    """define



    Arguments:
        definition (DefinitionInput): definition
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[NodeFragment]"""
    return (
        await aexecute(DefineMutation, {"definition": definition}, rath=rath)
    ).define


def define(
    definition: DefinitionInput, rath: ArkitektRath = None
) -> Optional[NodeFragment]:
    """define



    Arguments:
        definition (DefinitionInput): definition
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[NodeFragment]"""
    return execute(DefineMutation, {"definition": definition}, rath=rath).define


async def areset_repository(
    rath: ArkitektRath = None,
) -> Optional[Reset_repositoryMutationResetrepository]:
    """reset_repository



    Arguments:
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[Reset_repositoryMutationResetrepository]"""
    return (await aexecute(Reset_repositoryMutation, {}, rath=rath)).reset_repository


def reset_repository(
    rath: ArkitektRath = None,
) -> Optional[Reset_repositoryMutationResetrepository]:
    """reset_repository



    Arguments:
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[Reset_repositoryMutationResetrepository]"""
    return execute(Reset_repositoryMutation, {}, rath=rath).reset_repository


async def acreate_template(
    node: ID,
    params: Optional[Dict] = None,
    extensions: Optional[List[Optional[str]]] = None,
    version: Optional[str] = None,
    rath: ArkitektRath = None,
) -> Optional[TemplateFragment]:
    """create_template



    Arguments:
        node (ID): node
        params (Optional[Dict], optional): params.
        extensions (Optional[List[Optional[str]]], optional): extensions.
        version (Optional[str], optional): version.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[TemplateFragment]"""
    return (
        await aexecute(
            Create_templateMutation,
            {
                "node": node,
                "params": params,
                "extensions": extensions,
                "version": version,
            },
            rath=rath,
        )
    ).create_template


def create_template(
    node: ID,
    params: Optional[Dict] = None,
    extensions: Optional[List[Optional[str]]] = None,
    version: Optional[str] = None,
    rath: ArkitektRath = None,
) -> Optional[TemplateFragment]:
    """create_template



    Arguments:
        node (ID): node
        params (Optional[Dict], optional): params.
        extensions (Optional[List[Optional[str]]], optional): extensions.
        version (Optional[str], optional): version.
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[TemplateFragment]"""
    return execute(
        Create_templateMutation,
        {"node": node, "params": params, "extensions": extensions, "version": version},
        rath=rath,
    ).create_template


async def aslate(
    identifier: str, rath: ArkitektRath = None
) -> Optional[List[Optional[ID]]]:
    """slate


     slate: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.


    Arguments:
        identifier (str): identifier
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[List[Optional[ID]]]"""
    return (await aexecute(SlateMutation, {"identifier": identifier}, rath=rath)).slate


def slate(identifier: str, rath: ArkitektRath = None) -> Optional[List[Optional[ID]]]:
    """slate


     slate: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.


    Arguments:
        identifier (str): identifier
        rath (arkitekt.rath.ArkitektRath, optional): The arkitekt rath client

    Returns:
        Optional[List[Optional[ID]]]"""
    return execute(SlateMutation, {"identifier": identifier}, rath=rath).slate


ProvisionFragmentTemplate.update_forward_refs()
ArgPortInput.update_forward_refs()
DefinitionInput.update_forward_refs()
ReturnPortInput.update_forward_refs()
