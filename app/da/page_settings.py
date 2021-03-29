import logging
logger = logging.getLogger(__name__)
from app.util.db import source

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
    def update_member_page_settings(cls, id, page_type, view_type, page_size, sort_order):
        try:
            sort_order_list = list(sort_order.split(','))
            query = ("""
                UPDATE member_page_settings
                SET
                    page_type = %s,
                    view_type = %s,
                    page_size = %s,
                    sort_order = %s,
                    update_date = CURRENT_TIMESTAMP
                WHERE id = %s
            """)
            params = (page_type, view_type, page_size, sort_order_list, id)
            cls.source.execute(query, params)
            cls.source.commit()
            return True
        except Exception as err:
            logger.error(err, exc_info=True)
            raise err
