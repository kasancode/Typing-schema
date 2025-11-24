from dataclasses import dataclass
import dataclasses
import datetime
import enum
import json
from typing import Annotated, Literal, Optional, TypedDict, Union
from typing_schema import typing_to_schema, function_to_schema
from typing_schema.model import ArraySchema, BaseSchema, ObjectSchema, ValueSchema


def check(object, schema, expect_valid: bool = True):
    try:
        from jsonschema import validate, ValidationError  # type: ignore

        validate(instance=object, schema=schema)
        assert expect_valid, f"Validation failed: {object} should be invalid"
    except ValidationError as e:
        assert not expect_valid, f"Validation failed: {e.message}"
    except ImportError:
        print("jsonschema package is not installed. Skipping validation.")
        return


def test_object():
    d = ObjectSchema(
        type="object",
        required=["id", "name"],
        additionalProperties=False,
        properties={
            "id": ValueSchema(type="integer"),
            "name": ValueSchema(type="string"),
            "age": ValueSchema(type="integer"),
            "tags": ArraySchema(
                type="array",
                items=ValueSchema(type="string"),
            ),
        },
    )


TestType = str | int | None


class Record(TypedDict):
    """The record item"""

    id: int
    name: str
    content: Annotated[str | None, "Optional: The content"]


class Point3D(TypedDict):
    """A point in 3D space"""

    x: int
    y: int
    z: int | None
    label1: str | None
    label2: Optional[str]
    label3: Union[str, None]
    label4: str
    label5: TestType
    tags1: list[str] | None
    tags2: list[str | int | None]
    tags3: list[str | list[str]] | None
    size: Literal["small", "medium", "large"]
    mode: Literal["fast"]
    flag: Optional[bool]


class ColorStyle(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class NumberStyle(enum.IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3


class IdEnum(enum.IntEnum):
    ID_A = 100
    ID_B = 200
    ID_C = 300


@dataclass
class SampleData:
    """A sample data class"""

    id: int
    name: Annotated[str, "Name of the sample data"]
    values: list[float]
    active: bool
    metadata: Annotated[dict[str, str] | None, "Optional metadata"]
    content: dict


def test_typed_dict_type():
    schema = typing_to_schema(Record)
    print(json.dumps(schema, indent=2))
    object = Record(
        id=1,
        name="Test Record",
        content="This is a test.",
    )
    check(object, schema)

    schema = typing_to_schema(Point3D)
    print(json.dumps(schema, indent=2))
    object = Point3D(
        x=10,
        y=20,
        z=30,
        label2="Label2",
        label4="Label4",
        label5="Test",
        tags1=None,
        tags2=["tag1", 2],
        size="medium",
        mode="fast",
    )
    check(object, schema)

    object = Point3D(
        x=10,
        y=20,
        z=30,
        label1=None,
        label2="Label2",
        label4="Label4",
        label5="Test",
        tags2=["tag1", 2],
        size="medium",
        mode="fast",
    )
    check(object, schema)


def test_int_type():
    schema = typing_to_schema(int)
    print(json.dumps(schema, indent=2))

    check(42, schema)
    check("not an int", schema, expect_valid=False)


def test_dict_type():
    schema = typing_to_schema(dict)
    print(json.dumps(schema, indent=2))

    check({"key": "value"}, schema)
    check([1, 2, 3], schema, expect_valid=False)


def test_enum_type():
    schema = typing_to_schema(ColorStyle)
    print(json.dumps(schema, indent=2))

    check("red", schema)
    check(3, schema, expect_valid=False)

    schema = typing_to_schema(NumberStyle)
    print(json.dumps(schema, indent=2))

    check(1, schema)
    check("one", schema, expect_valid=False)

    schema = typing_to_schema(IdEnum)
    print(json.dumps(schema, indent=2))

    check(100, schema)
    check("ID_A", schema, expect_valid=False)


def test_dataclass_type():
    schema = typing_to_schema(SampleData)
    print(json.dumps(schema, indent=2))

    object = SampleData(
        id=1,
        name="Sample",
        values=[1.1, 2.2, 3.3],
        active=True,
        metadata={"author": "Alice"},
        content={"key": "value"},
    )

    check(dataclasses.asdict(object), schema)
    check("test", schema, expect_valid=False)


def test_func_args():
    def sample_function(
        a: int, b: SampleData, c=3.14, d: Optional[bool] = None
    ) -> None:
        """A sample function"""
        pass

    schema = typing_to_schema(sample_function)
    print(json.dumps(schema, indent=2))

    check(
        {
            "a": 10,
            "b": {
                "id": 1,
                "name": "Sample",
                "values": [1.1, 2.2],
                "active": True,
                "metadata": None,
                "content": {},
            },
            "c": 2.71,
            "d": True,
        },
        schema,
    )

    def handler(a: int, b: str = "x") -> None:
        """Example handler"""
        pass

    schema = typing_to_schema(handler)
    print(json.dumps(schema, indent=2))
    check(
        {
            "a": 5,
            "b": "test",
        },
        schema,
    )


def test_handle_typed():

    def handler(type):
        return {"type": "number", "description": "Handled by custom handler"}

    schema = typing_to_schema(int, type_handler=handler)
    print(json.dumps(schema, indent=2))
    check(42, schema)

    def handler(type):
        if (
            type is datetime.datetime
            or isinstance(type, datetime.date)
            or issubclass(type, datetime.date)
        ):
            return {"type": "string", "description": "Handled string type"}
        return None

    schema = typing_to_schema(datetime.date, type_handler=handler)
    print(json.dumps(schema, indent=2))
    check("2024-01-01", schema)


def test_handle_annotated_doc():
    doc = "Custom description for Annotated type"

    def doc_handler(args: tuple[type]) -> str | None:
        return doc

    schema = typing_to_schema(
        Annotated[int, 1],
        annotated_doc_handler=doc_handler,
    )

    print(json.dumps(schema, indent=2))
    check(1, schema)

    assert schema.get("description") == doc

    class Doc:
        def __init__(self, value: str):
            self.value = value

    class Data(TypedDict):
        name: Annotated[str, Doc("The name of the person")]

    def doc_handler(args: tuple[type, ...]) -> str | None:
        for arg in args:
            if isinstance(arg, Doc):
                return arg.value
        return None

    schema = typing_to_schema(Data, annotated_doc_handler=doc_handler)
    print(json.dumps(schema, indent=2))

    schema_props = schema.get("properties", {})
    check({"name": "Alice"}, schema)
    assert schema_props.get("name", {}).get("description") == "The name of the person"


def test_pydantic_model():
    try:
        from pydantic import BaseModel  # type: ignore
    except ImportError:
        print("pydantic is not installed. Skipping pydantic model test.")
        return

    class UserModel(BaseModel):
        """A user model"""

        id: int
        name: str
        email: Optional[str] = None
        roles: list[Literal["admin", "user", "guest"]]

    schema = typing_to_schema(UserModel)
    print(json.dumps(schema, indent=2))

    check(
        {
            "id": 1,
            "name": "Alice",
            "roles": ["admin", "user"],
        },
        schema,
    )
