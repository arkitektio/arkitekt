from enum import Enum
from typing import Literal, List, Union, Any, Optional, Iterator, AsyncIterator, Dict
from arkitekt.operation import GraphQLQuery, GraphQLMutation, GraphQLSubscription
from turms.types.object import GraphQLObject, GraphQLInputObject
from arkitekt.mixins.ports import (
    StringExpander,
    BoolExpander,
    ListExpander,
    StructureExpander,
    IntExpander,
)
from pydantic import Field
from arkitekt.mixins.node import NodeMixin
from arkitekt.scalars import QString


class NodeType(str, Enum):
    """An enumeration."""

    GENERATOR = "GENERATOR"
    "Generator"
    FUNCTION = "FUNCTION"
    "Function"


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


class RepositoryType(str, Enum):
    """An enumeration."""

    APP = "APP"
    "Repository that is hosted by an App"
    MIRROR = "MIRROR"
    "Repository mirrors online Repository"


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


class AgentStatus(str, Enum):
    """An enumeration."""

    ACTIVE = "ACTIVE"
    "Active"
    DISCONNECTED = "DISCONNECTED"
    "Disconnected"
    VANILLA = "VANILLA"
    "Complete Vanilla Scenario after a forced restart of"


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


class NodeTypeInput(str, Enum):
    """An enumeration."""

    GENERATOR = "GENERATOR"
    "Generator"
    FUNCTION = "FUNCTION"
    "Function"


class AgentStatusInput(str, Enum):
    """An enumeration."""

    ACTIVE = "ACTIVE"
    "Active"
    DISCONNECTED = "DISCONNECTED"
    "Disconnected"
    VANILLA = "VANILLA"
    "Complete Vanilla Scenario after a forced restart of"


class StructureBound(str, Enum):
    """An enumeration."""

    AGENT = "AGENT"
    "Bound to one Agent (Instance Dependented)"
    REGISTRY = "REGISTRY"
    "Registry (User Dependent)"
    APP = "APP"
    "Bound to one Application (User independent)"
    GLOBAL = "GLOBAL"
    "Unbound and usable for every application"


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


class BoundTypeInput(str, Enum):
    """An enumeration."""

    AGENT = "AGENT"
    "Bound to one Agent (Instance Dependented)"
    REGISTRY = "REGISTRY"
    "Registry (User Dependent)"
    APP = "APP"
    "Bound to one Application (User independent)"
    GLOBAL = "GLOBAL"
    "Unbound and usable for every application"


class WardTypes(str, Enum):
    GRAPHQL = "GRAPHQL"
    REST = "REST"


class PostmanProtocol(str, Enum):
    WEBSOCKET = "WEBSOCKET"
    KAFKA = "KAFKA"
    RABBITMQ = "RABBITMQ"


class ArgPortInput(GraphQLInputObject):
    key: Optional[str]
    "The Key"
    type: Optional[str]
    "the type of input"
    typename: Optional[str]
    "the type of input"
    description: Optional[str]
    "A description for this Port"
    label: Optional[str]
    "The Label of this inport"
    identifier: Optional[str]
    "The corresponding Model"
    widget: Optional["WidgetInput"]
    "Which Widget to use to render Port in User Interfaces"
    bound: Optional["BoundTypeInput"]
    "Where should this be bound to (only Structures"
    child: Optional["ArgPortInput"]
    "The Child of this"
    transpile: Optional[str]
    "The corresponding Model"
    options: Optional[Dict]
    "Options for an Enum"


class WidgetInput(GraphQLInputObject):
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


class KwargPortInput(GraphQLInputObject):
    key: Optional[str]
    "The Key"
    type: Optional[str]
    "the type of input"
    typename: Optional[str]
    "the type of input"
    description: Optional[str]
    "A description for this Port"
    label: Optional[str]
    "The Label of this inport"
    defaultDict: Optional[Dict]
    "Does this field have a specific value"
    defaultOption: Optional[Dict]
    "Does this field have a specific value"
    defaultInt: Optional[int]
    "Does this field have a specific value"
    defaultBool: Optional[bool]
    "Does this field have a specific value"
    defaultFloat: Optional[float]
    "Does this field have a specific value"
    defaultID: Optional[str]
    "Does this field have a specific value"
    defaultString: Optional[str]
    "Does this field have a specific value"
    defaultList: Optional[List[Optional[Dict]]]
    "Does this field have a specific value"
    identifier: Optional[str]
    "The corresponding Model"
    widget: Optional["WidgetInput"]
    "Which Widget to use to render Port in User Interfaces"
    bound: Optional["BoundTypeInput"]
    "Where should this be bound to (only Structures"
    child: Optional["KwargPortInput"]
    "The Child of this"
    transpile: Optional[str]
    "The corresponding Model"
    options: Optional[Dict]
    "Options for an Enum"


class ReturnPortInput(GraphQLInputObject):
    key: Optional[str]
    "The Key"
    type: Optional[str]
    "the type of input"
    typename: Optional[str]
    "the type of input"
    description: Optional[str]
    "A description for this Port"
    bound: Optional["BoundTypeInput"]
    "Where should this be bound to (only Structures"
    label: Optional[str]
    "The Label of this Outport"
    identifier: Optional[str]
    "The corresponding Model"
    child: Optional["ReturnPortInput"]
    "The Child of this"
    transpile: Optional[str]
    "The corresponding Model"


class DefinitionInput(GraphQLInputObject):
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
    type: Optional["NodeTypeInput"]
    "The variety"
    interface: str
    "The Interface"
    package: Optional[str]
    "The Package"


class ReserveParamsInput(GraphQLInputObject):
    autoProvide: Optional[bool]
    "Do you want to autoprovide"
    autoUnprovide: Optional[bool]
    "Do you want to auto_unprovide"
    registries: Optional[List[Optional[str]]]
    "Registry thar are allowed"
    agents: Optional[List[Optional[str]]]
    "Agents that are allowed"
    templates: Optional[List[Optional[str]]]
    "Templates that can be selected"
    desiredInstances: Optional[int]
    "The desired amount of Instances"
    minimalInstances: Optional[int]
    "The minimal amount of Instances"


KwargPortInput.update_forward_refs()
ReturnPortInput.update_forward_refs()
ArgPortInput.update_forward_refs()


class AssignationFragmentParent(GraphQLObject):
    typename: Optional[Literal["Assignation"]] = Field(alias="__typename")
    id: str


