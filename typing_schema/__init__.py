from collections.abc import Callable
from typing_schema.converter import _Converter
from typing_schema.model import BaseSchema


def typing_to_schema(
    object: type,
    raise_when_unsupported: bool = True,
    type_handler: Callable[[type], BaseSchema] | None = None,
    annotated_doc_handler: Callable[[tuple[type]], str] | None = None,
) -> BaseSchema:
    """
    Convert a Python type or typing annotation to a schema representation.

    Parameters:
    - object (type): The Python type or typing annotation to convert
        (for example: `int`, `list[str]`, `Annotated[...]`, a dataclass, or a
        TypedDict).
    - raise_when_unsupported (bool): If True, raise `ValueError` when an
        unsupported type is encountered. If False, a generic `ObjectSchema`
        will be returned for unsupported types.
    - type_handler (Callable[[type], BaseSchema] | None): Optional custom
        handler that receives the type and may return a `BaseSchema`. If the
        handler returns a truthy schema the converter uses it and skips the
        built-in conversion logic.
    - annotated_doc_handler (Callable[[tuple[type]], str] | None): Optional
        handler to extract documentation text from an `Annotated[...]` type's
        extra arguments. It receives the full tuple returned by
        `typing.get_args(AnnotatedType)` and should return a string or `None`.

    Returns:
    - BaseSchema: The converted schema for the given type.

    Raises:
    - ValueError: If an unsupported type is encountered and
        `raise_when_unsupported` is True.
    """

    converter = _Converter(raise_when_unsupported, type_handler, annotated_doc_handler)
    schema, _ = converter._convert_core(object)
    return schema


def function_to_schema(
    func: Callable,
    raise_when_unsupported: bool = True,
    type_handler: Callable[[type], BaseSchema] | None = None,
    annotated_doc_handler: Callable[[tuple[type]], str] | None = None,
) -> BaseSchema:
    """Convert a function's argument annotations to an ObjectSchema.

    Parameters:
    - func (Callable): The function whose parameters will be converted. The
        converter reads parameter annotations and defaults from the function's
        signature.
    - raise_when_unsupported (bool): See `convert`.
    - type_handler (Callable[[type], BaseSchema] | None): See `convert`.
    - annotated_doc_handler (Callable[[tuple[type]], str] | None): See
        `convert`.

    Returns:
    - BaseSchema: An `ObjectSchema` where function parameters are mapped to
        properties and `required` lists parameters without defaults.

    Raises:
    - ValueError: If a parameter is missing an annotation and no default is
        provided, or if an unsupported type is encountered and
        `raise_when_unsupported` is True.
    """

    converter = _Converter(raise_when_unsupported, type_handler, annotated_doc_handler)
    schema, _ = converter._convert_function(func)
    return schema
