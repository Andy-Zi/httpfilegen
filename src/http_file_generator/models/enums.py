from enum import StrEnum


class METHOD(StrEnum):
    OPTIONS = "OPTIONS"
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    TRACE = "TRACE"
    CONNECT = "CONNECT"
    GRAPHQL = "GRAPHQL"
    GRPC = "GRPC"
    WS = "WS"