class AssignationFragment(GraphQLObject):
    typename: Optional[Literal["Assignation"]] = Field(alias="__typename")
    args: Optional[List[Optional[Any]]]
    kwargs: Optional[Dict]
    id: str
    parent: Optional[AssignationFragmentParent]
    "The Assignations parent"
    id: str
    status: AssignationStatus
    "Current lifecycle of Assignation"
    statusmessage: str
    "Clear Text status of the Assignation as for now"


class TranscriptFragmentPostman(GraphQLObject):
    typename: Optional[Literal["PostmanSettings"]] = Field(alias="__typename")
    type: Optional[PostmanProtocol]
    "The communication protocol"
    kwargs: Optional[Dict]
    "kwargs for your postman"


class TranscriptFragment(GraphQLObject):
    typename: Optional[Literal["Transcript"]] = Field(alias="__typename")
    postman: Optional[TranscriptFragmentPostman]


class StringArgPortFragment(StringExpander, GraphQLObject):
    typename: Optional[Literal["StringArgPort"]] = Field(alias="__typename")
    key: Optional[str]


class IntArgPortFragment(IntExpander, GraphQLObject):
    typename: Optional[Literal["IntArgPort"]] = Field(alias="__typename")
    key: Optional[str]


class StructureArgPortFragment(StructureExpander, GraphQLObject):
    typename: Optional[Literal["StructureArgPort"]] = Field(alias="__typename")
    key: Optional[str]
    identifier: Optional[str]
    "The identifier of this Model"


class ListArgPortFragmentChildBase(GraphQLObject):
    typename: Optional[str] = Field(alias="__typename")


class ListArgPortFragmentChildStructureArgPortFragment(
    StructureExpander, ListArgPortFragmentChildBase
):
    typename: Optional[Literal["StructureArgPort"]] = Field(alias="__typename")
    identifier: Optional[str]
    "The identifier of this Model"


class ListArgPortFragment(ListExpander, GraphQLObject):
    typename: Optional[Literal["ListArgPort"]] = Field(alias="__typename")
    key: Optional[str]
    child: Optional[
        Union[
            ListArgPortFragmentChildStructureArgPortFragment,
            ListArgPortFragmentChildBase,
        ]
    ]
    "The child"


class DictArgPortFragmentChildBase(GraphQLObject):
    typename: Optional[str] = Field(alias="__typename")


class DictArgPortFragmentChildStructureArgPortFragment(
    StructureExpander, DictArgPortFragmentChildBase
):
    typename: Optional[Literal["StructureArgPort"]] = Field(alias="__typename")
    identifier: Optional[str]
    "The identifier of this Model"


class DictArgPortFragment(GraphQLObject):
    typename: Optional[Literal["DictArgPort"]] = Field(alias="__typename")
    key: Optional[str]
    child: Optional[
        Union[
            DictArgPortFragmentChildStructureArgPortFragment,
            DictArgPortFragmentChildBase,
        ]
    ]
    "The child"


class DictKwargPortFragment(GraphQLObject):
    typename: Optional[Literal["DictKwargPort"]] = Field(alias="__typename")
    key: Optional[str]
    defaultDict: Optional[Dict]
    "TheList"


class BoolKwargPortFragment(BoolExpander, GraphQLObject):
    typename: Optional[Literal["BoolKwargPort"]] = Field(alias="__typename")
    key: Optional[str]
    defaultBool: Optional[bool]
    "Default value"


class IntKwargPortFragment(IntExpander, GraphQLObject):
    typename: Optional[Literal["IntKwargPort"]] = Field(alias="__typename")
    key: Optional[str]
    defaultInt: Optional[int]
    "Default value"


class StringKwargPortFragment(StringExpander, GraphQLObject):
    typename: Optional[Literal["StringKwargPort"]] = Field(alias="__typename")
    key: Optional[str]
    defaultString: Optional[str]
    "Default value"


class ListKwargPortFragmentChildBase(GraphQLObject):
    typename: Optional[str] = Field(alias="__typename")


class ListKwargPortFragmentChildStructureKwargPortFragment(
    StructureExpander, ListKwargPortFragmentChildBase
):
    typename: Optional[Literal["StructureKwargPort"]] = Field(alias="__typename")
    identifier: Optional[str]
    "The identifier of this Model"


class ListKwargPortFragment(ListExpander, GraphQLObject):
    typename: Optional[Literal["ListKwargPort"]] = Field(alias="__typename")
    key: Optional[str]
    child: Optional[
        Union[
            ListKwargPortFragmentChildStructureKwargPortFragment,
            ListKwargPortFragmentChildBase,
        ]
    ]
    "The child"
    defaultList: Optional[List[Optional[Dict]]]
    "TheList"


class ListReturnPortFragmentChildBase(GraphQLObject):
    typename: Optional[str] = Field(alias="__typename")


class ListReturnPortFragmentChildStructureReturnPortFragment(
    StructureExpander, ListReturnPortFragmentChildBase
):
    typename: Optional[Literal["StructureReturnPort"]] = Field(alias="__typename")
    identifier: Optional[str]
    "The identifier of this Model"


class ListReturnPortFragment(ListExpander, GraphQLObject):
    typename: Optional[Literal["ListReturnPort"]] = Field(alias="__typename")
    key: Optional[str]
    child: Optional[
        Union[
            ListReturnPortFragmentChildStructureReturnPortFragment,
            ListReturnPortFragmentChildBase,
        ]
    ]
    "The child"


class StructureReturnPortFragment(StructureExpander, GraphQLObject):
    typename: Optional[Literal["StructureReturnPort"]] = Field(alias="__typename")
    __typename: str
    "The name of the current Object type at runtime."
    key: Optional[str]
    identifier: Optional[str]
    "The identifier of this Model"


class StringReturnPortFragment(StringExpander, GraphQLObject):
    typename: Optional[Literal["StringReturnPort"]] = Field(alias="__typename")
    __typename: str
    "The name of the current Object type at runtime."
    key: Optional[str]


class IntReturnPortFragment(IntExpander, GraphQLObject):
    typename: Optional[Literal["IntReturnPort"]] = Field(alias="__typename")
    __typename: str
    "The name of the current Object type at runtime."
    key: Optional[str]


class ReturnPortFragmentBase(GraphQLObject):
    key: Optional[str]
    description: Optional[str]


class ReturnPortFragmentBaseListReturnPort(
    ListReturnPortFragment, ReturnPortFragmentBase
):
    pass


class ReturnPortFragmentBaseStructureReturnPort(
    StructureReturnPortFragment, ReturnPortFragmentBase
):
    pass


