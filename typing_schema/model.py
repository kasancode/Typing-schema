from typing import Literal, TypedDict

ValueTypeItem = Literal["string", "integer", "number", "boolean", "null"]

ValueType = ValueTypeItem | list[ValueTypeItem]


class BaseSchema(TypedDict, total=False):
    description: str | None


class ValueSchema(BaseSchema, total=False):
    type: ValueType
    default: str | int | float | bool | None


class ArraySchema(BaseSchema, total=False):
    type: Literal["array"]
    items: BaseSchema


class ObjectSchema(BaseSchema, total=False):
    type: Literal["object"]
    properties: dict[str, BaseSchema] | None
    required: list[str] | None
    additionalProperties: bool | None


class ConstraintSchema(BaseSchema, total=False):
    const: str | int | float | bool | None


class EnumSchema(BaseSchema, total=False):
    enum: list[str | int | float | bool | None]
    default: str | int | float | bool | None


class OneOfSchema(BaseSchema, total=False):
    oneOf: list[BaseSchema]
