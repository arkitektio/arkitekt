class ActorException(Exception):
    pass


class UnknownMessageError(ActorException):
    pass


class ThreadedActorCancelled(ActorException):
    pass
