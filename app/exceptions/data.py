import psycopg2 as connector


class DuplicateKeyError (connector.errors.UniqueViolation):
    pass


class DataMissingError (connector.errors.NotNullViolation):
    pass


class RelationshipReferenceError (connector.errors.ForeignKeyViolation):
    pass