class ReturnPortFragmentBaseStringReturnPort(
    StringReturnPortFragment, ReturnPortFragmentBase
):
    pass


class ReturnPortFragmentBaseIntReturnPort(
    IntReturnPortFragment, ReturnPortFragmentBase
):
    pass


ReturnPortFragment = Union[
    ReturnPortFragmentBaseListReturnPort,
    ReturnPortFragmentBaseStructureReturnPort,
    ReturnPortFragmentBaseStringReturnPort,
    ReturnPortFragmentBaseIntReturnPort,
    ReturnPortFragmentBase,
]


class KwargPortFragmentBase(GraphQLObject):
    key: Optional[str]
    description: Optional[str]


class KwargPortFragmentBaseDictKwargPort(DictKwargPortFragment, KwargPortFragmentBase):
    pass


class KwargPortFragmentBaseBoolKwargPort(BoolKwargPortFragment, KwargPortFragmentBase):
    pass


class KwargPortFragmentBaseIntKwargPort(IntKwargPortFragment, KwargPortFragmentBase):
    pass


class KwargPortFragmentBaseListKwargPort(ListKwargPortFragment, KwargPortFragmentBase):
    pass


class KwargPortFragmentBaseStringKwargPort(
    StringKwargPortFragment, KwargPortFragmentBase
):
    pass


KwargPortFragment = Union[
    KwargPortFragmentBaseDictKwargPort,
    KwargPortFragmentBaseBoolKwargPort,
    KwargPortFragmentBaseIntKwargPort,
    KwargPortFragmentBaseListKwargPort,
    KwargPortFragmentBaseStringKwargPort,
    KwargPortFragmentBase,
]


class ArgPortFragmentBase(GraphQLObject):
    key: Optional[str]
    description: Optional[str]


class ArgPortFragmentBaseStringArgPort(StringArgPortFragment, ArgPortFragmentBase):
    pass


class ArgPortFragmentBaseStructureArgPort(
    StructureArgPortFragment, ArgPortFragmentBase
):
    pass


class ArgPortFragmentBaseListArgPort(ListArgPortFragment, ArgPortFragmentBase):
    pass


class ArgPortFragmentBaseIntArgPort(IntArgPortFragment, ArgPortFragmentBase):
    pass


class ArgPortFragmentBaseDictArgPort(DictArgPortFragment, ArgPortFragmentBase):
    pass


ArgPortFragment = Union[
    ArgPortFragmentBaseStringArgPort,
    ArgPortFragmentBaseStructureArgPort,
    ArgPortFragmentBaseListArgPort,
    ArgPortFragmentBaseIntArgPort,
    ArgPortFragmentBaseDictArgPort,
    ArgPortFragmentBase,
]


class ReservationFragmentNode(NodeMixin, GraphQLObject):
    typename: Optional[Literal["Node"]] = Field(alias="__typename")
    id: str
    pure: bool
    "Is this function pure. e.g can we cache the result?"


class ReservationFragment(GraphQLObject):
    typename: Optional[Literal["Reservation"]] = Field(alias="__typename")
    id: str
    statusmessage: str
    "Clear Text status of the Provision as for now"
    status: ReservationStatus
    "Current lifecycle of Reservation"
    node: Optional[ReservationFragmentNode]
    "The node this reservation connects"


class NodeFragment(NodeMixin, GraphQLObject):
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
    id: str
    args: Optional[List[Optional[ArgPortFragment]]]
    kwargs: Optional[List[Optional[KwargPortFragment]]]
    returns: Optional[List[Optional[ReturnPortFragment]]]


class TemplateFragmentRegistryApp(GraphQLObject):
    typename: Optional[Literal["LokApp"]] = Field(alias="__typename")
    name: str


class TemplateFragmentRegistryUser(GraphQLObject):
    typename: Optional[Literal["LokUser"]] = Field(alias="__typename")
    username: str
    "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."


class TemplateFragmentRegistry(GraphQLObject):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    app: Optional[TemplateFragmentRegistryApp]
    "The Associated App"
    user: Optional[TemplateFragmentRegistryUser]
    "The Associated App"


class TemplateFragment(GraphQLObject):
    typename: Optional[Literal["Template"]] = Field(alias="__typename")
    id: str
    registry: TemplateFragmentRegistry
    "The associated registry for this Template"
    node: NodeFragment
    "The node this template is implementatig"


class TodosSubscriptionTodos(GraphQLObject):
    typename: Optional[Literal["TodoEvent"]] = Field(alias="__typename")
    create: Optional[AssignationFragment]
    update: Optional[AssignationFragment]
    delete: Optional[str]


class TodosSubscription(GraphQLSubscription):
    todos: Optional[TodosSubscriptionTodos]

    class Meta:
        domain = "arkitekt"
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nsubscription todos($identifier: ID!) {\n  todos(identifier: $identifier) {\n    create {\n      ...Assignation\n    }\n    update {\n      ...Assignation\n    }\n    delete\n  }\n}"


class WaiterSubscriptionWaiter(GraphQLObject):
    typename: Optional[Literal["WaiterEvent"]] = Field(alias="__typename")
    create: Optional[ReservationFragment]
    update: Optional[ReservationFragment]
    delete: Optional[str]


class WaiterSubscription(GraphQLSubscription):
    waiter: Optional[WaiterSubscriptionWaiter]

    class Meta:
        domain = "arkitekt"
        document = "fragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n}\n\nsubscription waiter($identifier: ID!) {\n  waiter(identifier: $identifier) {\n    create {\n      ...Reservation\n    }\n    update {\n      ...Reservation\n    }\n    delete\n  }\n}"


class TodolistQuery(GraphQLQuery):
    todolist: Optional[List[Optional[AssignationFragment]]]

    class Meta:
        domain = "arkitekt"
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nquery todolist($appGroup: ID) {\n  todolist(appGroup: $appGroup) {\n    ...Assignation\n  }\n}"


class Get_provisionQueryProvisionTemplateNode(NodeMixin, GraphQLObject):
    typename: Optional[Literal["Node"]] = Field(alias="__typename")
    name: str
    "The cleartext name of this Node"


class Get_provisionQueryProvisionTemplateRegistryApp(GraphQLObject):
    typename: Optional[Literal["LokApp"]] = Field(alias="__typename")
    name: str


class Get_provisionQueryProvisionTemplateRegistry(GraphQLObject):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    app: Optional[Get_provisionQueryProvisionTemplateRegistryApp]
    "The Associated App"


