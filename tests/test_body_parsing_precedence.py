from http_file_generator.models.utils.body_parsing import handle_body


class Schema:
    def __init__(self, d) -> None:
        self._d = d

    def model_dump(self, **kwargs):
        return self._d


class Media:
    def __init__(self, example=None, examples=None, schema=None) -> None:
        self.example = example
        self.examples = examples
        self.media_type_schema = schema


class RequestBody:
    def __init__(self, content) -> None:
        self.content = content


def test_example_takes_precedence_over_examples() -> None:
    rb = RequestBody(
        {
            "application/json": Media(
                example={"chosen": True},
                examples={"ex": {"chosen": False}},
                schema=Schema({"type": "object"}),
            )
        }
    )
    out = handle_body("/x", rb)
    body, headers = out["application/json"]
    assert body == {"chosen": True}


def test_no_example_no_schema_leads_to_none_key_and_no_header() -> None:
    rb = RequestBody({"application/json": Media()})
    out = handle_body("/x", rb)
    assert None in out
    body, headers = out[None]
    assert body == {}
    assert headers == {}
