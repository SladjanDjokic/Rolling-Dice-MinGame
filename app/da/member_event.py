import logging
import datetime

from app.util.db import source
import app.util.json as json
from app.util.config import settings
from app.exceptions.file_sharing import FileShareExists, FileNotFound, \
    FileUploadCreateException, FileStorageUploadError

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
                    'id': id,
                    'name': name,
                    'description': description,
                    'host_member_id': host_member_id,
                    'event_type': event_type,
                    'event_status': event_status,
                    'duration_all_day': duration_all_day,
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime,
                    'location_address': location_address,
                    'location_postal': location_postal,
                    'event_image': event_image,
                    'recurrence': recurrence,
                    'create_date': create_date,
                    'update_date': update_date
                }
                events.append(event)

        return events

    @classmethod
    def __get_data_full(cls, key, value, search_time_start=None, search_time_end=None):

        query_date = ""
        if search_time_start and search_time_end:
            query_date = ("""
                ((start_datetime between '{str_time_start}' and '{str_time_end}')
                OR
                (end_datetime between '{str_time_start}' and '{str_time_end}'))
                AND """.format(str_time_start=search_time_start, str_time_end=search_time_end))

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
                    'id': id,
                    'name': name,
                    'description': description,
                    'host_member_id': host_member_id,
                    'event_type': event_type,
                    'event_status': event_status,
                    'duration_all_day': duration_all_day,
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime,
                    'location_address': location_address,
                    'location_postal': location_postal,
                    'event_image': event_image,
                    'recurrence': recurrence,
                    'create_date': create_date,
                    'update_date': update_date
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

    # Sequence of recurring events
    @classmethod
    def add_sequence(cls, sequence_name):
        try:
            query = (
                """ INSERT INTO event_sequence (sequence_name) VALUES (%s) RETURNING id """)
            params = (sequence_name,)
            cls.source.execute(query, params)
            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]
            cls.source.commit()
            return id

        except Exception as e:
            return None

    # New method to add events to event_2
    @classmethod
    def add_2(cls, sequence_id, event_color_id, event_name, event_description, host_member_id,
              is_full_day, event_tz, start_datetime, end_datetime, event_type, event_recurrence_freq,
              end_condition, repeat_weekdays, end_date_datetime, location_mode, location_id, location_address, repeat_times):
        try:
            query = (
                """ INSERT INTO event_2
                    (sequence_id, event_color_id, event_name, event_description, host_member_id,
                    is_full_day, event_tz, start_datetime, end_datetime, event_type,
                    event_recurrence_freq, end_condition, repeat_weekdays, end_date_datetime, location_mode,
                    location_id, location_address, repeat_times)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """)
            params = (sequence_id, event_color_id, event_name, event_description, host_member_id,
                      is_full_day, event_tz, start_datetime, end_datetime, event_type, event_recurrence_freq,
                      end_condition, json.dumps(repeat_weekdays), end_date_datetime, location_mode, location_id, location_address, repeat_times)
            cls.source.execute(query, params)
            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]
            cls.source.commit()
            return id
        except Exception as e:
            return None

    # Here we bind event media to an event
    @classmethod
    def bind_attachment(cls, event_id, attachment_file_id):
        try:
            query = ("""
                INSERT INTO event_media (event_id, member_file_id) VALUES (%s, %s)
            """)
            params = (event_id, attachment_file_id)
            cls.source.execute(query, params)
            cls.source.commit()
        except Exception as e:
            raise e

    # Unbind all attachments except list(ids)
    @classmethod
    def unbind_attachments_by_exception(cls, attachment_ids_to_stay, event_id):
        query = ("""
            DELETE FROM event_media
            WHERE event_id=%s AND event_media.id != ALL(%s)
        """)
        params = (event_id, attachment_ids_to_stay)
        cls.source.execute(query, params)
        cls.source.commit()

    # Unbind all attachments from evnet
    classmethod

    def unbind_all_attachments(cls, event_id):
        query = ("""
            DELETE FROM event_media
            WHERE event_id=%s
        """)
        params = (event_id,)
        cls.source.execute(query, params)
        cls.source.commit()

    # Cancel one event by id, return sequence id
    @classmethod
    def cancel_single_event(cls, event_id):
        try:
            query = ("""
                UPDATE event_2
	                SET event_status = 'Cancel'
	                WHERE event_2.id = %s
	                RETURNING event_2.sequence_id
                """)
            params = (event_id,)
            cls.source.execute(query, params)
            sequence_id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                sequence_id = result[0]
            cls.source.commit()
            return sequence_id
        except Exception as e:
            raise e

    # Cancel events in sequence starting from selected date
    @classmethod
    def cancel_events_after(cls, sequence_id, start_datetime):
        try:
            query = ("""
                UPDATE event_2
	                SET event_status = 'Cancel'
	                WHERE sequence_id = %s AND start_datetime >= %s
	                RETURNING TRUE
                """)
            params = (sequence_id, start_datetime)
            cls.source.execute(query, params)
            success = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                success = result[0]
            cls.source.commit()
            return success
        except Exception as e:
            raise e

    @classmethod
    def change_event_date(cls, event_id, start, end):
        try:
            query = ("""
                UPDATE event_2
                SET start_datetime = %s, end_datetime = %s
                    WHERE event_2.id = %s
                    RETURNING id
            """)
            params = (start, end, event_id)
            cls.source.execute(query, params)
            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]
            cls.source.commit()
            return id
        except Exception as e:
            raise e

    @classmethod
    def get_event_by_id(cls, event_id):
        query = ("""
            SELECT row_to_json(row)
            FROM (
                    SELECT
                        id as event_id,
                        sequence_id,
                        event_color_id,
                        event_name,
                        event_type,
                        event_description,
                        host_member_id,
                        is_full_day,
                        event_status,
                        event_tz,
                        start_datetime as start,
                        end_datetime as end,
                        event_recurrence_freq,
                        end_condition,
                        repeat_times,
                        repeat_weekdays,
                        end_date_datetime,
                        location_mode,
                        location_id,
                        location_address,
                        (
                            SELECT json_agg(files) as attachments
                            FROM (
                                SELECT
                                    event_media.id as attachment_id,
                                    member_file_id,
                                    file_id,
                                    member_file.file_name as file_name,
                                    member_file.file_size_bytes as file_size_bytes,
                                    file_storage_engine.storage_engine_id as file_link
                                FROM event_media
                                LEFT JOIN member_file ON member_file.id = member_file_id
                                LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                WHERE event_media.event_id = event_2.id
                            ) as files
                        ),
                        (
                            SELECT json_agg(invitees) as invitations
                            FROM (
                                SELECT
                                    id as invite_id,
                                    invite_member_id,
                                    invite_status,
                                    create_date,
                                    update_date
                                FROM event_invite_2
                                WHERE event_invite_2.event_id = event_2.id
                            ) AS invitees
                        )
                    FROM event_2
                    WHERE event_2.id = %s AND event_status != 'Cancel'
                ) AS row
        """)
        params = (event_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            return None

    @classmethod
    def get_event_sequence_by_id(cls, sequence_id):
        query = ("""
                SELECT json_agg(sequence) as sequence
                    FROM (
                        SELECT
                            id as event_id,
                            sequence_id,
                            event_color_id,
                            event_name,
                            event_type,
                            event_description,
                            host_member_id,
                            is_full_day,
                            event_status,
                            event_tz,
                            start_datetime as start,
                            end_datetime as end,
                            event_recurrence_freq,
                            end_condition,
                            repeat_times,
                            repeat_weekdays,
                            end_date_datetime,
                            location_mode,
                            location_id,
                            location_address,
                            (
                                SELECT json_agg(files) as attachments
                                FROM (
                                    SELECT
                                        event_media.id as attachment_id,
                                        member_file_id,
                                        file_id,
                                        member_file.file_name as file_name,
                                        member_file.file_size_bytes as file_size_bytes,
                                        file_storage_engine.storage_engine_id as file_link
                                    FROM event_media
                                    LEFT JOIN member_file ON member_file.id = member_file_id
                                    LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                    WHERE event_media.event_id = event_2.id
                                ) as files
                            ),
                            (
                                SELECT json_agg(invitees) as invitations
                                FROM (
                                    SELECT
                                        id as invite_id,
                                        invite_member_id,
                                        invite_status,
                                        create_date,
                                        update_date
                                    FROM event_invite_2
                                    WHERE event_invite_2.event_id = event_2.id
                                ) AS invitees
                            )
                        FROM event_2
                        WHERE sequence_id = %s AND event_status != 'Cancel'
                    ) AS sequence
                """)
        params = (sequence_id,)
        # FIXME: Amerize url
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()
        else:
            return None

    @classmethod
    def get_events_by_range(cls, event_host_member_id, search_time_start=None, search_time_end=None):

        query_date = ""
        if search_time_start and search_time_end:
            query_date = ("""
                ((start_datetime between '{str_time_start}' and '{str_time_end}')
                OR
                (end_datetime between '{str_time_start}' and '{str_time_end}'))
                AND """.format(str_time_start=search_time_start, str_time_end=search_time_end))

        query = ("""
             SELECT json_agg(sequence) as data
                    FROM (
                        SELECT
                            id as event_id,
                            sequence_id,
                            event_color_id,
                            event_name,
                            event_type,
                            event_description,
                            host_member_id,
                            is_full_day,
                            event_status,
                            event_tz,
                            start_datetime as start,
                            end_datetime as end,
                            event_recurrence_freq,
                            end_condition,
                            repeat_times,
                            repeat_weekdays,
                            end_date_datetime,
                            location_mode,
                            location_id,
                            location_address,
                            (
                                SELECT json_agg(files) as attachments
                                FROM (
                                    SELECT
                                        event_media.id as attachment_id,
                                        member_file_id,
                                        file_id,
                                        member_file.file_name as file_name,
                                        member_file.file_size_bytes as file_size_bytes,
                                        file_storage_engine.storage_engine_id as file_link
                                    FROM event_media
                                    LEFT JOIN member_file ON member_file.id = member_file_id
                                    LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                    WHERE event_media.event_id = event_2.id
                                ) as files
                            ),
                            (
                                SELECT json_agg(invitees) as invitations
                                FROM (
                                    SELECT
                                        id as invite_id,
                                        invite_member_id,
                                        invite_status,
                                        create_date,
                                        update_date
                                    FROM event_invite_2
                                    WHERE event_invite_2.event_id = event_2.id
                                ) AS invitees
                            )
                        FROM event_2
                        WHERE {} host_member_id = %s AND event_status != 'Cancel'
                    ) AS sequence
        """.format(query_date))
        params = (event_host_member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()
        else:
            return None

    @classmethod
    def delete_event(cls, id):
        try:
            query = ("""
                DELETE FROM event WHERE id = {}
            """.format(id))
            cls.source.execute(query)
            return True
        except Exception as e:
            return False

    @classmethod
    def update_event_by_id(cls, event_id, updates):
        try:
            sql_template = "UPDATE event_2 SET ({}) = %s WHERE id = {} RETURNING id"
            query = sql_template.format(', '.join(updates.keys()), event_id)
            params = (tuple(updates.values()),)

            cls.source.execute(query, params)
            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]
            cls.source.commit()
            return id
        except Exception as e:
            raise e

    # @classmethod
    # def update_event_by_id(cls, key, value, id):
    #     try:
    #         query = ("""
    #             UPDATE event SET {}={} WHERE id = %s RETURNING id;
    #         """.format(key, value))
    #         params = (id,)
    #         cls.source.execute(query, params)

    #         id = None
    #         if cls.source.has_results():
    #             result = cls.source.cursor.fetchone()
    #             id = result[0]

    #         if commit:
    #             cls.source.commit()

    #         return id
    #     except Exception as e:
    #         return None
