from dokker.forms import prompt_if_flags, value_set
import pydantic
from typing import List, Optional, Dict
import secrets
import namegenerator

import socket
from contextlib import closing
import rich_click as click




class User(pydantic.BaseModel):

    _prelude = "A User for the Arkitekt Service"
    _confirm = "Are you happy with the user $username"
    username: str = pydantic.Field(prompt_text="The username of the user")
    password: str = pydantic.Field(
        default_factory=lambda: secrets.token_hex(16),
        prompt_text="The password of the user",
        prompt=True,
        hide_input=True,
    )
    groups: List[str] = pydantic.Field(
        default_factory=list,
        effects=[prompt_if_flags("advanced")],
    )


class Group(pydantic.BaseModel):
    name: str
    description: str = pydantic.Field(default="No Description")

taken_ports = set()

def generate_unique_port():
    global taken_ports
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]
        if port in taken_ports:
            return generate_unique_port()
        taken_ports.add(port)
        return port

class Bucket(pydantic.BaseModel):
    name: str = pydantic.Field(
        default_factory=lambda: namegenerator.gen(separator=""),
        effects=[prompt_if_flags("expert")],
    )
    access_key: str = pydantic.Field(
        default_factory=lambda: namegenerator.gen(separator=""),
        effects=[prompt_if_flags("expert")],
    )
    secret_key: str = pydantic.Field(
        default_factory=lambda: secrets.token_hex(16),
        effects=[prompt_if_flags("expert")],
    )


class Service(pydantic.BaseModel):
    enabled: bool = pydantic.Field(
        default=True,
        prompt_text="Do you want to enable the Service?",
        effects=[prompt_if_flags("advanced")],
    )
    channel = pydantic.Field(
        default="paper",
        effects=[prompt_if_flags("expert")],
    )
    django_secret_key: str = pydantic.Field(
        default_factory=lambda: secrets.token_hex(16),
        effects=[prompt_if_flags("expert")],
    )
    bucket: Optional[Bucket] = pydantic.Field(default_factory=Bucket)
    db_name: str = pydantic.Field(
        default_factory=lambda: namegenerator.gen(separator="_") + "_db",
        effects=[prompt_if_flags("expert")],
    )
    port: int = pydantic.Field(
        default_factory=generate_unique_port,
        effects=[prompt_if_flags("expert")],
    )
    volumes: List[str] = pydantic.Field(
        default_factory=list,
        effects=[prompt_if_flags("expert")],
    )




class StaticToken(pydantic.BaseModel):
    sub: str = pydantic.Field(promp_text="Which User ID should this map to?")


class OrkestratorService(Service):
    _prelude = "Lets setup Orkestrator"


class RekuestService(Service):
    _prelude = "Lets setup Rekuest"
    enabled: bool = pydantic.Field(default=True)


class PortService(Service):
    _prelude = "Lets setup Rekuest"
    enabled: bool = pydantic.Field(default=True)


class LokService(Service):
    _prelude = "Lets setup Lok"
    enabled: bool = pydantic.Field(default=True)

class LokNextService(Service):
    _prelude = "Lets setup Lok"
    enabled: bool = pydantic.Field(default=True)

class FlussService(Service):
    _prelude = "Lets setup Fluss"
    enabled: bool = pydantic.Field(default=True)


class MikroService(Service):
    _prelude = "Lets setup Mikro"
    enabled: bool = pydantic.Field(default=True)


class KlusterService(Service):
    _prelude = " Lets setup Kluster"
    enabled: bool = pydantic.Field(default=True)


class OmeroArkService(Service):
    _prelude = " Lets setup OmeroArk"
    enabled: bool = pydantic.Field(default=True)


class GatewayService(pydantic.BaseModel):
    _prelude = "Lets setup your Kluster Gateway"
    enabled: bool = pydantic.Field(default=True)
    volumes: List[str] = pydantic.Field(
        default_factory=list,
        prompt="Do you want to add volumes?",
        effects=[prompt_if_flags("expert")],
    )
    port: int = pydantic.Field(
        default_factory=generate_unique_port,
        prompt="What should the port be?",
        effects=[prompt_if_flags("expert")],
    )


