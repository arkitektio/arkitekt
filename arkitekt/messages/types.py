#Base Types
EXCEPTION = "exception"
ALLOWANCE = "allowance"


#Base Type
AGENT_CONNECT = "agent_connect"
AGENT_DISCONNECT = "agent_disconnect"



ASSIGNATION = "assignation"
PROVISION = "provision"
ASSIGNATION_REQUEST = "assignation_request"
PROVISION_REQUEST = "provision_request"

ACTIVATE_POD = "activate_pod"
DEACTIVATE_POD ="deactivate_pod"

# ASIGN PATH
ASSIGN = "assign"
BOUNCED_ASSIGN = "bounced_assign"
BOUNCED_FORWARDED_ASSIGN = "bounced_forwarded_assign"

ASSIGN_DONE = "assign_done"
ASSIGN_CANCELLED = "assign_cancelled"
ASSIGN_LOG ="assign_log"
ASSIGN_CRITICAL = "assign_fail"
ASSIGN_YIELD =  "assign_yield"
ASSIGN_RETURN = "assign_return"
ASSIGN_RETRY = "assign_retry"

# UNASSIGN PATH
UNASSIGN = "unassign"
BOUNCED_UNASSIGN = "bounced_unassign"
BOUNCED_FORWARDED_UNASSIGN = "bounced_forwarded_unassign"

UNASSIGN_DONE = "unassign_done"
UNASSIGN_LOG ="unassign_log"
UNASSIGN_CRITICAL = "unassign_fail"

# Reserve
RESERVE = "reserve"
BOUNCED_RESERVE = "bounced_reserve"
BOUNCED_FORWARDED_RESERVE = "bounced_forwarded_reserve"

RESERVE_DONE = "reserve_done"
RESERVE_LOG = "reserve_log"
RESERVE_FAIL = "reserve_fail"
RESERVE_TRANSITION = "reserve_transition"
RESERVE_CRITICAL = "reserve_critical"
RESERVE_ACTIVE = "reserve_active"
RESERVE_WAITING = "reserve_waiting"

#Unreserve
UNRESERVE = "unreserve"
BOUNCED_UNRESERVE = "bounced_unreserve"

UNRESERVE_DONE = "unreserve_done"
UNRESERVE_LOG = "unreserve_log"
UNRESERVE_FAIL = "unreserve_fail"
UNRESERVE_CRITICAL = "unreserve_critical"


# Provide
PROVIDE = "provide"
BOUNCED_PROVIDE = "bounced_provide"

PROVIDE_DONE = "provide_done"
PROVIDE_LOG = "provide_log"
PROVIDE_TRANSITION = "provide_transition"
PROVIDE_FAIL = "provide_fail"
PROVIDE_CRITICAL = "provide_critical"
# Unprovide
UNPROVIDE = "unprovide"
BOUNCED_UNPROVIDE = "bounced_unprovide"

UNPROVIDE_DONE = "unprovide_done"
UNPROVIDE_LOG = "unprovide_log"
UNPROVIDE_FAIL = "unprovide_fail"
UNPROVIDE_CRITICAL = "unprovide_critical"
UNPROVIDE_ERROR = "unprovide_error"

