from herre.graphical import GraphicalBackend
from herre import get_current_herre

class UserDeniedAssignation(Exception):
    pass



def fill_args_kwargs_graphically(node, args, kwargs, parent=None):

    with GraphicalBackend(parent=parent):
        from arkitekt.ui.assign_widget import AssignWidget
        assignWidget = AssignWidget(node=node,set_args=args, set_kwargs=kwargs)
        if assignWidget.exec_():
            return assignWidget.args_kwargs_tuple
        else:
            raise UserDeniedAssignation("User Rejected an Assignation")


async def afill_args_kwargs_graphically(node, args, kwargs, parent=None):

    async with GraphicalBackend(parent=parent):
        from arkitekt.ui.assign_widget import AssignWidget
        assignWidget = AssignWidget(node=node,set_args=args, set_kwargs=kwargs)
        if assignWidget.exec_():
            return assignWidget.args_kwargs_tuple
        else:
            raise UserDeniedAssignation("User Rejected an Assignation")