class OmeroServerService(pydantic.BaseModel):
    _prelude = (
        "Setting up OMERO (The server)? Will also create another postgres instance."
    )
    enabled: bool = pydantic.Field(
        default=True,
        prompt_text="Do you wnat to enable OMERO?",
    )
    volumes: List[str] = pydantic.Field(default_factory=list)
    unsecure_port: int = pydantic.Field(
        default_factory=generate_unique_port,
        prompt_text="Which Port do you want to  for the Omero Secure API?",
        effects=[prompt_if_flags("expert")],
    )
    secure_port: int = pydantic.Field(
        default_factory=generate_unique_port,
        prompt_text="Which Port do you want to expose for the Omero Secure API?",
        effects=[prompt_if_flags("expert")],
    )
    postgres_password: str = pydantic.Field(
        default_factory=lambda: secrets.token_hex(16),
        prompt_text="Which Postgres password do you want to use?",
        effects=[prompt_if_flags("expert")],
    )
    root_password: str = pydantic.Field(
        "omero",
        prompt_text="What should be the root user password?",
        effects=[prompt_if_flags("advanced")],
    )
    postgres_user: str = pydantic.Field(
        default_factory=lambda: namegenerator.gen(separator=""),
        prompt_text="What should be the postgres user password?",
        effects=[prompt_if_flags("expert")],
    )
    postgres_db: str = pydantic.Field(
        default_factory=lambda: namegenerator.gen(separator="_") + "_db",
        prompt_text="What should be the postgres databas?",
        effects=[prompt_if_flags("expert")],
    )


class OmeroWebService(pydantic.BaseModel):
    _prelude = "Lets setup OMERO Web"
    enabled: bool = pydantic.Field(
        default=True,
        prompt_text="Do you want to enable OMERO Web?",
    )
    volumes: List[str] = pydantic.Field(
        default_factory=list,
        prompt=False,
        effects=[prompt_if_flags("expert")],
    )
    port: int = pydantic.Field(
        default_factory=generate_unique_port,
        prompt=False,
        prompt_text="Where do you want to expose Omero?",
        effects=[prompt_if_flags("expert")],
    )



class KeyPair(pydantic.BaseModel):
    public_key: str = pydantic.Field(
        prompt_text="What private key do you want?",
        effects=[prompt_if_flags("expert")],
    )
    private_key: str = pydantic.Field(
        prompt_text="What private key do you want?",
        effects=[prompt_if_flags("expert")],
    )

    @pydantic.root_validator(pre=True)
    def key_validator(cls, values):
        if values:
            if "private_key" in values and "public_key" in values:
                if values["private_key"] == values["public_key"]:
                    raise ValueError("Private and Public keys cannot be the same")
            else:
                raise ValueError("You must provide both a public and private key or None")
                
        else:
            try:
                import cryptography
                from cryptography.hazmat.backends import default_backend as crypto_default_backend
                from cryptography.hazmat.primitives import serialization as crypto_serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
            except ImportError:
                raise ImportError("Either provide a public key or pivate_key or install `cryptography` to use this feature")

            values = {}
            key = rsa.generate_private_key(
                backend=crypto_default_backend(), public_exponent=65537, key_size=2048
            )

            private_key = key.private_bytes(
                crypto_serialization.Encoding.PEM,
                crypto_serialization.PrivateFormat.PKCS8,
                crypto_serialization.NoEncryption(),
            ).decode()

            public_key = (
                key.public_key()
                .public_bytes(
                    crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
                )
                .decode()
            )

            values["private_key"] = private_key
            values["public_key"] = public_key
        
        return values




class Setup(pydantic.BaseModel):
    """This is the Arkitekt Server Setup

    We can help you setup your services in various configurations

    """
    _prelude = "Welcome to the Arkitekt Server\nLets setup your deployment"
    _confirm = "The setup for the service $name has been concluded. Are you happy?"
    name: str = pydantic.Field(
        default="default",
        description="Name of the setup",
        prompt_text="The name of the Deployment",
    )

    admin_username: str = pydantic.Field(
        alias="adminUsername",
        prompt_text="Your Admin username",
        default="admin",
        prompt=True,
    )
    admin_password: str = pydantic.Field(
        alias="adminPassword",
        default="admin",
        description="Password for the admin user",
        hide_input=True,
        confirmation_prompt=True,
        prompt=True,
        title="Admin Password",
        prompt_text="Please set your admin password",
    )
    jwt_key_pair: KeyPair = pydantic.Field(
        default_factory=KeyPair,
        prompt_text="Do you want to add a key pair?",
        effects=[prompt_if_flags("advanced")],
    )
    token_expiration: int = pydantic.Field(
        default=3600,
        prompt_text="What private key do you want?",
        effects=[prompt_if_flags("expert")],
    )
    postgres_password: str = pydantic.Field(
        default_factory=lambda: secrets.token_hex(16),
        prompt_text="What should your postgress password be?",
        effects=[prompt_if_flags("advanced")],
    )
    postgres_user: str = pydantic.Field(
        default_factory=lambda: namegenerator.gen(separator=""),
        prompt_text="What should your postgres username be?",
        effects=[prompt_if_flags("advanced")],
    )
    minio_root_user: str = pydantic.Field(
        prompt_text="What should your postgress password be?",
        effects=[prompt_if_flags("advanced")],
        default_factory=lambda: namegenerator.gen(separator=""),
    )
    minio_root_password: str = pydantic.Field(
        prompt_text="What should your minio password be?",
        effects=[prompt_if_flags("advanced")],
        default_factory=lambda: secrets.token_hex(16),
    )
    groups: List[Group] = pydantic.Field(
        default_factory=lambda: [Group(name="demo", description="A demo group")], prompt_text="Do you want to add some groups?", prompt=True
    )
    users: List[User] = pydantic.Field(
        default_factory=lambda: [User(username="demo", password="demo", groups=["demo"])], prompt_text="Do you want to add some users?", prompt=True
    )
    static_tokens: Dict[str, StaticToken] = pydantic.Field(
        default_factory=dict,
        prompt_text="Do you want to add some developer tokens?",
        effects=[prompt_if_flags("advanced")],
        key_prompt_text="What should be the Token?",
    )

    orkestrator: OrkestratorService = pydantic.Field(
        default=Service(),
        prompt_text="Lets setup orkestrator",
        should_prompt=[prompt_if_flags("advanced")],
    )
    rekuest: RekuestService = pydantic.Field(
        default=Service(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    lok: LokService = pydantic.Field(
        default=LokService(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    lok_next: LokNextService = pydantic.Field(
        default=LokNextService(),
        prompt_text="Lets setup lok_next",
        effects=[prompt_if_flags("advanced")],
    )
    fluss: FlussService = pydantic.Field(
        default=Service(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    minio: Service = pydantic.Field(
        default=Service(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    mikro: MikroService = pydantic.Field(
        default=Service(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    port: PortService = pydantic.Field(
        default=Service(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    kluster: KlusterService = pydantic.Field(
        default=KlusterService(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced")],
    )
    kluster_gateway: GatewayService = pydantic.Field(
        default=GatewayService(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced"), value_set("omero_ark.enabled")],
    )
    omero_ark: OmeroArkService = pydantic.Field(
        default=OmeroArkService(),
        prompt_text="Lets setup Omero Ark",
        effects=[prompt_if_flags("advanced")],
    )
    omero_server: OmeroServerService = pydantic.Field(
        default=OmeroServerService(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced"), value_set("omero_ark.enabled")],
    )
    omero_web: OmeroWebService = pydantic.Field(
        default=OmeroWebService(),
        prompt_text="Lets setup orkestrator",
        effects=[prompt_if_flags("advanced"), value_set("omero_ark.enabled")],
    )


    class Config:
        allow_population_by_field_name = True


    def get_buckets(self):
        """Utility to get all the buckets in the setup"""
        buckets = []

        for key, item in self.__dict__.items():
            if isinstance(item, Service):
                if item.bucket:
                    buckets.append(item.bucket)


        return buckets

    def get_db_names(self):
        """Utility to get all the db names in the setup"""
        db_names = []

        for key, item in self.__dict__.items():
            if isinstance(item, Service):
                db_names.append(item.db_name)


        return db_names

        

    @pydantic.validator("name", pre=True)
    def name_validator(cls, v):
        return v.lower()
    