class Get_provisionQueryProvisionTemplate(GraphQLObject):
    typename: Optional[Literal["Template"]] = Field(alias="__typename")
    id: str
    node: Get_provisionQueryProvisionTemplateNode
    "The node this template is implementatig"
    registry: Get_provisionQueryProvisionTemplateRegistry
    "The associated registry for this Template"
    extensions: Optional[List[Optional[str]]]
    "The extentions of this template"


class Get_provisionQueryProvisionBoundRegistry(GraphQLObject):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    id: str
    name: str
    "A name for this registzry"


class Get_provisionQueryProvisionBound(GraphQLObject):
    typename: Optional[Literal["Agent"]] = Field(alias="__typename")
    registry: Optional[Get_provisionQueryProvisionBoundRegistry]
    "The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users"
    name: str
    "This providers Name"
    identifier: str


class Get_provisionQueryProvisionReservationsCreator(GraphQLObject):
    typename: Optional[Literal["LokUser"]] = Field(alias="__typename")
    username: str
    "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."


class Get_provisionQueryProvisionReservationsApp(GraphQLObject):
    typename: Optional[Literal["LokApp"]] = Field(alias="__typename")
    name: str


class Get_provisionQueryProvisionReservations(GraphQLObject):
    typename: Optional[Literal["Reservation"]] = Field(alias="__typename")
    id: str
    reference: str
    "The Unique identifier of this Assignation"
    creator: Optional[Get_provisionQueryProvisionReservationsCreator]
    "This Reservations creator"
    app: Optional[Get_provisionQueryProvisionReservationsApp]
    "This Reservations app"


class Get_provisionQueryProvision(GraphQLObject):
    typename: Optional[Literal["Provision"]] = Field(alias="__typename")
    template: Optional[Get_provisionQueryProvisionTemplate]
    "The Template for this Provision"
    bound: Optional[Get_provisionQueryProvisionBound]
    "Is this Provision bound to a certain Agent?"
    reservations: List[Get_provisionQueryProvisionReservations]
    "The Provisions this reservation connects"


class Get_provisionQuery(GraphQLQuery):
    provision: Optional[Get_provisionQueryProvision]

    class Meta:
        domain = "arkitekt"
        document = "query get_provision($reference: ID!) {\n  provision(reference: $reference) {\n    template {\n      id\n      node {\n        name\n      }\n      registry {\n        app {\n          name\n        }\n      }\n      extensions\n    }\n    bound {\n      registry {\n        id\n        name\n      }\n      name\n      identifier\n    }\n    reservations {\n      id\n      reference\n      creator {\n        username\n      }\n      app {\n        name\n      }\n    }\n  }\n}"


class Get_reservationQueryReservationTemplateRegistryApp(GraphQLObject):
    typename: Optional[Literal["LokApp"]] = Field(alias="__typename")
    id: str
    name: str


class Get_reservationQueryReservationTemplateRegistryUser(GraphQLObject):
    typename: Optional[Literal["LokUser"]] = Field(alias="__typename")
    id: str
    email: str


class Get_reservationQueryReservationTemplateRegistry(GraphQLObject):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    app: Optional[Get_reservationQueryReservationTemplateRegistryApp]
    "The Associated App"
    user: Optional[Get_reservationQueryReservationTemplateRegistryUser]
    "The Associated App"


class Get_reservationQueryReservationTemplate(GraphQLObject):
    typename: Optional[Literal["Template"]] = Field(alias="__typename")
    id: str
    registry: Get_reservationQueryReservationTemplateRegistry
    "The associated registry for this Template"


class Get_reservationQueryReservationProvisions(GraphQLObject):
    typename: Optional[Literal["Provision"]] = Field(alias="__typename")
    id: str
    status: ProvisionStatus
    "Current lifecycle of Provision"


class Get_reservationQueryReservationNode(NodeMixin, GraphQLObject):
    typename: Optional[Literal["Node"]] = Field(alias="__typename")
    id: str
    type: NodeType
    "Function, generator? Check async Programming Textbook"
    name: str
    "The cleartext name of this Node"


class Get_reservationQueryReservation(GraphQLObject):
    typename: Optional[Literal["Reservation"]] = Field(alias="__typename")
    id: str
    template: Optional[Get_reservationQueryReservationTemplate]
    "The template this reservation connects"
    provisions: List[Get_reservationQueryReservationProvisions]
    "The Provisions this reservation connects"
    title: Optional[str]
    "A Short Hand Way to identify this reservation for you"
    status: ReservationStatus
    "Current lifecycle of Reservation"
    id: str
    reference: str
    "The Unique identifier of this Assignation"
    node: Optional[Get_reservationQueryReservationNode]
    "The node this reservation connects"


class Get_reservationQuery(GraphQLQuery):
    reservation: Optional[Get_reservationQueryReservation]

    class Meta:
        domain = "arkitekt"
        document = "query get_reservation($reference: ID!) {\n  reservation(reference: $reference) {\n    id\n    template {\n      id\n      registry {\n        app {\n          id\n          name\n        }\n        user {\n          id\n          email\n        }\n      }\n    }\n    provisions {\n      id\n      status\n    }\n    title\n    status\n    id\n    reference\n    node {\n      id\n      type\n      name\n    }\n  }\n}"


class WaitlistQuery(GraphQLQuery):
    waitlist: Optional[List[Optional[ReservationFragment]]]

    class Meta:
        domain = "arkitekt"
        document = "fragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n}\n\nquery waitlist($appGroup: ID) {\n  waitlist(appGroup: $appGroup) {\n    ...Reservation\n  }\n}"


