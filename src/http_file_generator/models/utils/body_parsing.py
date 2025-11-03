from typing import Union
from openapi_pydantic.v3.v3_1 import (
    Parameter as Parameter3_1,
    RequestBody as RequestBody3_1,
    ParameterLocation as ParameterLocation3_1,
    Operation as Operation3_1,
    Reference as Reference3_1,
    Example as Example3_1,
)
from openapi_pydantic.v3.v3_0 import (
    Parameter as Parameter3_0,
    RequestBody as RequestBody3_0,
    ParameterLocation as ParameterLocation3_0,
    Operation as Operation3_0,
    Reference as Reference3_0,
    Example as Example3_0,
)
from jsf import JSF


Parameter = Union[Parameter3_0, Parameter3_1]
RequestBody = Union[RequestBody3_0, RequestBody3_1]
Reference = Union[Reference3_0, Reference3_1]
Example = Union[Example3_0, Example3_1]
ParameterLocation = Union[ParameterLocation3_0, ParameterLocation3_1]
Operation = Union[Operation3_0, Operation3_1]


def handle_body(
    path: str, requestBody: RequestBody | Reference | None
) -> dict[str, tuple[Reference | Example, dict]]:
    """
    Handle parameters in the request path.
    """
    out = {}
    # Accept duck-typed RequestBody objects (with 'content' attribute)
    if requestBody is not None and hasattr(requestBody, "content"):
        for media_type, content_item in requestBody.content.items():
            if content_item.example:
                body = content_item.example
            elif content_item.examples:
                body = next(iter(content_item.examples.values()))
            elif content_item.media_type_schema:
                body = (
                    _generate_sample_body_from_schema(
                        content_item.media_type_schema.model_dump(
                            by_alias=True, exclude_none=True
                        )
                    )
                    or {}
                )
            else:
                body = {}
                media_type = None
            content_type_header = {"Content-Type": media_type} if media_type else {}
            out[media_type] = (body, content_type_header)
    return out


def _generate_sample_body_from_schema(schema: dict) -> dict:
    """Generate a sample dict conforming to the given JSON schema using jsf."""
    try:
        faker = JSF(schema=schema, allow_none_optionals=0)
        sample = faker.generate(n=1, use_defaults=True, use_examples=True)
        if isinstance(sample, list):
            if sample:
                return sample[0]
            else:
                return {}
        elif not isinstance(sample, dict):
            return {}
        return sample
    except Exception as e:
        raise ValueError(f"Failed to generate sample from schema: {e}")
