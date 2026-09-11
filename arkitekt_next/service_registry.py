import contextvars
from fakts_next import Fakts
from koil.composition.base import KoiledModel
from fakts_next.models import Manifest, Requirement
from typing import Any, Callable, Dict, Optional, Protocol, Set, TypeVar
from typing import runtime_checkable
from pydantic import BaseModel

Params = Dict[str, Any]


current_service_registry = contextvars.ContextVar(
    "current_service_registry", default=None
)


class Registration(BaseModel):
    name: str
    requirement: Requirement
    builder: Callable[[Fakts, Params], object]
    schema_loader: Callable[[str], object]


@runtime_checkable
class ArkitektService(Protocol):
    def get_service_name(self) -> str:
        """Get the service name. This is used to identify the service in the
        service registry. The service name should be unique across all services.
        """
        ...

    def build_service(self, fakts: Fakts, params: Params) -> Optional[KoiledModel]:
        """Build the service. This is used to build the service and return
        the service instance. The service instance should be a KoiledModel
        that is used to interact with the service.
        """
        ...

    def get_requirements(self) -> list[Requirement]:
        """Get the requirements for the service. This is used to get the
        requirements for the service. The requirements should be a list of
        Requirement objects that are used to identify the service in the
        service registry. The requirements should be unique across all
        """
        ...

    def get_graphql_schema(self) -> Optional[str]:
        """Get the GraphQL schema for the service. This is used to get the
        GraphQL schema for the service. The GraphQL schema should be a
        GraphQL schema object that is used to interact with the service.
        """
        pass

    def get_turms_project(self) -> Optional[Dict[str, Any]]:
        """Get the Turms project for the service. This is used to get the
        Turms project for the service. The Turms project should be a
        Turms project object that is used to interact with the service.
        """
        pass


class BaseArkitektService:
    """Base class for Arkitekt services. This class is used to define the
    interface for Arkitekt services. It is used to define the service name,
    build the service, and get the requirements for the service."""

    def get_service_name(self) -> str:
        raise NotImplementedError("get_service_name not implemented")

    def build_service(self, fakts: Fakts, params: Params) -> Optional[KoiledModel]:
        raise NotImplementedError("build_service not implemented")

    def get_requirements(self) -> list[Requirement]:
        raise NotImplementedError("get_requirements not implemented")

    def get_graphql_schema(self) -> Optional[str]:
        return None

    def get_turms_project(self) -> Optional[Dict[str, Any]]:
        """Get the Turms project for the service. This is used to get the
        Turms project for the service. The Turms project should be a
        Turms project object that is used to interact with the service.
        """
        return None


basic_requirements = []


class ServiceBuilderRegistry:
    def __init__(self):
        self.service_builders: Dict[str, ArkitektService] = {}
        self.additional_requirements: Dict[str, Requirement] = {}

    def register(
        self,
        service: ArkitektService,
    ):
        name = service.get_service_name()

        if name not in self.service_builders:
            self.service_builders[name] = service
        else:
            raise ValueError(f"Service {name} already registered")

    def register_requirement(self, requirement: Requirement):
        if requirement.key in self.additional_requirements:
            raise ValueError(f"Requirement {requirement.key} already registered)")
        self.additional_requirements[requirement.key] = requirement

    def get(self, name: str) -> Optional[ArkitektService]:
        return self.service_builders.get(name)

    def build_service_map(self, fakts: Fakts, params: Params):
        potentially_needed_services = {
            name: service.build_service(fakts, params)
            for name, service in self.service_builders.items()
        }

        return {
            key: value
            for key, value in potentially_needed_services.items()
            if value is not None
        }

    def get_requirements(self):
        requirements = []
        taken_requirements: Set[str] = set()

        for service in self.service_builders.values():
            for requirement in service.get_requirements():
                if requirement.key not in taken_requirements:
                    taken_requirements.add(requirement.key)
                    requirements.append(requirement)

        for requirement in self.additional_requirements.values():
            if requirement.key not in taken_requirements:
                taken_requirements.add(requirement.key)
                requirements.append(requirement)

        sorted_requirements = sorted(requirements, key=lambda x: x.key)

        return sorted_requirements


T = TypeVar("T")


def require(
    key: str,
    service: str,
    description: str | None = None,
    service_registry: Optional[ServiceBuilderRegistry] = None,
) -> Requirement:
    """Register a requirement with the service registry

    Parameters
    ----------
    key : str
        The key for the requirement. This should be unique across all
        requirements.

    service : str
        The service that you require. This should be a uinque fakts
        service name. I.e `live.arkitekt.lok` or `live.arkitekt.lok:0.0.1`

    description : str | None
        The description for the requirement. This should be a short
        description of the requirement that gets displayed to the user.

    service_registry : ServiceBuilderRegistry | None
        The service registry to register the requirement with. If
        None, the default service registry will be used.

    Returns
    -------
    Requirement
        The requirement that was registered. This can be used to
        get the requirement later on.

    """
    service_hook_registry = service_registry or get_default_service_registry()

    requirement = Requirement(key=key, service=service, description=description)
    service_hook_registry.register_requirement(requirement)

    return requirement


GLOBAL_SERVICE_REGISTRY = None


def get_default_service_registry() -> "ServiceBuilderRegistry":
    global GLOBAL_SERVICE_REGISTRY
    if GLOBAL_SERVICE_REGISTRY is None:
        GLOBAL_SERVICE_REGISTRY = ServiceBuilderRegistry()  # type: ignore
    return GLOBAL_SERVICE_REGISTRY
