import contextvars
from arkitekt.actors.helper import AssignationHelper, ProvisionHelper


current_assignation_helper = contextvars.ContextVar("current_assignation_helper")
current_provision_helper = contextvars.ContextVar("current_provision_helper")


def get_current_assignation_helper() -> AssignationHelper:
    return current_assignation_helper.get()


def get_current_provision_helper() -> ProvisionHelper:
    return current_provision_helper.get()
