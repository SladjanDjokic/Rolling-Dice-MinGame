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

    @classmethod
    def get_global_user_bug_reports(cls, search_key, page_size, page_number, sort_params, get_all, member_id):
        try:
            sort_columns_string = 'bug_report.create_date DESC'
            bug_reports = list()
            if sort_params:
                bug_reports_dict = {
                    'id': 'bug_report.id',
                    'member_id': 'bug_report.member_id',
                    'description': 'bug_report.description',
                    'assignee_member_id':'bug_report.assignee_member_id',
                    'status':'bug_report.status',
                    'current_url':'bug_report.current_url',
                    'referer_url':'bug_report.referer_url',
                    'create_date': 'bug_report.create_date',
                    'update_date':'bug_report.update_date',
                    'first_name':'member.first_name',
                    'last_name':'member.last_name'
                }
                sort_columns_string = cls.formatSortingParams(
                    sort_params, bug_reports_dict) or sort_columns_string
            
            query_conditions = f"""
                {f"bug_report.member_id = {member_id} AND " if member_id else ""}
                (
                    concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                    OR member.email iLIKE %s
                    OR bug_report.description iLIKE %s
                    OR bug_report.current_url iLIKE %s
                    OR bug_report.referer_url iLIKE %s
                    OR concat('create year ', EXTRACT(YEAR FROM bug_report.create_date)) iLIKE %s
                    OR concat('create month ', EXTRACT(MONTH FROM bug_report.create_date)) iLIKE %s
                    OR concat('create month ', to_char(bug_report.create_date, 'month')) iLIKE %s
                    OR concat('create day ', EXTRACT(DAY FROM bug_report.create_date)) iLIKE %s
                    OR concat('create day ', to_char(bug_report.create_date, 'day')) iLIKE %s
                    OR concat('update year ', EXTRACT(YEAR FROM bug_report.update_date)) iLIKE %s
                    OR concat('update month ', EXTRACT(MONTH FROM bug_report.update_date)) iLIKE %s
                    OR concat('update month ', to_char(bug_report.update_date, 'month')) iLIKE %s
                    OR concat('update day ', EXTRACT(DAY FROM bug_report.update_date)) iLIKE %s
                    OR concat('update day ', to_char(bug_report.update_date, 'day')) iLIKE %s
                )
            """

            query = (f"""
                SELECT
                    bug_report.id,
                    bug_report.member_id,
                    bug_report.description,
                    bug_report.assignee_member_id,
                    bug_report.status,
                    bug_report.current_url,
                    bug_report.referer_url,
                    bug_report.create_date,
                    bug_report.update_date,
                    member.first_name,
                    member.last_name,
                    bug_report.redux_state, 
                    bug_report.browser_info,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_screenshot_url
                FROM
                    bug_report
                LEFT OUTER JOIN member ON member.id = bug_report.member_id
                LEFT OUTER JOIN member_file ON member_file.id = bug_report.screenshot_storage_id
                LEFT OUTER JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                WHERE
                    {query_conditions}
                ORDER BY {sort_columns_string}
            """)

            countQuery = (f"""
                SELECT
                    COUNT(*)
                FROM
                    bug_report
                LEFT OUTER JOIN member ON member.id = bug_report.member_id
                WHERE
                    {query_conditions}
                """)

            like_search_key = """%{}%""".format(search_key)
            params = tuple(15 * [like_search_key])

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)

            logger.debug(f'members bug reports params {params} {query} {search_key}, {page_size}, {page_number}, {sort_params}, {get_all}, {member_id}')

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        member_id,
                        description,
                        assignee_member_id,
                        status,
                        current_url,
                        referer_url,
                        create_date,
                        update_date,
                        first_name,
                        last_name,
                        redux_state, 
                        browser_info,
                        s3_screenshot_url
                ) in cls.source.cursor:
                    bug_report = {
                        'id': id,
                        'member_id': member_id,
                        'description': description,
                        'assignee_member_id': assignee_member_id,
                        'status': status,
                        'current_url': current_url,
                        'referer_url': referer_url,
                        'create_date': create_date,
                        'update_date': update_date,
                        'first_name': first_name,
                        'last_name': last_name,
                        'redux_state': redux_state, 
                        'browser_info': browser_info,
                        's3_screenshot_url': s3_screenshot_url
                    }
                    bug_reports.append(bug_report)

                return {"bug_reports": bug_reports, "count": count}
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def formatSortingParams(cls, sort_by, entity_dict):
        columns_list = sort_by.split(',')
        new_columns_list = list()

        for column in columns_list:
            if column[0] == '-':
                column = column[1:]
                column = entity_dict.get(column)
                if column:
                    column = column + ' DESC'
                    new_columns_list.append(column)
            else:
                column = entity_dict.get(column)
                if column:
                    column = column + ' ASC'
                    new_columns_list.append(column)

        return (',').join(column for column in new_columns_list)

    @classmethod 
    def get_bug_report_users(cls):
        try:
            users = list()
            query = f"""
                SELECT
                    member_id,
                    member.first_name,
                    member.last_name
                FROM bug_report
                LEFT OUTER JOIN member ON member.id = bug_report.member_id
                GROUP BY
                    member_id,
                    member.first_name,
                    member.last_name
                ORDER BY
                    member.first_name,
                    member.last_name
            """
            params = ()

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                    member_id,
                    first_name,
                    last_name
                ) in cls.source.cursor:
                    user = {
                        "member_id": member_id,
                        "first_name": first_name,
                        "last_name": last_name
                    }
                    users.append(user)
            return users
        except:
            logger.debug(e, exc_info=True)
            return None