class FindQuery(GraphQLQuery):
    node: Optional[NodeFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment StructureArgPort on StructureArgPort {\n  key\n  identifier\n}\n\nfragment IntKwargPort on IntKwargPort {\n  key\n  defaultInt\n}\n\nfragment StringKwargPort on StringKwargPort {\n  key\n  defaultString\n}\n\nfragment StructureReturnPort on StructureReturnPort {\n  __typename\n  key\n  identifier\n}\n\nfragment StringArgPort on StringArgPort {\n  key\n}\n\nfragment ListKwargPort on ListKwargPort {\n  key\n  child {\n    __typename\n    ... on StructureKwargPort {\n      identifier\n    }\n  }\n  defaultList\n}\n\nfragment ListArgPort on ListArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment DictKwargPort on DictKwargPort {\n  key\n  defaultDict\n}\n\nfragment IntReturnPort on IntReturnPort {\n  __typename\n  key\n}\n\nfragment IntArgPort on IntArgPort {\n  key\n}\n\nfragment DictArgPort on DictArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment StringReturnPort on StringReturnPort {\n  __typename\n  key\n}\n\nfragment BoolKwargPort on BoolKwargPort {\n  key\n  defaultBool\n}\n\nfragment ListReturnPort on ListReturnPort {\n  key\n  child {\n    __typename\n    ... on StructureReturnPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment KwargPort on KwargPort {\n  __typename\n  key\n  description\n  ...DictKwargPort\n  ...BoolKwargPort\n  ...IntKwargPort\n  ...ListKwargPort\n  ...StringKwargPort\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  key\n  description\n  ...ListReturnPort\n  ...StructureReturnPort\n  ...StringReturnPort\n  ...IntReturnPort\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  description\n  ...StringArgPort\n  ...StructureArgPort\n  ...ListArgPort\n  ...IntArgPort\n  ...DictArgPort\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nquery find($id: ID, $package: String, $interface: String, $template: ID, $q: QString) {\n  node(\n    id: $id\n    package: $package\n    interface: $interface\n    template: $template\n    q: $q\n  ) {\n    ...Node\n  }\n}"


class Get_templateQuery(GraphQLQuery):
    template: Optional[TemplateFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment StringArgPort on StringArgPort {\n  key\n}\n\nfragment DictArgPort on DictArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment ListArgPort on ListArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment IntKwargPort on IntKwargPort {\n  key\n  defaultInt\n}\n\nfragment StringKwargPort on StringKwargPort {\n  key\n  defaultString\n}\n\nfragment ListKwargPort on ListKwargPort {\n  key\n  child {\n    __typename\n    ... on StructureKwargPort {\n      identifier\n    }\n  }\n  defaultList\n}\n\nfragment StringReturnPort on StringReturnPort {\n  __typename\n  key\n}\n\nfragment IntReturnPort on IntReturnPort {\n  __typename\n  key\n}\n\nfragment IntArgPort on IntArgPort {\n  key\n}\n\nfragment BoolKwargPort on BoolKwargPort {\n  key\n  defaultBool\n}\n\nfragment ListReturnPort on ListReturnPort {\n  key\n  child {\n    __typename\n    ... on StructureReturnPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment StructureArgPort on StructureArgPort {\n  key\n  identifier\n}\n\nfragment StructureReturnPort on StructureReturnPort {\n  __typename\n  key\n  identifier\n}\n\nfragment DictKwargPort on DictKwargPort {\n  key\n  defaultDict\n}\n\nfragment KwargPort on KwargPort {\n  __typename\n  key\n  description\n  ...DictKwargPort\n  ...BoolKwargPort\n  ...IntKwargPort\n  ...ListKwargPort\n  ...StringKwargPort\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  description\n  ...StringArgPort\n  ...StructureArgPort\n  ...ListArgPort\n  ...IntArgPort\n  ...DictArgPort\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  key\n  description\n  ...ListReturnPort\n  ...StructureReturnPort\n  ...StringReturnPort\n  ...IntReturnPort\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nfragment Template on Template {\n  id\n  registry {\n    app {\n      name\n    }\n    user {\n      username\n    }\n  }\n  node {\n    ...Node\n  }\n}\n\nquery get_template($id: ID!) {\n  template(id: $id) {\n    ...Template\n  }\n}"


class Get_agentQueryAgentRegistry(GraphQLObject):
    typename: Optional[Literal["Registry"]] = Field(alias="__typename")
    id: str
    name: str
    "A name for this registzry"


class Get_agentQueryAgent(GraphQLObject):
    typename: Optional[Literal["Agent"]] = Field(alias="__typename")
    registry: Optional[Get_agentQueryAgentRegistry]
    "The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users"
    name: str
    "This providers Name"
    identifier: str


class Get_agentQuery(GraphQLQuery):
    agent: Optional[Get_agentQueryAgent]

    class Meta:
        domain = "arkitekt"
        document = "query get_agent($id: ID!) {\n  agent(id: $id) {\n    registry {\n      id\n      name\n    }\n    name\n    identifier\n  }\n}"


class AssignMutation(GraphQLMutation):
    assign: Optional[AssignationFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nmutation assign($reservation: ID!, $args: [GenericScalar]!, $kwargs: GenericScalar) {\n  assign(reservation: $reservation, args: $args, kwargs: $kwargs) {\n    ...Assignation\n  }\n}"


class UnassignMutation(GraphQLMutation):
    unassign: Optional[AssignationFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment Assignation on Assignation {\n  args\n  kwargs\n  id\n  parent {\n    id\n  }\n  id\n  status\n  statusmessage\n}\n\nmutation unassign($assignation: ID!) {\n  unassign(assignation: $assignation) {\n    ...Assignation\n  }\n}"


class NegotiateMutation(GraphQLMutation):
    negotiate: Optional[TranscriptFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment Transcript on Transcript {\n  postman {\n    type\n    kwargs\n  }\n}\n\nmutation negotiate {\n  negotiate {\n    ...Transcript\n  }\n}"


class ReserveMutation(GraphQLMutation):
    reserve: Optional[ReservationFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n}\n\nmutation reserve($node: ID, $template: ID, $params: ReserveParamsInput, $title: String, $callbacks: [Callback], $creator: ID, $appGroup: ID) {\n  reserve(\n    node: $node\n    template: $template\n    params: $params\n    title: $title\n    callbacks: $callbacks\n    creator: $creator\n    appGroup: $appGroup\n  ) {\n    ...Reservation\n  }\n}"


class UnreserveMutation(GraphQLMutation):
    unreserve: Optional[ReservationFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment Reservation on Reservation {\n  id\n  statusmessage\n  status\n  node {\n    id\n    pure\n  }\n}\n\nmutation unreserve($id: ID!) {\n  unreserve(id: $id) {\n    ...Reservation\n  }\n}"


class Create_nodeMutation(GraphQLMutation):
    createNode: Optional[NodeFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment StructureArgPort on StructureArgPort {\n  key\n  identifier\n}\n\nfragment IntKwargPort on IntKwargPort {\n  key\n  defaultInt\n}\n\nfragment StringKwargPort on StringKwargPort {\n  key\n  defaultString\n}\n\nfragment StructureReturnPort on StructureReturnPort {\n  __typename\n  key\n  identifier\n}\n\nfragment StringArgPort on StringArgPort {\n  key\n}\n\nfragment ListKwargPort on ListKwargPort {\n  key\n  child {\n    __typename\n    ... on StructureKwargPort {\n      identifier\n    }\n  }\n  defaultList\n}\n\nfragment ListArgPort on ListArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment DictKwargPort on DictKwargPort {\n  key\n  defaultDict\n}\n\nfragment IntReturnPort on IntReturnPort {\n  __typename\n  key\n}\n\nfragment IntArgPort on IntArgPort {\n  key\n}\n\nfragment DictArgPort on DictArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment StringReturnPort on StringReturnPort {\n  __typename\n  key\n}\n\nfragment BoolKwargPort on BoolKwargPort {\n  key\n  defaultBool\n}\n\nfragment ListReturnPort on ListReturnPort {\n  key\n  child {\n    __typename\n    ... on StructureReturnPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment KwargPort on KwargPort {\n  __typename\n  key\n  description\n  ...DictKwargPort\n  ...BoolKwargPort\n  ...IntKwargPort\n  ...ListKwargPort\n  ...StringKwargPort\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  key\n  description\n  ...ListReturnPort\n  ...StructureReturnPort\n  ...StringReturnPort\n  ...IntReturnPort\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  description\n  ...StringArgPort\n  ...StructureArgPort\n  ...ListArgPort\n  ...IntArgPort\n  ...DictArgPort\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nmutation create_node($name: String!, $interface: String!, $args: [ArgPortInput]) {\n  createNode(name: $name, interface: $interface, args: $args) {\n    ...Node\n  }\n}"


class DefineMutation(GraphQLMutation):
    define: Optional[NodeFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment StructureArgPort on StructureArgPort {\n  key\n  identifier\n}\n\nfragment IntKwargPort on IntKwargPort {\n  key\n  defaultInt\n}\n\nfragment StringKwargPort on StringKwargPort {\n  key\n  defaultString\n}\n\nfragment StructureReturnPort on StructureReturnPort {\n  __typename\n  key\n  identifier\n}\n\nfragment StringArgPort on StringArgPort {\n  key\n}\n\nfragment ListKwargPort on ListKwargPort {\n  key\n  child {\n    __typename\n    ... on StructureKwargPort {\n      identifier\n    }\n  }\n  defaultList\n}\n\nfragment ListArgPort on ListArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment DictKwargPort on DictKwargPort {\n  key\n  defaultDict\n}\n\nfragment IntReturnPort on IntReturnPort {\n  __typename\n  key\n}\n\nfragment IntArgPort on IntArgPort {\n  key\n}\n\nfragment DictArgPort on DictArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment StringReturnPort on StringReturnPort {\n  __typename\n  key\n}\n\nfragment BoolKwargPort on BoolKwargPort {\n  key\n  defaultBool\n}\n\nfragment ListReturnPort on ListReturnPort {\n  key\n  child {\n    __typename\n    ... on StructureReturnPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment KwargPort on KwargPort {\n  __typename\n  key\n  description\n  ...DictKwargPort\n  ...BoolKwargPort\n  ...IntKwargPort\n  ...ListKwargPort\n  ...StringKwargPort\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  key\n  description\n  ...ListReturnPort\n  ...StructureReturnPort\n  ...StringReturnPort\n  ...IntReturnPort\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  description\n  ...StringArgPort\n  ...StructureArgPort\n  ...ListArgPort\n  ...IntArgPort\n  ...DictArgPort\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nmutation define($definition: DefinitionInput!) {\n  define(definition: $definition) {\n    ...Node\n  }\n}"


class Reset_repositoryMutationResetrepository(GraphQLObject):
    typename: Optional[Literal["ResetRepositoryReturn"]] = Field(alias="__typename")
    ok: Optional[bool]


class Reset_repositoryMutation(GraphQLMutation):
    resetRepository: Optional[Reset_repositoryMutationResetrepository]

    class Meta:
        domain = "arkitekt"
        document = "mutation reset_repository {\n  resetRepository {\n    ok\n  }\n}"


class Create_templateMutation(GraphQLMutation):
    createTemplate: Optional[TemplateFragment]

    class Meta:
        domain = "arkitekt"
        document = "fragment StringArgPort on StringArgPort {\n  key\n}\n\nfragment DictArgPort on DictArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment ListArgPort on ListArgPort {\n  key\n  child {\n    __typename\n    ... on StructureArgPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment IntKwargPort on IntKwargPort {\n  key\n  defaultInt\n}\n\nfragment StringKwargPort on StringKwargPort {\n  key\n  defaultString\n}\n\nfragment ListKwargPort on ListKwargPort {\n  key\n  child {\n    __typename\n    ... on StructureKwargPort {\n      identifier\n    }\n  }\n  defaultList\n}\n\nfragment StringReturnPort on StringReturnPort {\n  __typename\n  key\n}\n\nfragment IntReturnPort on IntReturnPort {\n  __typename\n  key\n}\n\nfragment IntArgPort on IntArgPort {\n  key\n}\n\nfragment BoolKwargPort on BoolKwargPort {\n  key\n  defaultBool\n}\n\nfragment ListReturnPort on ListReturnPort {\n  key\n  child {\n    __typename\n    ... on StructureReturnPort {\n      __typename\n      identifier\n    }\n  }\n}\n\nfragment StructureArgPort on StructureArgPort {\n  key\n  identifier\n}\n\nfragment StructureReturnPort on StructureReturnPort {\n  __typename\n  key\n  identifier\n}\n\nfragment DictKwargPort on DictKwargPort {\n  key\n  defaultDict\n}\n\nfragment KwargPort on KwargPort {\n  __typename\n  key\n  description\n  ...DictKwargPort\n  ...BoolKwargPort\n  ...IntKwargPort\n  ...ListKwargPort\n  ...StringKwargPort\n}\n\nfragment ArgPort on ArgPort {\n  __typename\n  key\n  description\n  ...StringArgPort\n  ...StructureArgPort\n  ...ListArgPort\n  ...IntArgPort\n  ...DictArgPort\n}\n\nfragment ReturnPort on ReturnPort {\n  __typename\n  key\n  description\n  ...ListReturnPort\n  ...StructureReturnPort\n  ...StringReturnPort\n  ...IntReturnPort\n}\n\nfragment Node on Node {\n  name\n  interface\n  package\n  description\n  type\n  id\n  args {\n    ...ArgPort\n  }\n  kwargs {\n    ...KwargPort\n  }\n  returns {\n    ...ReturnPort\n  }\n}\n\nfragment Template on Template {\n  id\n  registry {\n    app {\n      name\n    }\n    user {\n      username\n    }\n  }\n  node {\n    ...Node\n  }\n}\n\nmutation create_template($node: ID!, $params: GenericScalar, $extensions: [String], $version: String) {\n  createTemplate(\n    node: $node\n    params: $params\n    extensions: $extensions\n    version: $version\n  ) {\n    ...Template\n  }\n}"


async def atodos(identifier: str) -> AsyncIterator[TodosSubscriptionTodos]:
    """todos



    Arguments:
        identifier (ID): ID

    Returns:
        TodosSubscriptionTodos: The returned Mutation"""
    async for event in TodosSubscription.asubscribe({"identifier": identifier}):
        yield event.todos


def todos(identifier: str) -> Iterator[TodosSubscriptionTodos]:
    """todos



    Arguments:
        identifier (ID): ID

    Returns:
        TodosSubscriptionTodos: The returned Mutation"""
    for event in TodosSubscription.subscribe({"identifier": identifier}):
        yield event.todos


async def awaiter(identifier: str) -> AsyncIterator[WaiterSubscriptionWaiter]:
    """waiter



    Arguments:
        identifier (ID): ID

    Returns:
        WaiterSubscriptionWaiter: The returned Mutation"""
    async for event in WaiterSubscription.asubscribe({"identifier": identifier}):
        yield event.waiter


def waiter(identifier: str) -> Iterator[WaiterSubscriptionWaiter]:
    """waiter



    Arguments:
        identifier (ID): ID

    Returns:
        WaiterSubscriptionWaiter: The returned Mutation"""
    for event in WaiterSubscription.subscribe({"identifier": identifier}):
        yield event.waiter


async def atodolist(appGroup: str = None) -> List[AssignationFragment]:
    """todolist



    Arguments:
        appGroup (ID, Optional): ID

    Returns:
        AssignationFragment: The returned Mutation"""
    return (await TodolistQuery.aexecute({"appGroup": appGroup})).todolist


def todolist(appGroup: str = None) -> List[AssignationFragment]:
    """todolist



    Arguments:
        appGroup (ID, Optional): ID

    Returns:
        AssignationFragment: The returned Mutation"""
    return TodolistQuery.execute({"appGroup": appGroup}).todolist


async def aget_provision(reference: str) -> Get_provisionQueryProvision:
    """get_provision



    Arguments:
        reference (ID): ID

    Returns:
        Get_provisionQueryProvision: The returned Mutation"""
    return (await Get_provisionQuery.aexecute({"reference": reference})).provision


def get_provision(reference: str) -> Get_provisionQueryProvision:
    """get_provision



    Arguments:
        reference (ID): ID

    Returns:
        Get_provisionQueryProvision: The returned Mutation"""
    return Get_provisionQuery.execute({"reference": reference}).provision


async def aget_reservation(reference: str) -> Get_reservationQueryReservation:
    """get_reservation



    Arguments:
        reference (ID): ID

    Returns:
        Get_reservationQueryReservation: The returned Mutation"""
    return (await Get_reservationQuery.aexecute({"reference": reference})).reservation


def get_reservation(reference: str) -> Get_reservationQueryReservation:
    """get_reservation



    Arguments:
        reference (ID): ID

    Returns:
        Get_reservationQueryReservation: The returned Mutation"""
    return Get_reservationQuery.execute({"reference": reference}).reservation


async def awaitlist(appGroup: str = None) -> List[ReservationFragment]:
    """waitlist



    Arguments:
        appGroup (ID, Optional): ID

    Returns:
        ReservationFragment: The returned Mutation"""
    return (await WaitlistQuery.aexecute({"appGroup": appGroup})).waitlist


def waitlist(appGroup: str = None) -> List[ReservationFragment]:
    """waitlist



    Arguments:
        appGroup (ID, Optional): ID

    Returns:
        ReservationFragment: The returned Mutation"""
    return WaitlistQuery.execute({"appGroup": appGroup}).waitlist


async def afind(
    id: str = None,
    package: str = None,
    interface: str = None,
    template: str = None,
    q: QString = None,
) -> NodeFragment:
    """find

    Asss

        Is A query for all of these specials in the world


    Arguments:
        id (ID, Optional): ID
        package (String, Optional): String
        interface (String, Optional): String
        template (ID, Optional): ID
        q (QString, Optional): QString

    Returns:
        NodeFragment: The returned Mutation"""
    return (
        await FindQuery.aexecute(
            {
                "id": id,
                "package": package,
                "interface": interface,
                "template": template,
                "q": q,
            }
        )
    ).node


def find(
    id: str = None,
    package: str = None,
    interface: str = None,
    template: str = None,
    q: QString = None,
) -> NodeFragment:
    """find

    Asss

        Is A query for all of these specials in the world


    Arguments:
        id (ID, Optional): ID
        package (String, Optional): String
        interface (String, Optional): String
        template (ID, Optional): ID
        q (QString, Optional): QString

    Returns:
        NodeFragment: The returned Mutation"""
    return FindQuery.execute(
        {
            "id": id,
            "package": package,
            "interface": interface,
            "template": template,
            "q": q,
        }
    ).node


async def aget_template(id: str) -> TemplateFragment:
    """get_template



    Arguments:
        id (ID): ID

    Returns:
        TemplateFragment: The returned Mutation"""
    return (await Get_templateQuery.aexecute({"id": id})).template


def get_template(id: str) -> TemplateFragment:
    """get_template



    Arguments:
        id (ID): ID

    Returns:
        TemplateFragment: The returned Mutation"""
    return Get_templateQuery.execute({"id": id}).template


async def aget_agent(id: str) -> Get_agentQueryAgent:
    """get_agent



    Arguments:
        id (ID): ID

    Returns:
        Get_agentQueryAgent: The returned Mutation"""
    return (await Get_agentQuery.aexecute({"id": id})).agent


def get_agent(id: str) -> Get_agentQueryAgent:
    """get_agent



    Arguments:
        id (ID): ID

    Returns:
        Get_agentQueryAgent: The returned Mutation"""
    return Get_agentQuery.execute({"id": id}).agent


async def aassign(
    reservation: str, args: List[Dict], kwargs: Dict = None
) -> AssignationFragment:
    """assign



    Arguments:
        reservation (ID): ID
        args (List[GenericScalar]): GenericScalar
        kwargs (GenericScalar, Optional): GenericScalar

    Returns:
        AssignationFragment: The returned Mutation"""
    return (
        await AssignMutation.aexecute(
            {"reservation": reservation, "args": args, "kwargs": kwargs}
        )
    ).assign


def assign(
    reservation: str, args: List[Dict], kwargs: Dict = None
) -> AssignationFragment:
    """assign



    Arguments:
        reservation (ID): ID
        args (List[GenericScalar]): GenericScalar
        kwargs (GenericScalar, Optional): GenericScalar

    Returns:
        AssignationFragment: The returned Mutation"""
    return AssignMutation.execute(
        {"reservation": reservation, "args": args, "kwargs": kwargs}
    ).assign


async def aunassign(assignation: str) -> AssignationFragment:
    """unassign



    Arguments:
        assignation (ID): ID

    Returns:
        AssignationFragment: The returned Mutation"""
    return (await UnassignMutation.aexecute({"assignation": assignation})).unassign


def unassign(assignation: str) -> AssignationFragment:
    """unassign



    Arguments:
        assignation (ID): ID

    Returns:
        AssignationFragment: The returned Mutation"""
    return UnassignMutation.execute({"assignation": assignation}).unassign


async def anegotiate() -> TranscriptFragment:
    """negotiate

    Create Node according to the specifications

    Arguments:

    Returns:
        TranscriptFragment: The returned Mutation"""
    return (await NegotiateMutation.aexecute({})).negotiate


def negotiate() -> TranscriptFragment:
    """negotiate

    Create Node according to the specifications

    Arguments:

    Returns:
        TranscriptFragment: The returned Mutation"""
    return NegotiateMutation.execute({}).negotiate


async def areserve(
    node: str = None,
    template: str = None,
    params: ReserveParamsInput = None,
    title: str = None,
    callbacks: List[str] = None,
    creator: str = None,
    appGroup: str = None,
) -> ReservationFragment:
    """reserve



    Arguments:
        node (ID, Optional): ID
        template (ID, Optional): ID
        params (ReserveParamsInput, Optional): ReserveParamsInput
        title (String, Optional): String
        callbacks (List[Callback], Optional): Callback
        creator (ID, Optional): ID
        appGroup (ID, Optional): ID

    Returns:
        ReservationFragment: The returned Mutation"""
    return (
        await ReserveMutation.aexecute(
            {
                "node": node,
                "template": template,
                "params": params,
                "title": title,
                "callbacks": callbacks,
                "creator": creator,
                "appGroup": appGroup,
            }
        )
    ).reserve


def reserve(
    node: str = None,
    template: str = None,
    params: ReserveParamsInput = None,
    title: str = None,
    callbacks: List[str] = None,
    creator: str = None,
    appGroup: str = None,
) -> ReservationFragment:
    """reserve



    Arguments:
        node (ID, Optional): ID
        template (ID, Optional): ID
        params (ReserveParamsInput, Optional): ReserveParamsInput
        title (String, Optional): String
        callbacks (List[Callback], Optional): Callback
        creator (ID, Optional): ID
        appGroup (ID, Optional): ID

    Returns:
        ReservationFragment: The returned Mutation"""
    return ReserveMutation.execute(
        {
            "node": node,
            "template": template,
            "params": params,
            "title": title,
            "callbacks": callbacks,
            "creator": creator,
            "appGroup": appGroup,
        }
    ).reserve


async def aunreserve(id: str) -> ReservationFragment:
    """unreserve



    Arguments:
        id (ID): ID

    Returns:
        ReservationFragment: The returned Mutation"""
    return (await UnreserveMutation.aexecute({"id": id})).unreserve


def unreserve(id: str) -> ReservationFragment:
    """unreserve



    Arguments:
        id (ID): ID

    Returns:
        ReservationFragment: The returned Mutation"""
    return UnreserveMutation.execute({"id": id}).unreserve


async def acreate_node(
    name: str, interface: str, args: List[ArgPortInput] = None
) -> NodeFragment:
    """create_node

    Create Node according to the specifications

    Arguments:
        name (String): String
        interface (String): String
        args (List[ArgPortInput], Optional): ArgPortInput

    Returns:
        NodeFragment: The returned Mutation"""
    return (
        await Create_nodeMutation.aexecute(
            {"name": name, "interface": interface, "args": args}
        )
    ).createNode


def create_node(
    name: str, interface: str, args: List[ArgPortInput] = None
) -> NodeFragment:
    """create_node

    Create Node according to the specifications

    Arguments:
        name (String): String
        interface (String): String
        args (List[ArgPortInput], Optional): ArgPortInput

    Returns:
        NodeFragment: The returned Mutation"""
    return Create_nodeMutation.execute(
        {"name": name, "interface": interface, "args": args}
    ).createNode


async def adefine(definition: DefinitionInput) -> NodeFragment:
    """define

    Defines a node according to is definition

    Arguments:
        definition (DefinitionInput): DefinitionInput

    Returns:
        NodeFragment: The returned Mutation"""
    return (await DefineMutation.aexecute({"definition": definition})).define


def define(definition: DefinitionInput) -> NodeFragment:
    """define

    Defines a node according to is definition

    Arguments:
        definition (DefinitionInput): DefinitionInput

    Returns:
        NodeFragment: The returned Mutation"""
    return DefineMutation.execute({"definition": definition}).define


async def areset_repository() -> Reset_repositoryMutationResetrepository:
    """reset_repository

    Create Repostiory

    Arguments:

    Returns:
        Reset_repositoryMutationResetrepository: The returned Mutation"""
    return (await Reset_repositoryMutation.aexecute({})).resetRepository


def reset_repository() -> Reset_repositoryMutationResetrepository:
    """reset_repository

    Create Repostiory

    Arguments:

    Returns:
        Reset_repositoryMutationResetrepository: The returned Mutation"""
    return Reset_repositoryMutation.execute({}).resetRepository


async def acreate_template(
    node: str, params: Dict = None, extensions: List[str] = None, version: str = None
) -> TemplateFragment:
    """create_template



    Arguments:
        node (ID): ID
        params (GenericScalar, Optional): GenericScalar
        extensions (List[String], Optional): String
        version (String, Optional): String

    Returns:
        TemplateFragment: The returned Mutation"""
    return (
        await Create_templateMutation.aexecute(
            {
                "node": node,
                "params": params,
                "extensions": extensions,
                "version": version,
            }
        )
    ).createTemplate


def create_template(
    node: str, params: Dict = None, extensions: List[str] = None, version: str = None
) -> TemplateFragment:
    """create_template



    Arguments:
        node (ID): ID
        params (GenericScalar, Optional): GenericScalar
        extensions (List[String], Optional): String
        version (String, Optional): String

    Returns:
        TemplateFragment: The returned Mutation"""
    return Create_templateMutation.execute(
        {"node": node, "params": params, "extensions": extensions, "version": version}
    ).createTemplate
