import logging
import datetime

from app.util.db import source
from app.util.config import settings

logger = logging.getLogger(__name__)


class MemberSchedulerSettingDA(object):
    source = source

    @classmethod
    def get_setting(cls, member_id):
        return cls.__get_data('member_id', member_id)

    @classmethod
    def __get_data(cls, key, value):
        query = ("""
        SELECT member_id, date_format, time_format, start_time, time_interval,
            start_day, drag_method, create_date, update_date 
        FROM member_scheduler_setting WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    member_id,
                    date_format,
                    time_format,
                    start_time,
                    time_interval,
                    start_day,
                    drag_method,
                    create_date,
                    update_date
            ) in cls.source.cursor:
                setting = {
                    "member_id": member_id,
                    "date_format": date_format,
                    "time_format": time_format,
                    "start_time": start_time,
                    "time_interval": time_interval,
                    "start_day": start_day,
                    "drag_method": drag_method,
                    "create_date": create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "update_date": update_date.strftime("%m/%d/%Y %H:%M:%S"),
                }

                return setting

        return None

    @classmethod
    def set(cls, member_id, date_format, time_format, start_time,
                 time_interval, start_day, drag_method,
                 commit=True):
        try:
            query = ("""
            INSERT INTO member_scheduler_setting (member_id, date_format,
            time_format, start_time, time_interval, start_day, drag_method) VALUES (%s, %s,
            %s, %s, %s, %s, %s) ON conflict(member_id) DO UPDATE SET date_format =
            %s, time_format = %s, start_time = %s, time_interval = %s, start_day
            = %s, drag_method = %s RETURNING member_id
            """)
            
            # store info
            params_value = (member_id, date_format, time_format, start_time, time_interval, start_day, drag_method,
                date_format, time_format, start_time, time_interval, start_day, drag_method)
            res = cls.source.execute(query, params_value)

            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchall()
                id = result[0][0]

            if commit:
                cls.source.commit()

            return id

        except Exception as e:
            return None