import logging
import datetime

from app.util.db import source
import app.util.json as json
from app.util.config import settings
from app.exceptions.file_sharing import FileShareExists, FileNotFound, \
    FileUploadCreateException, FileStorageUploadError
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class MemberEventDA(object):
    source = source

    # @classmethod
    # def get_event_by_id(cls, id):
    #     return cls.__get_data('id', id)

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
              end_condition, repeat_weekdays, end_date_datetime, location_mode, location_id, location_address, repeat_times, cover_attachment_id, group_id=None):
        try:
            query = (
                """ INSERT INTO event_2
                    (sequence_id, event_color_id, event_name, event_description, host_member_id,
                    is_full_day, event_tz, start_datetime, end_datetime, event_type,
                    event_recurrence_freq, end_condition, repeat_weekdays, end_date_datetime, location_mode,
                    location_id, location_address, repeat_times, group_id, cover_attachment_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """)
            params = (sequence_id, event_color_id, event_name, event_description, host_member_id,
                      is_full_day, event_tz, start_datetime, end_datetime, event_type, event_recurrence_freq,
                      end_condition, json.dumps(repeat_weekdays), end_date_datetime, location_mode, location_id, location_address, repeat_times, group_id, cover_attachment_id)
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
    def cancel_events_by_sequence_id(cls, sequence_id):
        try:
            query = ("""
                UPDATE event_2
                    SET event_status = 'Cancel'
                    WHERE sequence_id = %s
                    RETURNING TRUE
                """)
            params = (sequence_id, )
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
                        (
                            SELECT row_to_json(group_data) as group_info
                            FROM (
                                SELECT
                                    member_group.id as group_id,
                                    group_name,
                                    group_leader_id
                                FROM member_group
                                WHERE member_group.id = group_id
                            ) as group_data
                        ),
                        event_color_id,
                        event_name,
                        event_type,
                        event_description,
                        (
                            SELECT row_to_json(member_data) as host_member_info
                            FROM (
                                SELECT
                                    member.id as host_member_id,
                                    member.first_name,
                                    member.middle_name,
                                    member.last_name,
                                    member.company_name
                                FROM member
                                WHERE member.id = host_member_id
                            ) as member_data
                        ),
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
                                    file_storage_engine.mime_type as mime_type,
                                    file_path(file_storage_engine.storage_engine_id, '/member/file') as file_url
                                FROM event_media
                                LEFT JOIN member_file ON member_file.id = member_file_id
                                LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                WHERE event_media.event_id = event_2.id
                            ) as files
                        ),
                        cover_attachment_id,
                        (
                            SELECT json_agg(invitees) as invitations
                            FROM (
                                SELECT
                                    event_invite_2.id as invite_id,
                                    event_invite_2.invite_member_id,
                                    event_invite_2.invite_status,
                                    event_invite_2.invitee_comment,
                                    event_invite_2.create_date,
                                    event_invite_2.update_date,
                                    member.company_name as company,
                                    job_title.name as title,
                                    member.first_name,
                                    member.middle_name,
                                    member.last_name,
                                    file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url
                                FROM event_invite_2
                                    INNER JOIN member                   ON member.id = event_invite_2.invite_member_id
                                    LEFT OUTER JOIN member_profile      ON member.id = member_profile.member_id
                                    LEFT OUTER JOIN job_title           ON member.job_title_id = job_title.id
                                    LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
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
                            (
                                SELECT row_to_json(group_data) as group_info
                                FROM (
                                    SELECT
                                        member_group.id as group_id,
                                        group_name,
                                        group_leader_id
                                    FROM member_group
                                    WHERE member_group.id = group_id
                                ) as group_data
                            ),
                            event_color_id,
                            event_name,
                            event_type,
                            event_description,
                            (
                                SELECT row_to_json(member_data) as host_member_info
                                FROM (
                                    SELECT
                                        member.id as host_member_id,
                                        member.first_name,
                                        member.middle_name,
                                        member.last_name,
                                        member.company_name
                                    FROM member
                                    WHERE member.id = host_member_id
                                ) as member_data
                            ),
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
                                        file_storage_engine.mime_type as mime_type,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as file_url
                                    FROM event_media
                                    LEFT JOIN member_file ON member_file.id = member_file_id
                                    LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                    WHERE event_media.event_id = event_2.id
                                ) as files
                            ),
                            cover_attachment_id,
                            (
                                SELECT json_agg(invitees) as invitations
                                FROM (
                                    SELECT
                                        event_invite_2.id as invite_id,
                                        event_invite_2.invite_member_id,
                                        event_invite_2.invite_status,
                                        event_invite_2.invitee_comment,
                                        event_invite_2.create_date,
                                        event_invite_2.update_date,
                                        member.company_name as company,
                                        job_title.name as title,
                                        member.first_name,
                                        member.middle_name,
                                        member.last_name,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url
                                    FROM event_invite_2
                                        INNER JOIN member                   ON member.id = event_invite_2.invite_member_id
                                        LEFT OUTER JOIN member_profile      ON member.id = member_profile.member_id
                                        LEFT OUTER JOIN job_title           ON member.job_title_id = job_title.id
                                        LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
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
                            (
                                SELECT row_to_json(group_data) as group_info
                                FROM (
                                    SELECT
                                        member_group.id as group_id,
                                        group_name,
                                        group_leader_id
                                    FROM member_group
                                    WHERE member_group.id = group_id
                                ) as group_data
                            ),
                            event_color_id,
                            event_name,
                            event_type,
                            event_description,
                            (
                                SELECT row_to_json(member_data) as host_member_info
                                FROM (
                                    SELECT
                                        member.id as host_member_id,
                                        member.first_name,
                                        member.middle_name,
                                        member.last_name,
                                        member.company_name
                                    FROM member
                                    WHERE member.id = host_member_id
                                ) as member_data
                            ),
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
                                        file_storage_engine.mime_type as mime_type,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as file_url
                                    FROM event_media
                                    LEFT JOIN member_file ON member_file.id = member_file_id
                                    LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                    WHERE event_media.event_id = events.id
                                ) as files
                            ),
                            cover_attachment_id,
                            (
                                SELECT json_agg(invitees) as invitations
                                FROM (
                                    SELECT
                                        event_invite_2.id as invite_id,
                                        event_invite_2.invite_member_id,
                                        event_invite_2.invite_status,
                                        event_invite_2.invitee_comment,
                                        event_invite_2.create_date,
                                        event_invite_2.update_date,
                                        member.company_name as company,
                                        job_title.name as title,
                                        member.first_name,
                                        member.middle_name,
                                        member.last_name,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url
                                    FROM event_invite_2
                                        INNER JOIN member                   ON member.id = event_invite_2.invite_member_id
                                        LEFT OUTER JOIN member_profile      ON member.id = member_profile.member_id
                                        LEFT OUTER JOIN job_title           ON member.job_title_id = job_title.id
                                        LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                                    WHERE event_invite_2.event_id = events.id
                                ) AS invitees
                            )
                        FROM (
                            SELECT
                                event_2.*,
                                event_2.host_member_id AS viewer_member_id
                            FROM event_2 WHERE {} event_2.host_member_id = %s AND
                                event_2.event_status='Active'
                            UNION
                            SELECT
                                event_2.*,
                                event_invite_2.invite_member_id AS viewer_member_id
                            FROM event_2
                            INNER JOIN event_invite_2 ON event_2.id=event_invite_2.event_id
                            WHERE {} event_invite_2.invite_member_id = %s AND
                                event_2.event_status='Active' AND
                                event_invite_2.invite_status='Accepted'
                        ) as events
                    ) AS sequence
        """.format(query_date, query_date))
        params = (event_host_member_id, event_host_member_id)
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

    @classmethod
    def get_recurring_copies_invite_ids(cls, member_id, original_event_id):
        try:
            query = ('''
                SELECT event_invite_2.id
                    FROM event_invite_2
                    LEFT JOIN event_2 ON event_invite_2.event_id = event_2.id
                    LEFT JOIN event_sequence ON event_2.sequence_id = event_sequence.id
                    WHERE event_invite_2.invite_member_id = %s
                        AND event_invite_2.invite_status = 'Recurring'
                        AND event_sequence.id = (
                            SELECT event_sequence.id
                            FROM event_sequence
                            LEFT JOIN event_2 ON event_2.sequence_id = event_sequence.id
                            LEFT JOIN event_invite_2 ON event_2.id = event_invite_2.event_id
                            WHERE event_invite_2.id = %s
                        )
            ''')
            params = (member_id, original_event_id)
            cls.source.execute(query, params)
            if cls.source.has_results():
                invite_ids = [r[0] for r in cls.source.cursor.fetchall()]
                return invite_ids

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

    @classmethod
    def get_upcoming_events(cls, member_id, current, limit):
        query = ("""
            SELECT json_agg(sequence) as data
                    FROM (
                        SELECT
                            events.id as event_id,
                            sequence_id,
                            (
                                SELECT row_to_json(group_data) as group_info
                                FROM (
                                    SELECT
                                        member_group.id as group_id,
                                        group_name,
                                        group_leader_id
                                    FROM member_group
                                    WHERE member_group.id = group_id
                                ) as group_data
                            ),
                            event_color_id,
                            event_name,
                            event_type,
                            event_description,
                            (
                                SELECT row_to_json(member_data) as host_member_info
                                FROM (
                                    SELECT
                                        member.id as host_member_id,
                                        member.first_name,
                                        member.middle_name,
                                        member.last_name,
                                        member.company_name
                                    FROM member
                                    WHERE member.id = host_member_id
                                ) as member_data
                            ),
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
                            member.first_name as first_name,
                            member.last_name as last_name,
                            file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                            role.name as role,
                            (
                                SELECT json_agg(files) as attachments
                                FROM (
                                    SELECT
                                        event_media.id as attachment_id,
                                        member_file_id,
                                        file_id,
                                        member_file.file_name as file_name,
                                        member_file.file_size_bytes as file_size_bytes,
                                        file_storage_engine.mime_type as mime_type,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as file_url
                                    FROM event_media
                                    LEFT JOIN member_file ON member_file.id = member_file_id
                                    LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                                    WHERE event_media.event_id = events.id
                                ) as files
                            ),
                            cover_attachment_id,
                            (
                                SELECT json_agg(invitees) as invitations
                                FROM (
                                    SELECT
                                        event_invite_2.id as invite_id,
                                        event_invite_2.invite_member_id,
                                        event_invite_2.invite_status,
                                        event_invite_2.invitee_comment,
                                        event_invite_2.create_date,
                                        event_invite_2.update_date,
                                        member.company_name as company,
                                        job_title.name as title,
                                        member.first_name,
                                        member.middle_name,
                                        member.last_name,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url
                                    FROM event_invite_2
                                        INNER JOIN member                   ON member.id = event_invite_2.invite_member_id
                                        LEFT OUTER JOIN member_profile      ON member.id = member_profile.member_id
                                        LEFT OUTER JOIN job_title           ON member.job_title_id = job_title.id
                                        LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                                    WHERE event_invite_2.event_id = events.id
                                ) AS invitees
                            )
                        FROM (
                            SELECT event_2.*, event_2.host_member_id AS viewer_member_id
                            FROM event_2 WHERE event_2.host_member_id = %s AND event_2.event_status='Active'
                            UNION
                            SELECT event_2.*, event_invite_2.invite_member_id AS viewer_member_id
                            FROM event_2
                            INNER JOIN event_invite_2 ON event_2.id=event_invite_2.event_id
                            WHERE event_invite_2.invite_member_id = %s and event_2.event_status='Active' and event_invite_2.invite_status='Accepted'
                        ) as events
                        LEFT JOIN member ON member.id = events.host_member_id
                        LEFT JOIN member_profile ON member.id = member_profile.member_id
                        LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                        LEFT OUTER JOIN contact ON
                            (   events.host_member_id = contact.contact_member_id
                            AND events.viewer_member_id = contact.member_id)
                        LEFT OUTER JOIN role ON (contact.role_id = role.id)
                        WHERE events.start_datetime >= %s and events.event_status='Active'
                    ORDER BY events.start_datetime
                    Limit %s
                ) AS sequence
        """)
        params = (member_id, member_id, current, limit)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (data,) = cls.source.cursor.fetchone()
            return data
        else:
            return None

    @classmethod
    def get_event_invitations(cls, member_id):
        query = ("""
            SELECT json_agg(SEQUENCE) AS data
            FROM
            (SELECT event_invite_2.id as id,
                    event_2.id AS event_id,
                    sequence_id,
                    (
                        SELECT row_to_json(group_data) as group_info
                        FROM (
                            SELECT
                                member_group.id as group_id,
                                group_name,
                                group_leader_id
                            FROM member_group
                            WHERE member_group.id = group_id
                        ) as group_data
                    ),
                    event_color_id,
                    event_name,
                    event_type,
                    event_description,
                    (
                        SELECT row_to_json(member_data) as host_member_info
                        FROM (
                            SELECT
                                member.id as host_member_id,
                                member.first_name,
                                member.middle_name,
                                member.last_name,
                                member.company_name
                            FROM member
                            WHERE member.id = host_member_id
                        ) as member_data
                    ),
                    is_full_day,
                    event_status,
                    event_tz,
                    start_datetime AS START,
                    end_datetime AS END,
                    event_recurrence_freq,
                    end_condition,
                    repeat_times,
                    repeat_weekdays,
                    end_date_datetime,
                    location_mode,
                    location_id,
                    location_address,
                    member.first_name as first_name,
                    member.last_name as last_name,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                    role.name as role,
                (SELECT json_agg(files) AS attachments
                FROM
                    (SELECT event_media.id AS attachment_id,
                            member_file_id,
                            file_id,
                            member_file.file_name AS file_name,
                            member_file.file_size_bytes AS file_size_bytes,
                            file_storage_engine.mime_type as mime_type,
                            file_path(file_storage_engine.storage_engine_id, '/member/file') AS file_url
                    FROM event_media
                    LEFT JOIN member_file ON member_file.id = member_file_id
                    LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                    WHERE event_media.event_id = event_2.id ) AS files),
                cover_attachment_id,
                (SELECT json_agg(invitees) AS invitations
                FROM
                    (
                        SELECT
                            event_invite_2.id as invite_id,
                            event_invite_2.invite_member_id,
                            event_invite_2.invite_status,
                            event_invite_2.invitee_comment,
                            event_invite_2.create_date,
                            event_invite_2.update_date,
                            member.company_name as company,
                            job_title.name as title,
                            member.first_name,
                            member.middle_name,
                            member.last_name,
                            file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url
                        FROM event_invite_2
                            INNER JOIN member                   ON member.id = event_invite_2.invite_member_id
                            LEFT OUTER JOIN member_profile      ON member.id = member_profile.member_id
                            LEFT OUTER JOIN job_title           ON member.job_title_id = job_title.id
                            LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                        WHERE event_invite_2.event_id = event_2.id
                     ) AS invitees)
            FROM event_2
            INNER JOIN event_invite_2 ON event_invite_2.event_id = event_2.id
            LEFT JOIN member ON member.id = event_2.host_member_id
            LEFT JOIN member_profile ON member.id = member_profile.member_id
            LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
            LEFT OUTER JOIN contact ON
                (   event_2.host_member_id = contact.contact_member_id
                AND event_invite_2.invite_member_id = contact.member_id)
            LEFT OUTER JOIN role ON (contact.role_id = role.id)
            WHERE event_invite_2.invite_member_id = %s
                AND event_2.event_status='Active'
                AND event_invite_2.invite_status='Tentative'
            ORDER BY event_2.start_datetime
            ) AS SEQUENCE
        """)
        params = (member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (data,) = cls.source.cursor.fetchone()
            return data if data else []
        else:
            return None

    @classmethod
    def set_event_invite_status(cls, member_id, event_invite_id, status, comment):
        query = ("""
            UPDATE event_invite_2
                SET invite_status = %s,
                    invitee_comment = %s
            WHERE id = %s and invite_member_id=%s
        """)
        params = (status, comment, event_invite_id, member_id)
        cls.source.execute(query, params)
        cls.source.commit()
        return True

    @classmethod
    def get_events_ids_sequence_by_id(cls, sequence_id):
        try:
            query = ("""
                SELECT array_agg(event_2.id) as event_ids
                FROM event_2
                WHERE sequence_id = %s
                GROUP BY sequence_id
            """)
            params = (sequence_id,)
            cls.source.execute(query, params)
            ids = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                ids = result[0]
            cls.source.commit()
            return ids
        except Exception as e:
            raise e

    @classmethod
    def delete_events_sequence_by_id(cls, sequence_id):
        try:
            query = ("""
                DELETE
                FROM event_2
                WHERE sequence_id = %s
            """)
            params = (sequence_id,)
            cls.source.execute(query, params)
            cls.source.commit()
            return True
        except Exception as e:
            raise e

    @classmethod
    def delete_attachments_event_by_ids(cls, event_ids):
        try:
            ids = list()
            for id in event_ids:
                ids.append(str(id))

            event_comma_ids = ', '.join(ids)

            query = ("""
                DELETE
                FROM event_media
                WHERE event_id in (%s)
            """)

            params = (event_comma_ids,)
            cls.source.execute(query, params)
            cls.source.commit()
            return True
        except Exception as e:
            raise e

    @classmethod
    def get_all_group_event_invitations_by_member_id(cls, member_id):
        groups = list()

        try:
            query = f"""
                SELECT
                    event_invite_2.id,
                    event_invite_2.invite_status as status,
                    event_invite_2.create_date,
                    event_2.event_name,
                    event_2.event_type,
                    event_2.event_description,
                    member_group.id as group_id,
                    member_group.group_name,
                    member.id as create_user_id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    file_storage_engine.storage_engine_id,
                    json_build_object(
                        'group_id', member_group.id,
                        'group_name', member_group.group_name,
                        'group_leader_id', member_group.group_leader_id
                    ) AS group_info
                FROM event_invite_2
                INNER JOIN event_2 on event_invite_2.event_id = event_2.id
                INNER JOIN member_group ON event_2.group_id = member_group.id
                INNER JOIN member ON event_2.host_member_id = member.id
                LEFT JOIN member_profile ON member.id = member_profile.member_id
                LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                WHERE
                    event_invite_2.invite_member_id = %s AND event_2.event_status='Active'
                ORDER BY event_invite_2.create_date DESC
                LIMIT 25
            """

            params = (member_id,)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        status,
                        create_date,
                        event_name,
                        event_type,
                        event_description,
                        group_id,
                        group_name,
                        create_user_id,
                        first_name,
                        last_name,
                        email,
                        storage_engine_id,
                        group_info
                ) in cls.source.cursor:
                    mail = {
                        "id": id,
                        "status": status,
                        "create_date": create_date,
                        "event_name": event_name,
                        "event_type": event_type,
                        "event_description": event_description,
                        "group_id": group_id,
                        "group_name": group_name,
                        "create_user_id": create_user_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "group_info": group_info
                    }
                    groups.append(mail)

            return groups
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def get_all_event_invitations_by_member_id(cls, member_id):
        events = list()

        try:
            query = f"""
                SELECT
                    event_sequence.id,
                    event_invite_2.invite_status as status,
                    event_sequence.create_date,
                    event_2.event_name,
                    event_2.event_type,
                    event_2.event_description,
                    member.id as create_user_id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    file_storage_engine.storage_engine_id,
                    json_agg(json_build_object(
                        'invite_id', invitations.id,
                        'invite_member_id', invitations.invite_member_id,
                        'first_name', invited_member.first_name,
                        'middle_name', invited_member.middle_name,
                        'last_name', invited_member.last_name
                    )) AS invitations,
                    json_build_object(
                        'host_member_id', member.id,
                        'first_name', member.first_name,
                        'middle_name', member.middle_name,
                        'last_name', member.last_name
                    ) AS host_member_info
                FROM event_sequence
				INNER JOIN event_2 on event_2.sequence_id = event_sequence.id
				INNER JOIN event_invite_2 on event_invite_2.event_id = event_2.id
                INNER JOIN member ON event_2.host_member_id = member.id
                LEFT OUTER JOIN event_invite_2 AS invitations ON invitations.event_id = event_2.id
                LEFT OUTER JOIN member AS invited_member ON invitations.invite_member_id = invited_member.id
                LEFT JOIN member_profile ON member.id = member_profile.member_id
                LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                WHERE
                    event_invite_2.invite_member_id = %s
                    AND
                    event_2.event_status='Active'
                    AND
                    event_invite_2.invite_status != 'Recurring'
                    AND
                    event_2.group_id is NULL
                GROUP BY
                    event_sequence.id,
                    event_invite_2.invite_status,
                    event_sequence.create_date,
                    event_2.event_name,
                    event_2.event_type,
                    event_2.event_description,
                    member.id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    file_storage_engine.storage_engine_id
                ORDER BY event_sequence.create_date DESC
                LIMIT 25
            """

            params = (member_id,)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        status,
                        create_date,
                        event_name,
                        event_type,
                        event_description,
                        create_user_id,
                        first_name,
                        last_name,
                        email,
                        storage_engine_id,
                        invitations,
                        host_member_info
                ) in cls.source.cursor:
                    event = {
                        "id": id,
                        "status": status,
                        "create_date": create_date,
                        "event_name": event_name,
                        "event_type": event_type,
                        "event_description": event_description,
                        "create_user_id": create_user_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "invitation_type": "event_invitation",
                        "invitations": invitations,
                        "host_member_info": host_member_info
                    }
                    events.append(event)

            return events
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
