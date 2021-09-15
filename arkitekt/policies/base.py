from enum import Enum
from typing import Optional, Union
from herre.access.object import GraphQLObject

class ReservePolicy(GraphQLObject):
    """Determinns how the once running
    provision can be reserved

    Args:
        GraphQLModel ([type]): [description]
    """
    pass

class PrivateReservePolicy(ReservePolicy):
    # Only the provisioner can reserve a provision of this template
    pass


class AllReservePolicy(ReservePolicy):
    # All users can reserve a provision of this template
    pass

class GroupReservePolicy(ReservePolicy):
    # Only users of a certain group can reserve this provision
    allowed_groups: Optional[int]    


class ProvisionPolicy(GraphQLObject):
    """Determins who and when a user can
    provision a pod also, if it should die or not
    after

    Args:
        GraphQLModel ([type]): [description]
    """
    pass

class AllProvisionPolicy(ProvisionPolicy):

    pass

class AdminProvisionPolicy(ProvisionPolicy):

    pass


class GroupProvisionPolicy(ProvisionPolicy):
    allowed_groups: Optional[int]  


class BalanceStrategy(GraphQLObject):
    """
    Distinguihhes how reservations to this worker are being handles
    should we try to provision a new worker for every reservation, etc
    
    """

    pass

class OneToOneStrategy(BalanceStrategy):
    """Map every Reservation to its own Provision

    Args:
        BalanceStrategy ([type]): [description]
    """
    allowed_provisions_per_user: int = -1 # indefinite amount of provisions allowed

class ManyToOneStrategy(BalanceStrategy):
    """Share a provision amongs a lot of reservations

    Use Cases:
        - A lot of users can access one resource (e.g. Microscope) without saving
          intermediate state (e.g a communal slice is mounted)

    Args:
        BalanceStrategy ([type]): [description]
    """


class OneToManyStrategy(BalanceStrategy):
    """Map every Reservation to its own Provision

    Args:
        BalanceStrategy ([type]): [description]
    """





class Policy(GraphQLObject):
    reserve: ReservePolicy
    provision: Union[AllProvisionPolicy, GroupProvisionPolicy]
    strategy: Union[OneToOneStrategy, ManyToOneStrategy, OneToManyStrategy]



EACH_USER_ONE_PROVISION = Policy(provision=AllProvisionPolicy(), reserve=AllReservePolicy(), strategy=OneToOneStrategy(allowed_provisions_per_user=1))
EVERY_USER_ON_PROVISION = Policy(provision=AllProvisionPolicy(), reserve=AllReservePolicy(), strategy=ManyToOneStrategy(allowed_provisions_per_user=1))
ONE_INSTANCE_PROVIDABLE_BY_ADMIN_SHARED_BY_EVERYONE = Policy(provision=AdminProvisionPolicy(), reserve=AllReservePolicy(), strategy=ManyToOneStrategy(allowed_provisions_per_user=1))
MANY_INSTANCES_PROVIDABLE_BY_ADMIN_SHARED_BY_GROUP = Policy(provision=AdminProvisionPolicy(), reserve=AllReservePolicy(), strategy=ManyToOneStrategy(allowed_provisions_per_user=-1))
