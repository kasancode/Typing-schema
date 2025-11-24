import enum
from types import UnionType
from typing import (
    Annotated,
    Callable,
    Union,
    get_args,
    get_origin,
    is_typeddict,
    Literal,
)
from typing_schema.model import (
    ArraySchema,
    BaseSchema,
    ConstraintSchema,
    EnumSchema,
    ObjectSchema,
    OneOfSchema,
    ValueSchema,
)
from dataclasses import is_dataclass
import inspect

from importlib.util import find_spec


def _is_union(annotation: type) -> bool:
    """Check if a type annotation is Union."""
    origin = get_origin(annotation)
    return origin is Union or origin is UnionType


def _is_literal(annotation: type) -> bool:
    """Check if a type annotation is Literal."""
    origin = get_origin(annotation)
    return origin is Literal


def _is_array(annotation: type) -> bool:
    """Check if a type annotation is a sequence (like list or tuple)."""
    origin = get_origin(annotation)
    return origin in [list, tuple, set]


def _is_dict(annotation: type) -> bool:
    """Check if a type annotation is a dictionary."""
    origin = get_origin(annotation)
    return origin is dict


def _is_enum(annotation: type) -> bool:
    """Check if a type annotation is an Enum."""
    return isinstance(annotation, type) and issubclass(annotation, enum.Enum)


def _is_annotated(annotation: type) -> bool:
    """Check if a type annotation is a typing annotation."""
    origin = get_origin(annotation)
    return origin is Annotated


class _Converter:
    def __init__(
        self,
        raise_when_unsupported: bool = True,
        type_handler: Callable[[type], BaseSchema] | None = None,
        annotated_doc_handler: Callable[[tuple[type]], str] | None = None,
    ) -> None:
        self.to_doc = annotated_doc_handler or self._hande_annotated_doc
        self._raise_when_unsupported = raise_when_unsupported
        self._type_handler = type_handler

        self._enable_pydantic = find_spec("pydantic") is not None

    def _convert_pydantic_model(self, model: type) -> BaseSchema | None:
        """Convert a Pydantic model to a schema using Pydantic's built-in schema generation."""
        if self._enable_pydantic and hasattr(model, "model_json_schema"):
            return model.model_json_schema()

        return None

    def _hande_annotated_doc(self, args: tuple[type, ...]) -> str | None:
        """Extract documentation from an Annotated type."""
        for arg in args[1:]:
            if isinstance(arg, str):
                return arg
        return None

    def _convert_union(self, annotations: tuple[type, ...]) -> tuple[BaseSchema, bool]:
        """Convert a Union type annotation to a BaseSchema."""
        require = not (type(None) in annotations)

        if len(annotations) == 0:
            return ValueSchema(type="null"), False

        if len(annotations) == 1:
            return self._convert_core(annotations[0])[0], require

        schemas = [self._convert_core(ann)[0] for ann in annotations]

        if all(
            "type" in s.keys() and s["type"] not in ["array", "object"] for s in schemas  # type: ignore
        ):
            return (
                ValueSchema(type=[s["type"] for s in schemas]),  # type: ignore
                require,
            )

        return OneOfSchema(oneOf=schemas), require

    def _convert_function(self, func: Callable) -> tuple[BaseSchema, bool]:
        sig = inspect.signature(func)
        properties = {}
        required = []

        for name, param in sig.parameters.items():
            if (
                param.kind
                in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
                or param.name == "self"
            ):
                continue  # Skip *args and **kwargs

            test_annotation = param.annotation

            if param.annotation is inspect.Parameter.empty:
                if param.default is not inspect.Parameter.empty:
                    test_annotation = type(param.default)
                elif not self._raise_when_unsupported:
                    test_annotation = dict
                else:
                    raise ValueError(
                        f"Parameter '{name}' is missing a type annotation."
                    )

            schema, is_required = self._convert_core(test_annotation)
            if param.default is not inspect.Parameter.empty:
                schema["default"] = param.default  # type: ignore

            properties[name] = schema

            if is_required and param.default is inspect.Parameter.empty:
                required.append(name)

        obj_schema = ObjectSchema(
            type="object",
            properties=properties,
            required=required,
        )

        if hasattr(func, "__doc__") and func.__doc__:
            obj_schema["description"] = func.__doc__

        return obj_schema, True

    def _convert_core(self, object: type) -> tuple[BaseSchema, bool]:
        """Convert a Python type to a ValueSchema."""

        if self._type_handler:
            custom_schema = self._type_handler(object)
            if custom_schema:
                return custom_schema, True

        if self._enable_pydantic:
            pydantic_schema = self._convert_pydantic_model(object)
            if pydantic_schema:
                return pydantic_schema, True

        if _is_union(object):
            item_schema, required = self._convert_union(get_args(object))
            return item_schema, required

        if _is_array(object):
            item_schema, _ = self._convert_union(get_args(object))
            return (
                ArraySchema(type="array", items=item_schema),
                True,
            )

        if _is_annotated(object):
            args = get_args(object)
            item_schema, required = self._convert_core(args[0])

            if "description" not in item_schema:
                doc = self.to_doc(args)
                if doc:
                    item_schema["description"] = doc

            return item_schema, required

        if _is_literal(object):
            args = get_args(object)
            if len(args) == 0:
                return ValueSchema(type="null"), False

            if len(args) == 1:
                return ConstraintSchema(const=args[0]), True
            return EnumSchema(enum=list(args)), True

        if _is_enum(object):
            enum_values = [member.value for member in object]  # type: ignore
            return EnumSchema(enum=enum_values), True

        if is_typeddict(object) or is_dataclass(object):
            annotations = object.__annotations__
            required_items = []
            properties = {}

            for key, value in annotations.items():
                schema, is_required = self._convert_core(value)
                properties[key] = schema
                if is_required:
                    required_items.append(key)

            obj_schema = ObjectSchema(
                type="object", properties=properties, required=required_items
            )

            if hasattr(object, "__doc__") and object.__doc__:
                obj_schema["description"] = object.__doc__

            return obj_schema, True

        if _is_dict(object):
            return ObjectSchema(type="object"), True

        if object is type(None):
            return ValueSchema(type="null"), False

        mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            dict: "object",
            list: "array",
        }
        if object in mapping:
            return ValueSchema(type=mapping[object]), True  # type: ignore

        if callable(object):
            return self._convert_function(object)

        if self._raise_when_unsupported:
            raise ValueError(f"Unsupported type: {object}")
        else:
            return ObjectSchema(type="object"), True
