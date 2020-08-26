import logging
import datetime

from app.util.db import source
from app.util.config import settings

logger = logging.getLogger(__name__)


class MemberScheduleEventDA(object):
    source = source

    @classmethod
    def get_eventById(cls, id):
        return cls.__get_data('id', id)

    @classmethod
    def get_eventById_full(cls, id):
        return cls.__get_data_full('id', id)

    @classmethod
    def check_eventExistanceById(cls, id):
        events = cls.__get_data('id', id)
        if len(events) == 0:
            return False
        
        return True

    @classmethod
    def get_events_full(cls, member_id, search_time_start = None, search_time_end = None):
        return cls.__get_data_full('event_host_member_id', member_id, search_time_start, search_time_end)

    @classmethod
    def __get_data(cls, key, value):
        query = ("""
        SELECT * FROM schedule_event WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)

        events = []
        if cls.source.has_results():
            for (
                id,
                event_name,
                event_host_member_id,
                event_type,
                event_datetime_start,
                event_datetime_end,
                event_location_address,
                event_location_postal,
                event_recurrence,
                event_image,
                create_date,
                update_date
            ) in cls.source.cursor:
                event = {
                    "id": id,
                    "event_name": event_name,
                    "event_host_member_id": event_host_member_id,
                    "event_type": event_type,
                    "event_datetime_start": event_datetime_start.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_datetime_end": event_datetime_end.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_location_address": event_location_address,
                    "event_location_postal": event_location_postal,
                    "event_recurrence": event_recurrence,
                    "event_image": event_image,
                    "create_date": create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "update_date": update_date.strftime("%m/%d/%Y %H:%M:%S"),
                }
                events.append(event)

        return events


    @classmethod
    def __get_data_full(cls, key, value, search_time_start = None, search_time_end = None):

        query_date = ""
        if search_time_start  and search_time_end:
            query_date =  ("""
                ((event_datetime_start between '{str_time_start}' and '{str_time_end}') 
                OR 
                (event_datetime_end between '{str_time_start}' and '{str_time_end}')) 
                AND """.format(str_time_start = search_time_start, str_time_end = search_time_end))            

        query = ("""
            select b.*, file_storage_engine.storage_engine_id from (
                (
                    select a.*, member_file.file_id as member_file_id from 
                    (
                        (
                            SELECT id, event_host_member_id, event_name, event_type,
                                event_datetime_start, 
                                event_datetime_end,
                                event_location_address, event_location_postal, 
                                event_recurrence, event_image,
                                event_invite_to_list,
                                create_date,
                                update_date 
                            FROM schedule_event WHERE {} {} = %s 
                        ) a 
                        left join member_file
                        on a.event_image = member_file.id
                    )
                ) b 
                left join file_storage_engine
                on b.member_file_id = file_storage_engine.id
            )
            """.format(query_date, key))
        
        params = (value,)        
        cls.source.execute(query, params)

        events = []
        if cls.source.has_results():
            for (
                id,
                event_host_member_id,
                event_name,
                event_type,
                event_datetime_start,
                event_datetime_end,
                event_location_address,
                event_location_postal,
                event_recurrence,
                event_image,
                event_invite_to_list,
                create_date,
                update_date,
                member_file_id,
                storage_engine_id
            ) in cls.source.cursor:
                event = {
                    "id": id,
                    "event_host_member_id": event_host_member_id,
                    "event_name": event_name,
                    "event_type": event_type,
                    "event_datetime_start": event_datetime_start.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_datetime_end": event_datetime_end.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_location_address": event_location_address,
                    "event_location_postal": event_location_postal,
                    "event_recurrence": event_recurrence,
                    "event_image": event_image,
                    "event_invite_to_list": event_invite_to_list,
                    "create_date": create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "update_date": update_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "member_file_id": member_file_id,
                    "storage_engine_id": storage_engine_id,
                }
                events.append(event)

        return events

    @classmethod
    def add(cls, event_name, event_host_member_id, event_type, event_datetime_start, event_datetime_end,
                event_recurrence, event_invite_to_list = None ,
                event_location_address = None, event_location_postal = None, event_image = None,
                commit=True):
        try:
            query = ("""
                INSERT INTO schedule_event (event_name, event_host_member_id,
                event_type, event_datetime_start, event_datetime_end,
                event_location_address, event_location_postal, event_recurrence, event_invite_to_list, event_image) VALUES (%s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """)
            
            # store info
            params_value = (event_name, event_host_member_id, event_type, event_datetime_start, event_datetime_end,
             event_location_address, event_location_postal, event_recurrence, event_invite_to_list, event_image)

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