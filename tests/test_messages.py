from arkitekt.messages import (
    Assignation,
    AssignationStatus,
)


def test_update_message():

    x = Assignation(assignation=1, status=AssignationStatus.PENDING, kwargs={"a": 1})
    y = Assignation(
        assignation=1, status=AssignationStatus.RETURNED, args=["nana"], kwargs=None
    )

    x.update(y)
    assert x.status == AssignationStatus.RETURNED, "Status should be updated"
    assert x.kwargs == {"a": 1}, "Kwargs should have not been updated"


def test_update_message():

    x = Assignation(assignation=1, status=AssignationStatus.PENDING, kwargs={"a": 1})
    y = Assignation(
        assignation=1, status=AssignationStatus.RETURNED, args=["nana"], kwargs=None
    )

    t = x.update(y, in_place=False)
    assert x.status == AssignationStatus.PENDING, "Status should have not been updated"
    assert x.kwargs == {"a": 1}, "Kwargs should have not been updated"

    assert (
        t.status == AssignationStatus.RETURNED
    ), "Status of copy should have been updated"
    assert t.kwargs == {"a": 1}, "Kwargs  of copy should have not been updated"
