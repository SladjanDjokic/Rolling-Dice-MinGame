import logging
from app.util.auth import inject_member, check_session
import app.util.json as json
import app.util.request as request
from app.da.project import ProjectDA
from operator import itemgetter

logger = logging.getLogger(__name__)


class ProjectResource(object):
    @inject_member
    def on_get(self, req, resp, member):
        try:
            projects = ProjectDA.get_related_projects(member["member_id"])
            resp.body = json.dumps({
                "success": True,
                "description": "Projects data fetched succefully",
                "data": projects
            })
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @inject_member
    def on_post(self, req, resp, member):
        try:
            (company_id, creator_project_role_id, owner_member_id, project_title, project_type, project_description, project_start_date, project_estimated_days,) = request.get_json_or_form(
                "company_id", "creator_project_role_id", "owner_member_id", "project_title", "project_type", "project_description", "project_start_date", "project_estimated_days", req=req)

            # Create project
            project_id = ProjectDA.create_project_entry({'company_id': company_id,
                                                         'project_title': project_title,
                                                         'project_type': project_type,
                                                         'project_description': project_description,
                                                         'start_date': project_start_date,
                                                         'estimated_days': f"{project_estimated_days} days"}
                                                        )

            # Create project members for creator and owner
            creator_member_id = member["member_id"]
            creator_project_member_id = ProjectDA.create_project_member({'project_id': project_id,
                                                                         'member_id': creator_member_id,
                                                                         'pay_rate': 0,
                                                                         'pay_type': 'hourly',
                                                                         'currency_id': 666,
                                                                         'privileges': ['approve', 'create', 'view', 'edit']
                                                                         })

            owner_project_member_id = creator_project_member_id
            if creator_member_id != owner_member_id:
                owner_project_member_id = ProjectDA.create_project_member({'project_id': project_id,
                                                                           'member_id': owner_member_id,
                                                                           'pay_rate': 0,
                                                                           'pay_type': 'hourly',
                                                                           'currency_id': 666,
                                                                           'privileges': ['approve', 'create', 'view', 'edit']
                                                                           })

            # Assign ownership
            ProjectDA.assign_owner({'project_id': project_id,
                                    'owner_id': owner_project_member_id})

            # Assign project roles
            ProjectDA.assign_project_role(
                {'project_id': project_id, 'project_member_id': creator_project_member_id, 'project_role_id': creator_project_role_id})

            resp.body = json.dumps({
                "success": True,
                "description": 'Project created successfully'
            })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @inject_member
    def on_post_member(self, req, resp, member):
        try:
            (project_id, members,) = request.get_json_or_form(
                "project_id", "members", req=req)

            if len(members) > 0:
                # Member ids of persons already in the project
                onboarded_member_ids = ProjectDA.get_member_ids_for_project(
                    project_id=project_id)

                new_members = set(members) - set(onboarded_member_ids)
                # Last item makes sure we don't delete ourselves
                discarded_members = set(
                    onboarded_member_ids) - set(members) - {member["member_id"]}

                if len(new_members) > 0:
                    for member_id in new_members:
                        project_member_id = ProjectDA.create_project_member(
                            {"project_id": project_id, "member_id": member_id, "pay_rate": 0, "pay_type": "hourly", "currency_id": 666, "privileges": ['view']})

                if len(discarded_members) > 0:
                    for member_id in discarded_members:
                        ProjectDA.delete_project_member(
                            {"project_id": project_id, "member_id": member_id})

                resp.body = json.dumps({
                    "success": True,
                    "description": 'Team successfully assigned'
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_post_member_role(self, req, resp):
        try:
            (project_id, roles_data) = request.get_json_or_form(
                "project_id", "roles_data", req=req)

            if len(roles_data) > 0:
                for item in roles_data:
                    (project_member_id, role_ids) = itemgetter(
                        "project_member_id", "role_ids")(item)

                    existing_roles = ProjectDA.get_project_roles_for_member(
                        {"project_id": project_id, "project_member_id": project_member_id})

                    new_roles = set(role_ids) - set(existing_roles)
                    cancelled_roles = set(existing_roles) - set(role_ids)

                    if len(new_roles) > 0:
                        for role_id in new_roles:
                            ProjectDA.assign_project_role(
                                {"project_id": project_id, "project_member_id": project_member_id, "project_role_id": role_id})

                    if len(cancelled_roles) > 0:
                        for role_id in cancelled_roles:
                            ProjectDA.delete_project_member_role(
                                {"project_id": project_id, "project_member_id": project_member_id, "project_role_id": role_id})

                resp.body = json.dumps({
                    "success": True,
                    "description": "Roles assigned successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": True,
                    "description": "No updates were made as no roles data was passed"
                })
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_post_member_privilege(self, req, resp):
        try:
            (project_id, privileges_data) = request.get_json_or_form(
                "project_id", "privileges_data", req=req)

            if len(privileges_data) > 0:
                for item in privileges_data:
                    (project_member_id, privileges) = itemgetter(
                        "project_member_id", "privileges")(item)
                    if privileges:
                        ProjectDA.assign_project_privilege(
                            {"project_member_id": project_member_id, "privileges": privileges})
                resp.body = json.dumps({
                    "success": True,
                    "description": "Privileges assigned successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": True,
                    "description": "No updates were made as no privilege data was passed"
                })
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_get_roles(self, req, resp):
        try:
            roles = ProjectDA.get_all_project_roles()
            resp.body = json.dumps({
                "success": True,
                "description": "Project roles fetched sucessfully",
                "data": roles
            })
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    # Epics
    @inject_member
    def on_post_epic(self, req, resp, member):
        try:
            (project_id, epic_title, epic_description) = request.get_json_or_form(
                "project_id", "epic_title", "epic_description", req=req)

            inserted = ProjectDA.insert_epic({"project_id": project_id, "epic_title": epic_title,
                                              "epic_description": epic_description, "member_id": member["member_id"]})

            if inserted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Epic created successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when creating epic"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @inject_member
    def on_put_epic(self, req, resp, member, epic_id):
        try:
            (epic_title, epic_description) = request.get_json_or_form(
                "epic_title", "epic_description", req=req)

            updated = ProjectDA.update_epic({"epic_id": epic_id, "epic_title": epic_title,
                                             "epic_description": epic_description, "member_id": member["member_id"]})

            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Epic updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating epic"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_delete_epic(self, req, resp, epic_id):
        try:
            deleted = ProjectDA.delete_epic(epic_id=epic_id)

            if deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Epic deleted successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deleting epic"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    # Tremors
    @inject_member
    def on_post_tremor(self, req, resp, member):
        try:
            (project_id, project_epic_id, tremor_title, tremor_description) = request.get_json_or_form(
                "project_id", "project_epic_id", "tremor_title", "tremor_description", req=req)

            inserted = ProjectDA.insert_tremor({"project_id": project_id, "project_epic_id": project_epic_id,
                                                "tremor_title": tremor_title, "tremor_description": tremor_description, "member_id": member["member_id"]})

            if inserted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Tremor created successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when creating tremor"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @inject_member
    def on_put_tremor(self, req, resp, tremor_id, member):
        try:
            (project_id, tremor_title, tremor_description) = request.get_json_or_form(
                "project_id", "tremor_title", "tremor_description", req=req)

            updated = ProjectDA.update_tremor({"project_id": project_id, "tremor_id": tremor_id,
                                               "tremor_title": tremor_title, "tremor_description": tremor_description, "member_id": member["member_id"]})

            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Tremor updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating tremor"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_delete_tremor(self, req, resp, tremor_id):
        try:
            deleted = ProjectDA.delete_tremor(tremor_id=tremor_id)

            if deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Tremor deleted successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deleting tremor"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    # Story
    @inject_member
    def on_post_story(self, req, resp, member):
        try:
            (project_id, project_tremor_id, story_title, story_description) = request.get_json_or_form(
                "project_id", "project_tremor_id", "story_title", "story_description", req=req)

            inserted = ProjectDA.insert_story({"project_id": project_id, "project_tremor_id": project_tremor_id,
                                               "story_title": story_title, "story_description": story_description, "member_id": member["member_id"]})

            if inserted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Story created successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when creating story"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @inject_member
    def on_put_story(self, req, resp, story_id, member):
        try:
            (project_id, story_title, story_description) = request.get_json_or_form(
                "project_id", "story_title", "story_description", req=req)

            updated = ProjectDA.update_tremor({"project_id": project_id, "story_id": story_id,
                                               "story_title": story_title, "story_description": story_description, "member_id": member["member_id"]})

            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Story updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating story"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_delete_story(self, req, resp, story_id):
        try:
            deleted = ProjectDA.delete_story(story_id=story_id)

            if deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Story deleted successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deleting story"
                })

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    # Task
    @inject_member
    def on_post_task(self, req, resp, member):
        logger.debug('task')
