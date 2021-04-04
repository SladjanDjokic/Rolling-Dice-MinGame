import logging
from app.util.db import source

logger = logging.getLogger(__name__)

class PageSettingsDA(object):
    source = source

    @classmethod
    def get_member_page_settings(cls, member_id):
        try:
            page_settings = []
            query = ("""
                SELECT
                    id,
                    page_type,
                    view_type,
                    page_size,
                    sort_order,
                    create_date,
                    update_date
                FROM member_page_settings
                WHERE member_id = %s
            """)
            params = (member_id,)
            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                    id,
                    page_type,
                    view_type,
                    page_size,
                    sort_order,
                    create_date,
                    update_date
                ) in cls.source.cursor:
                    page_setting = {
                        "id": id,
                        "page_type": page_type,
                        "view_type": view_type,
                        "page_size": page_size,
                        "sort_order": sort_order,
                        "create_date": create_date,
                        "update_date": update_date
                    }
                    page_settings.append(page_setting)
                return page_settings
            return None
        except Exception as err:
            logger.error(err, exc_info=True)
            raise err

    @classmethod
    def create_member_page_settings(cls, member_id, page_type, view_type, page_size, sort_order):
        try:
            sort_order_list = list(sort_order.split(','))

            query = ("""
                    INSERT INTO member_page_settings
                        (member_id, page_type, view_type, page_size, sort_order)
                    VALUES
                        (%s, %s, %s, %s, %s)
                    RETURNING *
                """)

            params = (member_id, page_type, view_type, page_size, sort_order_list)


            cls.source.execute(query, params)

            cls.source.commit()

            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                page_setting = {
                    "id": result[0],
                    "page_type": result[2],
                    "view_type": result[3],
                    "page_size": result[4],
                    "sort_order": result[5],
                    "create_date": result[6],
                    "update_date": result[7]
                }
                return page_setting

            return None
        except Exception as err:
            logger.error(err, exc_info=True)
            raise err


    @classmethod
    def update_member_page_settings(cls, id, member_id, page_type, view_type, page_size, sort_order):
        try:
            sort_order_list = list(sort_order.split(','))

            query = ("""
            INSERT INTO member_page_settings
                (member_id, page_type, view_type, page_size, sort_order)
            VALUES
                (%s, %s, %s, %s, %s)
            ON CONFLICT (member_id, page_type)
            DO UPDATE
            SET
                page_type = %s,
                view_type = %s,
                page_size = %s,
                sort_order = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE member_page_settings.id = %s
            RETURNING *
            """)

            params = (member_id, page_type, view_type, page_size, sort_order_list,
                      page_type, view_type, page_size, sort_order_list, id)

            cls.source.execute(query, params)

            cls.source.commit()

            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                page_setting = {
                    "id": result[0],
                    "page_type": result[2],
                    "view_type": result[3],
                    "page_size": result[4],
                    "sort_order": result[5],
                    "create_date": result[6],
                    "update_date": result[7]
                }
                return page_setting

            return None
        except Exception as err:
            logger.error(err, exc_info=True)
            raise err
