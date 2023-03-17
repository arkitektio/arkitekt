from datetime import datetime
import json
from typing import List, Optional
from arkitekt import easy
import sqlalchemy
from mikro.api.schema import TableFragment, RepresentationFragment, FeatureFragment
from sqlalchemy import inspect
from sqlalchemy.engine.base import Connection
from sqlalchemy.sql import text
from rekuest.widgets import SearchWidget

app = easy("tableboy")

# Connect to postgres via sqlalchemy
engine = sqlalchemy.create_engine(
    "postgresql://arkitekt:6398045f7711b517ac0aa3c7e6b77a63@localhost/mikro_db"
)

inspector = inspect(engine)
print(inspector.get_columns("grunnlag_label"))


def create_label(instance, representation: RepresentationFragment, con: Connection):
    """Create a label for a given instance of a representation"""
    statement = text(
        """INSERT INTO grunnlag_label(instance, representation_id, name, created_at, creator_id) VALUES(:instance, :representation_id, :name, :created_at, :creator_id);
           SELECT currval('grunnlag_label_id_seq') AS id;
        """
    )

    data = {
        "instance": instance,
        "representation_id": representation.id,
        "name": str(instance),
        "created_at": datetime.now(),
        "creator_id": 1,
    }

    x = con.execute(statement, **data)
    return x.mappings().all()[0]["id"]


def create_feature(label, key, value, con: Connection):
    """Create a label for a given instance of a representation"""
    statement = text(
        """INSERT INTO grunnlag_feature(key, value, creator_id, label_id) VALUES(:key, :value, :creator_id, :label_id);
           SELECT currval('grunnlag_feature_id_seq') AS id;
        """
    )
    data = {
        "label_id": label,
        "key": key,
        "value": json.dumps(value),
        "creator_id": 1,
    }

    x = con.execute(statement, **data)
    return x.mappings().all()[0]["id"]
    # Create a label in the database


# with engine.connect() as con:

#     data = [{"key": "Area", "value": json.dumps(0.5), "label_id": 1}]

#     statement = text(
#         """INSERT INTO grunnlag_feature(key, label_id, value) VALUES(:key, :label_id, :value)"""
#     )

#     for line in data:


labelColumnWidget = SearchWidget(
    query="""
query ($table: ID!) {
  options: columnsof(id: $table, dtype: INT64) {
    value: name
    label: name
  }
}""",
    ward="mikro",
)

extractColumnWidget = SearchWidget(
    query="""
query ($table: ID!) {
  options: columnsof(id: $table) {
    value: name
    label: name
  }
}""",
    ward="mikro",
)


@app.rekuest.register(
    widgets={"take_columns": extractColumnWidget, "label_column": labelColumnWidget}
)
def table_to_features(
    table: TableFragment,
    representation: Optional[RepresentationFragment],
    label_column: str,
    take_columns: List[str] = None,
) -> int:
    """Table to Features

    Converts a table with features to features on the server.

    Args:
        table (TableFragment): Table with features
        representation (Optional[RepresentationFragment]): Representation to attach features to
        label_column (str, optional): Column with label. Defaults to "label".

    Returns:
        int: The amount of created features


    """
    representation = representation or table.representation
    table_data = table.data

    assert (
        label_column in table_data.columns
    ), f"Label column {label_column} not in table"
    assert representation, "No representation given"
    if take_columns:
        assert all(
            [column in table_data.columns for column in take_columns]
        ), "Take columns not in table"
        table_data = table_data[take_columns + [label_column]]

    table_data.set_index(label_column, inplace=True)

    with engine.connect() as con:
        for index, row in table_data.iterrows():
            label_id = create_label(index, representation, con)
            for key, value in row.items():
                create_feature(label_id, key, value, con)
                print(key, value)

    return 1


@app.rekuest.register()
def print_feature(feature: FeatureFragment):
    """Prints a feature

    Prints a feature

    Args:
        feature (FeatureFragment): Feature to print

    """
    print(feature)


if __name__ == "__main__":

    with app:

        app.rekuest.run()
