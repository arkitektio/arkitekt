import websockets
from arkitekt.agents.transport.base import AgentTransport
import asyncio
import json
from arkitekt.agents.transport.errors import (
    AssignationListDeniedError,
    ProvisionListDeniedError,
)
from arkitekt.agents.transport.protocols.agent_json import *


async def token_loader():
    raise NotImplementedError(
        "Websocket transport does need a defined token_loader on Connection"
    )


class WebsocketAgentTransport(AgentTransport):
    def __init__(
        self,
        *args,
        ws_url="ws://localhost:8090/agi/",
        instance_id=None,
        token_loader=token_loader,
        provide_callback=None,
        assign_callback=None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.retries = 5
        self.time_between_retries = 5
        self.connection_alive = False
        self.connection_dead = False
        self.token_loader = token_loader
        self.ws_url = ws_url
        self.instance_id = instance_id
        self.provide_callback = provide_callback
        self.assign_callback = assign_callback
        self.futures = {}
        self.broadcast = None

    async def aconnect(self):
        assert self.broadcast is not None, "Broadcast must be defined"
        self.send_queue = asyncio.Queue()
        self.connection_task = asyncio.create_task(self.websocket_loop())

    async def websocket_loop(self, retry=0):
        send_task = None
        receive_task = None
        try:
            token = await self.token_loader()
            assert self.instance_id, "Needs an instance id"
            async with websockets.connect(
                f"{self.ws_url}?token={token}&instance_id={self.instance_id}"
            ) as client:

                send_task = asyncio.create_task(self.sending(client))
                receive_task = asyncio.create_task(self.receiving(client))

                self.connection_alive = True
                self.connection_dead = False
                done, pending = await asyncio.wait(
                    [send_task, receive_task],
                    return_when=asyncio.FIRST_EXCEPTION,
                )
                self.connection_alive = True

                for task in pending:
                    task.cancel()

                for task in done:
                    raise task.exception()

        except Exception as e:
            print("Error on Websockets", e)
            raise e

    async def sending(self, client):
        try:
            while True:
                message = await self.send_queue.get()
                await client.send(message)
                self.send_queue.task_done()
        except asyncio.CancelledError as e:
            print("Sending Task sucessfully Cancelled")

    async def receiving(self, client):
        try:
            async for message in client:
                await self.receive(message)
        except asyncio.CancelledError as e:
            print("Receiving Task sucessfully Cancelled")

    async def receive(self, message):
        json_dict = json.loads(message)
        if "type" in json_dict:
            type = json_dict["type"]
            id = json_dict["id"]
            print(json_dict)

            # State Layer
            if type == AgentSubMessageTypes.ASSIGN:
                await self.broadcast(AssignSubMessage(**json_dict))

            if type == AgentSubMessageTypes.PROVIDE:
                await self.broadcast(ProvideSubMessage(**json_dict))

            if type == AgentMessageTypes.LIST_ASSIGNATIONS_REPLY:
                self.futures[id].set_result(AssignationsListReply(**json_dict))
            if type == AgentMessageTypes.LIST_ASSIGNATIONS_DENIED:
                self.futures[id].set_exception(
                    AssignationListDeniedError(json_dict["error"])
                )

            if type == AgentMessageTypes.LIST_PROVISIONS_REPLY:
                self.futures[id].set_result(ProvisionListReply(**json_dict))
            if type == AgentMessageTypes.LIST_PROVISIONS_DENIED:
                self.futures[id].set_exception(
                    ProvisionListDeniedError(json_dict["error"])
                )

        else:
            print(f"Error {json_dict}")

    async def list_provisions(
        self, exclude: Optional[ProvisionStatus] = None
    ) -> List[Provision]:
        action = ProvisionList(exclude=exclude)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        prov_list_reply: ProvisionListReply = await self.futures[str(action.id)]
        return prov_list_reply.provisions

    async def change_provision(
        self,
        id: str,
        status: ProvisionStatus = None,
        message: str = None,
        mode: ProvisionMode = None,
    ):
        action = ProvisionChangedMessage(
            provision=id, status=status, message=message, mode=mode
        )
        await self.send_queue.put(action.json())

    async def change_assignation(
        self,
        id: str,
        status: AssignationStatus = None,
        message: str = None,
        returns: List[Any] = None,
    ):
        action = AssignationChangedMessage(
            assignation=id, status=status, message=message, result=returns
        )
        await self.send_queue.put(action.json())

    async def list_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        action = AssignationsList(exclude=exclude)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        ass_list_reply: AssignationsListReply = await self.futures[str(action.id)]
        return ass_list_reply.assignations
