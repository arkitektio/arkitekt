from arkitekt.agents.errors import AgentException


class AgentTransportException(AgentException):
    """
    Base class for all exceptions raised by the Agent Transport.
    """



class ProvisionListDeniedError(AgentTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """



class AssignationListDeniedError(AgentTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """

