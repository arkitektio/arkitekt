from arkitekt.postmans.errors import PostmanException


class PostmanTransportException(PostmanException):
    """
    Base class for all exceptions raised by the Agent Transport.
    """



class ReservationListDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """



class AssignationListDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """



class AssignDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """



class UnassignDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """



class ReserveDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """



class UnreserveDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """

