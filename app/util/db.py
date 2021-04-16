import logging
import psycopg2 as connector
from pprint import pformat
from psycopg2 import errorcodes
from psycopg2.extras import LoggingConnection
import psycopg2.extras as extras

from app.config import settings
from app.exceptions.data import DataMissingError, DuplicateKeyError, \
    RelationshipReferenceError

logger = logging.getLogger(__name__)
ds_logger = logging.getLogger(__name__ + '.DataSource')


class DataSource (object):

    instance = None

    class __DataSource (object):
        def __str__(self):
            return repr(self) + self.config

        def __init__(self):
            self.cursor = None
            self.conn = None

        def connect(self):
            logging_level = settings.get("database.log_level")
            logger.debug(f"Database Logging Level: {logging_level}")
            if not logging_level:
                logging_level = settings.get("log_level")
                logger.debug(f"NO Database Logging Level - Using default: {logging_level}")

            ds_logger.setLevel(logging_level)

            try:
                ds_logger.debug("DB.py Connection: {} ".format(
                    pformat(DataSource.get_connection_config())))
                conn = connector.connect(
                    connection_factory=LoggingConnection,
                    **DataSource.get_connection_config()
                )
                conn.initialize(ds_logger)
            except connector.Error as err:
                if err.pgcode == errorcodes.INVALID_AUTHORIZATION_SPECIFICATION:  # noqa: E501
                    print("Something is wrong with your user name or password")
                elif err.pgcode == errorcodes.INVALID_SCHEMA_NAME:
                    print("Database does not exist")
                else:
                    print(err)
                raise
            self.conn = conn
            self.cursor = self.conn.cursor()

        def disconnect(self):
            self.cursor.close()
            return self.conn.close()

        def commit(self):
            return self.conn.commit()

        def rollback(self):
            return self.conn.rollback()

        def start_transaction(self):
            return self.conn.start_transaction()

        def get_last_row_id(self):
            result = self.cursor.fetchone()
            ds_logger.debug(f"QUERY RESULT: {result}")
            return result[0]

        def execute(self, query, params, bulk_insert=False, debug_query=True):
            try:
                if not self.cursor:
                    self.connect()
                ds_logger.debug(f"BULK_INSERT: {bulk_insert}")
                ds_logger.debug(f"EXECUTE_QUERY: {query}")
                ds_logger.debug(f"EXECUTE_PARAMS: {params}")
                if bulk_insert:
                    return extras.execute_values(self.cursor, query, params)
                else:
                    return self.cursor.execute(query, params)
            except connector.errors.UniqueViolation as err:
                self.rollback()
                raise DuplicateKeyError from err
            except connector.errors.NotNullViolation as err:
                self.rollback()
                raise DataMissingError from err
            except connector.errors.ForeignKeyViolation as err:
                self.rollback()
                raise RelationshipReferenceError from err
            except Exception:
                logger.exception("[FIXME]: Unknown Database Exception")
                logger.debug(f"EXECUTE_QUERY: {query}")
                logger.debug(f"EXECUTE_PARAMS: {params}")
                try:
                    self.rollback()
                except Exception:
                    logger.exception("[FIXME]: Exception Rolling Back")
                    pass

        def has_results(self):
            try:
                logger.debug("Rowcount: {}".format(self.cursor.rowcount))
                return self.cursor.rowcount != -1 and self.cursor.rowcount > 0
            except AttributeError:
                logger.exception("[FIXME]: self.cursor is none: "
                                 "rowcount doesn't exist")

            return False

    @staticmethod
    def get_connection_config():
        return {
            "user": settings.get("database.user"),
            "password": settings.get("database.password"),
            "host": settings.get("database.host"),
            "port": settings.get("database.port"),
            "database": settings.get("database.database"),
        }

    def __init__(self):
        if not DataSource.instance:
            DataSource.instance = DataSource.__DataSource()

    def __getattr__(self, name):
        return getattr(self.instance, name)


source = DataSource()


def formatSortingParams(sort_by, entity_dict):
    columns_list = sort_by.split(',')
    new_columns_list = list()

    for column in columns_list:
        if column[0] == '-':
            column = column[1:]
            column = entity_dict.get(column)
            if column:
                column = column + ' DESC'
                new_columns_list.append(column)
        else:
            column = entity_dict.get(column)
            if column:
                column = column + ' ASC'
                new_columns_list.append(column)

    return (',').join(column for column in new_columns_list)
