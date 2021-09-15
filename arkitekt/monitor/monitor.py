from arkitekt.messages.postman.log import LogLevel
from contextvars import ContextVar
from rich.console import ConsoleRenderable
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from herre.console.context import get_current_console

current_monitor: ContextVar["Monitor"] = ContextVar('current_monitor', default=None)


def get_current_monitor():
    global current_monitor
    return current_monitor.get()


class ReservationPanel:

    def __init__(self, monitor: "Monitor", reservation) -> None:
        self.monitor = monitor
        self.reservation = reservation

    def start(self):
        heading_information = Table.grid(expand=True)
        heading_information.add_column()
        heading_information.add_column(style="green")

        reserving_table = Table(title=f"[bold green]Reserving on ...", show_header=False)

        for key, value in self.reservation.params.dict().items():
            reserving_table.add_row(key, str(value))

        heading_information.add_row(self.reservation.node.__rich__(), reserving_table)

        self.table = Table()
        self.table.add_column("Level")
        self.table.add_column("Message")

        columns = Table.grid(expand=True)
        columns.add_column()

        columns.add_row(heading_information)
        columns.add_row(self.table)

        self.monitor.addRow(Panel(columns, title="Reservation"))

    def end(self):
        pass

    def log(self, message: str, level: LogLevel = LogLevel.INFO):
         self.table.add_row(level, f"{message}")

class ActorPanel:

    def __init__(self, monitor: "Monitor", actor) -> None:
        self.monitor = monitor
        self.actor = actor

    def start(self):
        heading_information = Table.grid(expand=True)
        heading_information.add_column()
        heading_information.add_column(style="green")

        reserving_table = Table(title=f"[bold green]Provision on ...", show_header=False)

        heading_information.add_row(self.actor.template.node.__rich__())

        self.table = Table()
        self.table.add_column("Level")
        self.table.add_column("Message")

        columns = Table.grid(expand=True)
        columns.add_column()

        columns.add_row(heading_information)
        columns.add_row(self.table)

        self.monitor.addRow(Panel(columns, title="Provision"))

    def end(self):
        pass

    def log(self, message: str, level: LogLevel = LogLevel.INFO):
        self.table.add_row(level, f"{message}")


class AgentPanel:

    def __init__(self, monitor: "Monitor", provision) -> None:
        self.monitor = monitor
        self.provision = provision

    def start(self):
        heading_information = Table.grid(expand=True)
        heading_information.add_column()
        heading_information.add_column(style="green")


        self.table = Table()
        self.table.add_column("Template")
        self.table.add_column("Agent")

        columns = Table.grid(expand=True)
        columns.add_column()

        columns.add_row(heading_information)
        columns.add_row(self.table)

        self.monitor.addRow(Panel(columns, title="Agent Facts"))

    def end(self):
        pass

    def add_to_actor_map(self, template, actor):
        self.table.add_row(f"{template.id} - {template.node.name}", f"{actor.__name__}")



class Monitor:

    def __init__(self, title="Monitor", log=False) -> None:
        """Monitor allows you to monitor the progress of what is happenening inside your application


        Args:
            title (str, optional): The Title of this Monitor (Is the Panels Title). Defaults to "Monitor".
            progress (bool, optional): Do you want to monitor the progress of assignments and reservations? Defaults to False.
        """
        self.columns = Table.grid(expand=True)
        self.columns.add_column()
        self.log = log
        self.panel = Panel(self.columns, title=title)
        self.live = Live(self.panel, refresh_per_second=4, console=get_current_console())


    def create_reservation_panel(self, reservation):
        return ReservationPanel(self, reservation)

    def create_actor_panel(self, provision):
        return ActorPanel(self, provision)

    def create_agent_panel(self, agent):
        return AgentPanel(self, agent)

    def addRow(self, renderable: ConsoleRenderable):
        self.columns.add_row(renderable)

    def __aenter__(self):
        '''Convenience Method'''
        return self.__aenter__()

    def __aexit__(self,*args,**kwargs):
        self.__exit__(*args,**kwargs)

    def __enter__(self):
        current_monitor.set(self)
        self.live.__enter__()
        return self


    def __exit__(self, *args, **kwargs):
        self.live.__exit__(*args, **kwargs)
        current_monitor.set(None)
