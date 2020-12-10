import psycopg2 as connector
from falcon import HTTPBadRequest as FalconHTTPBadRequest, HTTPNotFound as FalconHTTPNotFound, HTTPError


class BaseHTTPError(HTTPError):

    def to_dict(self, obj_type=dict):
        """Return a basic dictionary representing the error.

        This method can be useful when serializing the error to hash-like
        media types, such as YAML, JSON, and MessagePack.

        Args:
            obj_type: A dict-like type that will be used to store the
                error information (default ``dict``).

        Returns:
            dict: A dictionary populated with the error's title,
            description, etc.

        """

        obj = obj_type()

        obj['error'] = self.title

        if self.description is not None:
            obj['description'] = self.description

        if self.code is not None:
            obj['code'] = self.code

        if self.link is not None:
            obj['link'] = self.link

        return obj


class DuplicateKeyError (connector.errors.UniqueViolation):
    pass


class DataMissingError (connector.errors.NotNullViolation):
    pass


class RelationshipReferenceError (connector.errors.ForeignKeyViolation):
    pass


class HTTPBadRequest(FalconHTTPBadRequest, BaseHTTPError):
    pass


class HTTPNotFound(FalconHTTPNotFound, BaseHTTPError):
    pass
