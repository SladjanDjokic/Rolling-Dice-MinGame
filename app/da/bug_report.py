import logging
from app.util.db import source

logger = logging.getLogger(__name__)


class BugReportDA(object):
    source = source

    @classmethod
    def create(cls, member_id, description, redux_state, member_file_id,
               browser_info, referer_url, current_url, commit=True):

        query = ("""
            INSERT INTO bug_report
                (member_id, description, redux_state,
                 screenshot_storage_id, browser_info,
                 referer_url, current_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (
            member_id, description, redux_state, member_file_id, browser_info,
            referer_url, current_url
        )
        try:
            cls.source.execute(query, params)
            report_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()
            return report_id
        except Exception as e:
            logger.error(e, exc_info=True)
            return False
