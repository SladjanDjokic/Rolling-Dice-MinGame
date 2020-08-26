import logging
import datetime

from app.util.db import source
from app.util.config import settings

logger = logging.getLogger(__name__)


class MemberScheduleHolidayDA(object):
    source = source

    @classmethod
    def get_holidays(cls, holiday_creator_member_id, search_time_start = None, search_time_end = None):
        return cls.__get_data('holiday_creator_member_id', holiday_creator_member_id)

    @classmethod
    def __get_data(cls, key, value):
        query = ("""
        SELECT
            id, holiday_creator_member_id, holiday_name, holiday_type, holiday_recurrence, 
            create_date, update_date
        FROM schedule_holiday WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)

        holidays = []

        if cls.source.has_results():
            for (
                    id,
                    holiday_creator_member_id,
                    holiday_name,
                    holiday_type,
                    holiday_recurrence,
                    create_date,
                    update_date
            ) in cls.source.cursor:
                holiday = {
                    "id": id,
                    "holiday_creator_member_id": holiday_creator_member_id,
                    "holiday_name": holiday_name,
                    "holiday_type": holiday_type,
                    "holiday_recurrence": holiday_recurrence,
                    "create_date": create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "update_date": update_date.strftime("%m/%d/%Y %H:%M:%S"),
                }
                holidays.append(holiday)

        return holidays        

    @classmethod
    def add(cls, holiday_creator_member_id, holiday_name, holiday_type, holiday_recurrence,
                 commit=True):
        try:
            query = ("""
            INSERT INTO schedule_holiday (holiday_creator_member_id, holiday_name,
            holiday_type, holiday_recurrence) VALUES (%s, %s,
            %s, %s) RETURNING id
            """)
            
            # store info
            params_value = (holiday_creator_member_id, holiday_name, holiday_type, holiday_recurrence)
            res = cls.source.execute(query, params_value)

            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]

            if commit:
                cls.source.commit()

            return id
            
        except Exception as e:
            return None