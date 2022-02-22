from arkitekt.postmans.errors import PostmanException


class PostmanTransportException(PostmanException):
    """
    Base class for all exceptions raised by the Agent Transport.
    """

    pass


class ReservationListDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """

    pass


class AssignationListDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """

    pass


class AssignDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """

    pass


class UnassignDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the provisions.
    """

    pass


class ReserveDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """

    pass


class UnreserveDeniedError(PostmanTransportException):
    """
    Raised when the backend is not able to list the assignations.
    """

    pass
