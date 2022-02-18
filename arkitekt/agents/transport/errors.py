from arkitekt.agents.errors import AgentException


class AgentTransportException(AgentException):
    """
    Base class for all exceptions raised by the Agent Transport.
    """

    pass


class ProvisionListDeniedError(AgentTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """

    pass


class AssignationListDeniedError(AgentTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """

    pass
