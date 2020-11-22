import logging
import datetime

from app.util.db import source
from app.util.config import settings

logger = logging.getLogger(__name__)


class MemberEventDA(object):
    source = source

    @classmethod
    def get_event_by_id(cls, id):
        return cls.__get_data('id', id)

    @classmethod
    def get_event_by_id_full(cls, id):
        return cls.__get_data_full('id', id)

    @classmethod
    def check_event_existance_by_id(cls, id):
        events = cls.__get_data('id', id)
        if len(events) == 0:
            return False
        
        return True

    @classmethod
    def get_events_full(cls, member_id, search_time_start=None, search_time_end=None):
        return cls.__get_data_full('host_member_id', member_id, search_time_start, search_time_end)

    @classmethod
    def __get_data(cls, key, value):
        query = ("""
        SELECT
            id,
            name,
            description,
            host_member_id,
            event_type,
            event_status,
            duration_all_day,
            start_datetime,
            end_datetime,
            location_address,
            location_postal,
            event_image,
            recurrence,
            recr_cycle,
            recr_day_of_week,
            recr_day_of_month,
            recr_month_of_year,
            recr_occurrence_week,
            recr_start_date,
            recr_end_date,
            recr_max_occurrence,
            create_date,
            update_date
        FROM event WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)

        events = []
        if cls.source.has_results():
            for (
                id,
                name,
                description,
                host_member_id,
                event_type,
                event_status,
                duration_all_day,
                start_datetime,
                end_datetime,
                location_address,
                location_postal,
                event_image,
                recurrence,
                recr_cycle,
                recr_day_of_week,
                recr_day_of_month,
                recr_month_of_year,
                recr_occurrence_week,
                recr_start_date,
                recr_end_date,
                recr_max_occurrence,
                create_date,
                update_date
            ) in cls.source.cursor:
                event = {
                    'id':id,
                    'name':name,
                    'description':description,
                    'host_member_id':host_member_id,
                    'event_type':event_type,
                    'event_status':event_status,
                    'duration_all_day':duration_all_day,
                    'start_datetime':start_datetime,
                    'end_datetime':end_datetime,
                    'location_address':location_address,
                    'location_postal':location_postal,
                    'event_image':event_image,
                    'recurrence':recurrence,
                    'create_date':create_date,
                    'update_date':update_date
                }
                events.append(event)

        return events


    @classmethod
    def __get_data_full(cls, key, value, search_time_start=None, search_time_end=None):

        query_date = ""
        if search_time_start  and search_time_end:
            query_date =  ("""
                ((start_datetime between '{str_time_start}' and '{str_time_end}') 
                OR 
                (end_datetime between '{str_time_start}' and '{str_time_end}')) 
                AND """.format(str_time_start = search_time_start, str_time_end = search_time_end))            

        query = ("""
            SELECT 
                id,
                name,
                description,
                host_member_id,
                event_type,
                event_status,
                duration_all_day,
                start_datetime,
                end_datetime,
                location_address,
                location_postal,
                event_image,
                recurrence,
                recr_cycle,
                recr_day_of_week,
                recr_day_of_month,
                recr_month_of_year,
                recr_occurrence_week,
                recr_start_date,
                recr_end_date,
                recr_max_occurrence,
                create_date,
                update_date
            FROM event WHERE {} {}= %s
        """.format(query_date, key))
        
        params = (value,)

        cls.source.execute(query, params)

        events = []
        if cls.source.has_results():
            for (
                id,
                name,
                description,
                host_member_id,
                event_type,
                event_status,
                duration_all_day,
                start_datetime,
                end_datetime,
                location_address,
                location_postal,
                event_image,
                recurrence,
                recr_cycle,
                recr_day_of_week,
                recr_day_of_month,
                recr_month_of_year,
                recr_occurrence_week,
                recr_start_date,
                recr_end_date,
                recr_max_occurrence,
                create_date,
                update_date
            ) in cls.source.cursor:
                event = {
                    'id':id,
                    'name':name,
                    'description':description,
                    'host_member_id':host_member_id,
                    'event_type':event_type,
                    'event_status':event_status,
                    'duration_all_day':duration_all_day,
                    'start_datetime':start_datetime,
                    'end_datetime':end_datetime,
                    'location_address':location_address,
                    'location_postal':location_postal,
                    'event_image':event_image,
                    'recurrence':recurrence,
                    'create_date':create_date,
                    'update_date':update_date
                }
                events.append(event)
        return events
        
    @classmethod
    def add(cls, name, description,  host_member_id, event_type, event_status, duration_all_day,
                start_datetime, end_datetime, location_address=None,
                location_postal=None, event_image=None, recurrence='None',
                commit=True):
        try:
            query = ("""
                INSERT INTO event (name, description,  host_member_id, event_type, event_status, duration_all_day,
                start_datetime, end_datetime, location_address, location_postal, event_image, recurrence) VALUES (%s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """)
            
            # store info
            params = (name, description,  host_member_id, event_type, event_status, duration_all_day,
                start_datetime, end_datetime, location_address,
                location_postal, event_image, recurrence)

            cls.source.execute(query, params)

            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]

            if commit:
                cls.source.commit()

            return id

        except Exception as e:
            return None
    
    @classmethod
    def delete_event(cls, id):
        try:        
            query=("""
                DELETE FROM event WHERE id = {}
            """.format(id))            
            cls.source.execute(query)
            return True
        except Exception as e:
            return False

    @classmethod
    def update_event_by_id(cls, key, value, id):
        try:
            query=("""
                UPDATE event SET {}={} WHERE id = %s RETURNING id;
            """.format(key, value))
            params = (id,)
            cls.source.execute(query, params)

            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]

            if commit:
                cls.source.commit()

            return id
        except Exception as e:
            return None