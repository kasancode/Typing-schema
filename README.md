
# Typing schema

Convert Python types and typing annotations (including `Annotated`, `Union`, `Literal`, `dataclasses`, `TypedDicts`, and `pydantic.BaseModel`) into a simple schema representation.

## Overview

This library provides utilities to transform Python type hints and function signatures into a JSON-like schema. It is useful for documenting or validating function inputs and the data structures described by Python typing constructs.
It can also generate parameter schemas compatible with OpenAI's function-calling API, making it easier to provide accurate function parameter definitions for model function calls.

Key features:
- Convert basic types (`str`, `int`, `float`, `bool`, `list`, `dict`) to simple value schemas.
- Convert `Union`, `Literal`, `Enum`, `Annotated` (with inline descriptions), `dataclasses`, `TypedDict`, and `pydantic.BaseModel` to object/oneOf/enum schemas.
- Convert a function signature into a schema that lists parameters, types, and required fields.
- Provide extension points: custom type handlers and annotated-doc handlers.


## Usage

Basic example using type annotations:

### Convert a typing annotation
```python
from schema_builder import typing_to_schema, function_to_schema
from typing import Annotated, Union, Literal

class Record(TypedDict):
    """The record item"""
    id: int
    name: str
    content: Annotated[str | None, "The content (Optional)"]

schema = typing_to_schema(Record)
print(json.dumps(schema, indent=2))
```

Output:
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "integer"
    },
    "name": {
      "type": "string"
    },
    "content": {
      "type": [
        "string",
        "null"
      ],
      "description": "The content (Optional)"
    }
  },
  "required": [
    "id",
    "name"
  ],
  "description": "The record item"
}
```

### Convert a function signature
```python
def func(a: int, b: str = 'x') -> None:
    """Example function"""
    pass

schema = function_to_schema(func)
print(json.dumps(schema, indent=2))
```
Output:
```json
{
  "type": "object",
  "properties": {
    "a": {
      "type": "integer"
    },
    "b": {
      "type": "string",
      "default": "x"
    }
  },
  "required": [
    "a"
  ],
  "description": "Example function"
}
```

## Extension points
- `type_handler`: pass a callback to `typing_to_schema` or `function_to_schema` to handle custom types. If it returns a schema the converter will use it.
- `annotated_doc_handler`: pass a callback to extract documentation from `Annotated[...]` metadata.

### Handle custom types

```python
def handler(type) -> dict | None:
    if (
        type is datetime.datetime
        or isinstance(type, datetime.date)
        or issubclass(type, datetime.date)
    ):
        return {"type": "string", "description": "Handled string type"}
    return None

schema = typing_to_schema(datetime.date, type_handler=handler)
print(json.dumps(schema, indent=2))
```
Output:
```json
{
  "type": "string",
  "description": "Handled string type"
}
```

### Extract documentation from `Annotated` metadata

By default, the first `str` value in `Annotated` metadata is used as the `description`.

```python
class Doc:
    def __init__(self, value: str):
        self.value = value

def doc_handler(args: tuple[type, ...]) -> str | None:
    for arg in args:
        if isinstance(arg, Doc):
            return arg.value
    return None

class Record(TypedDict):
    name: Annotated[str, Doc("The name of the person")]

schema = typing_to_schema(Record, annotated_doc_handler=doc_handler)
print(json.dumps(schema, indent=2))
```
output:
```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "The name of the person"
    }
  },
  "required": [
    "name"
  ]
}
```