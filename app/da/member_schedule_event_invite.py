import logging
import datetime

from app.util.db import source
from app.util.config import settings

logger = logging.getLogger(__name__)


class MemberScheduleEventInviteDA(object):
    source = source

    @classmethod
    def create_invite(cls, invitee_id, event_id, status='Tentative'):
        query = ("""
            INSERT INTO event_invite_2 (invite_member_id, event_id, invite_status)
            VALUES (%s, %s, %s)
            RETURNING id
        """)
        params = (invitee_id, event_id, status)
        cls.source.execute(query, params)
        id = None
        if cls.source.has_results():
            result = cls.source.cursor.fetchone()
            id = result[0]
        cls.source.commit()
        return id

    @classmethod
    def delete_invites_by_exception(cls, event_id, invite_ids_to_stay):
        query = ("""
            DELETE FROM event_invite_2
            WHERE event_id = %s AND event_invite_2.id != ALL(%s)
        """)
        params = (event_id, invite_ids_to_stay)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def delete_invites_by_event(cls, event_id):
        query = ("""
                DELETE FROM event_invite_2
                WHERE event_id = %s
            """)
        params = (event_id,)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def get_event_inviteById(cls, id):
        return cls.__get_data('id', id)

    @classmethod
    def get_event_inviteById_full(cls, id, search_time_start=None, search_time_end=None):
        return cls.__get_data_full('id', id, event_invite_to, search_time_start, search_time_end)

    @classmethod
    def get_event_invites_full(cls, event_invite_to, search_time_start=None, search_time_end=None):
        return cls.__get_data_full('event_invite_to', event_invite_to, search_time_start, search_time_end)

    @classmethod
    def __get_data(cls, key, value):
        query = ("""
        SELECT * FROM schedule_event_invite WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)

        invites = []

        if cls.source.has_results():
            for (
                    id,
                    event_id,
                    event_invite_to,
                    event_invite_status,
                    create_date,
                    update_date,
            ) in cls.source.cursor:
                invite = {
                    "id": id,
                    "event_id": event_id,
                    "event_invite_to": event_invite_to,
                    "event_invite_status": event_invite_status,
                    "create_date": create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "update_date": update_date.strftime("%m/%d/%Y %H:%M:%S"),
                }
                invites.append(invite)

        return invites

    @classmethod
    def __get_data_full(cls, key, value, search_time_start=None, search_time_end=None):

        query_date = ""
        if search_time_start and search_time_end:
            query_date = ("""
                where
                    ((event_datetime_start between '{str_time_start}' and '{str_time_end}') 
                    OR 
                    (event_datetime_end between '{str_time_start}' and '{str_time_end}'))
                """.format(str_time_start=search_time_start, str_time_end=search_time_end))

        query = ("""
            select b.*, file_storage_engine.storage_engine_id from (
                (
                    select a.*, member_file.file_id as member_file_id from 
                    (
                        (
                        select z.*,
                                schedule_event.event_host_member_id, schedule_event.event_name, schedule_event.event_type,
                                schedule_event.event_datetime_start, 
                                schedule_event.event_datetime_end,
                                schedule_event.event_location_address, schedule_event.event_location_postal,
                                schedule_event.event_recurrence, schedule_event.event_image,
                                schedule_event.create_date as event_create_date,
                                schedule_event.update_date as event_update_date
                            from (
                                (select * from schedule_event_invite where schedule_event_invite.{key} = %s) z
                                left join schedule_event 
                                on z.event_id = schedule_event. id
                            )
                            {query_date}
                        ) a 
                        left join member_file
                        on a.event_image = member_file.id
                    )
                ) b 
                left join file_storage_engine
                on b.member_file_id = file_storage_engine.id
            )
            """.format(key=key, query_date=query_date))

        params = (value,)
        cls.source.execute(query, params)

        invites = []
        if cls.source.has_results():
            for (
                id,
                event_id,
                event_invite_to,
                event_invite_status,
                create_date,
                update_date,
                event_host_member_id,
                event_name,
                event_type,
                event_datetime_start,
                event_datetime_end,
                event_location_address,
                event_location_postal,
                event_recurrence,
                event_image,
                event_create_date,
                event_update_date,
                member_file_id,
                storage_engine_id

            ) in cls.source.cursor:
                invite = {
                    "id": id,
                    "event_id": event_id,
                    "event_invite_to": event_invite_to,
                    "event_invite_status": event_invite_status,
                    "create_date": create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "update_date": update_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_host_member_id": event_host_member_id,
                    "event_name": event_name,
                    "event_type": event_type,
                    "event_datetime_start": event_datetime_start.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_datetime_end": event_datetime_end.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_location_address": event_location_address,
                    "event_location_postal": event_location_postal,
                    "event_recurrence": event_recurrence,
                    "event_image": event_image,
                    "event_create_date": event_create_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "event_update_date": event_update_date.strftime("%m/%d/%Y %H:%M:%S"),
                    "member_file_id": member_file_id,
                    "storage_engine_id": storage_engine_id,
                }
                invites.append(invite)

        return invites

    @classmethod
    def addSingle(cls, event_id, event_invite_to, commit=True):
        try:
            query = ("""
                INSERT INTO schedule_event_invite (event_id, event_invite_to, event_invite_status) 
                VALUES (%s, %s) RETURNING id
                """)

            logger.debug("query: {}".format(query))

            # store info
            params_value = (event_id, event_invite_to)

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

    @classmethod
    def addMultiple(cls, event_id, event_invite_to_list, commit=True):
        try:
            if (event_invite_to_list is None) or (len(event_invite_to_list) == 0):
                return list()

            query_values = ""

            for event_invite_to in event_invite_to_list:
                if query_values:
                    query_values += ", "
                query_values += ("""({event_id}, {event_invite_to})""".format(
                    event_id=event_id, event_invite_to=event_invite_to))

            query = ("""
                INSERT INTO schedule_event_invite (event_id, event_invite_to) 
                VALUES {} RETURNING id
                """.format(query_values))

            # store info
            params_value = ()
            res = cls.source.execute(query, params_value)

            entry = list()
            if cls.source.has_results():
                for entry_da in cls.source.cursor.fetchall():
                    entry.append(entry_da[0])

            if commit:
                cls.source.commit()

            return entry

        except Exception as e:
            return None

    @classmethod
    def setStatus(cls, event_invite_id, event_invite_status, commit=True):
        try:
            query = ("""
                UPDATE schedule_event_invite SET 
                event_invite_status = %s WHERE id = %s   
                RETURNING id
                """)

            # store info
            params_value = (event_invite_status, event_invite_id)

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
