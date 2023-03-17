from mikro.api.schema import *
from arkitekt import easy
from rekuest.widgets import SearchWidget

app = easy("easy_widget")

SEARCH_OBJECTIVES = SearchWidget(
    query="""
     query search($search: String) {
        options: objectives(name: $search, app: "easy_widget") { 
            label: name 
            value: id
        }
     }
    """,  # we can use the app name to filter the objectives (only those created by this app will be shown)
    ward="mikro",
)


@app.rekuest.register(widgets={"objective": SEARCH_OBJECTIVES})
def acquire_2d(
    position: PositionFragment, objective: Optional[ObjectiveFragment]
) -> RepresentationFragment:
    """Acquire hhhh

    Acquire a 2D snap of an image"""
    OmeroRepresentationInput(
        position=position,
        acquisitionDate=datetime.datetime.now(),
        physicalSize=PhysicalSizeInput(x=1, y=1, z=1, c=1, t=1),
        objective=objective,
    )


with app:
    l = create_objective(
        serial_number="123", name="test"
    )  # this app will be registered as having created the objective
    app.rekuest.run()
