import logging
from app.util.auth import check_session
import app.util.json as json
import app.util.request as request
from app.da.project import ProjectDA
from app.da.group import GroupDA, GroupMembershipDA, GroupRole, GroupMemberStatus, GroupExchangeOptions
from operator import itemgetter
from app.exceptions.project import ProjectMemberNotFound, NotEnoughPriviliges, ContractDoesNotBelongProject, MemberDoesNotBelongToContract, NotProjectOwner
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectResource(object):
    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        try:
            projects = ProjectDA.get_related_projects(member_id)
            if not projects:
                projects = []
            resp.body = json.dumps({
                "success": True,
                "description": "Projects data fetched successfully",
                "data": projects
            })
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_post(self, req, resp):
        try:
            creator_member_id = req.context.auth["session"]["member_id"]
            (company_id, creator_project_role_id, owner_member_id, project_title, project_type, project_description, project_start_date, project_estimated_days,) = request.get_json_or_form(
                "company_id", "creator_project_role_id", "owner_member_id", "project_title", "project_type", "project_description", "project_start_date", "project_estimated_days", req=req)

            # Create project group
            group_id = GroupDA().create_group_with_trees(
                name=project_title, exchange_option=GroupExchangeOptions.NO_ENCRYPTION.value, group_type='project')

            # Create group membership
            owner_status = GroupMemberStatus.ACTIVE.value if creator_member_id == owner_member_id else GroupMemberStatus.ACTIVE.INVITED
            GroupMembershipDA().create_group_membership(group_id=group_id,
                                                        member_id=owner_member_id, status=owner_status, group_role=GroupRole.OWNER.value)
            if owner_member_id != creator_member_id:
                GroupMembershipDA().create_group_membership(group_id=group_id, member_id=creator_member_id,
                                                            status=GroupMemberStatus.INVITED.value, group_role=GroupRole.ADMIN.value)

            # Create project
            project_id = ProjectDA.create_project_entry({'company_id': company_id,
                                                         'project_title': project_title,
                                                         'project_type': project_type,
                                                         'project_description': project_description,
                                                         'start_date': project_start_date,
                                                         'estimated_days': f"{project_estimated_days} days",
                                                         "group_id": group_id}
                                                        )

            # Create project members for creator and owner
            creator_project_member_id = ProjectDA.create_project_member({'project_id': project_id,
                                                                         'member_id': creator_member_id,
                                                                         'privileges': ['approve', 'create', 'view', 'edit']
                                                                         })
            # Creator gets an active contract
            default_rate = ProjectDA.get_member_default_rate(creator_member_id)
            creator_contract_id = ProjectDA.create_contract(
                {'project_member_id': creator_project_member_id, "pay_rate": default_rate["pay_rate"], "currency_code_id": default_rate["currency_code_id"], "rate_type": "hourly", "author_id": creator_project_member_id})
            status_updated = ProjectDA.create_contract_status_entry(
                contract_id=creator_contract_id, contract_status="active", author_id=creator_project_member_id)

            owner_project_member_id = creator_project_member_id
            if creator_member_id != owner_member_id:
                owner_project_member_id = ProjectDA.create_project_member({'project_id': project_id,
                                                                           'member_id': owner_member_id,
                                                                           'privileges': ['approve', 'create', 'view', 'edit']
                                                                           })
                # If the creator aasigns someone else as an owner, he/she gets a regular pending contract
                default_rate = ProjectDA.get_member_default_rate(
                    creator_member_id)
                owner_contract_id = ProjectDA.create_contract(
                    {'project_member_id': owner_project_member_id, "pay_rate": default_rate["pay_rate"], "currency_code_id": default_rate["currency_code_id"], "rate_type": "hourly", "author_id": creator_project_member_id})
                status_updated = ProjectDA.create_contract_status_entry(
                    contract_id=owner_contract_id, contract_status="pending", author_id=creator_project_member_id)

            # Assign ownership
            ProjectDA.assign_owner({'project_id': project_id,
                                    'owner_id': owner_project_member_id})

            # Assign project roles
            ProjectDA.assign_project_role(
                {'project_id': project_id, 'project_member_id': creator_project_member_id, 'project_role_id': creator_project_role_id})

            resp.body = json.dumps({
                "success": True,
                "data": {"project_id": project_id},
                "description": 'Project created successfully'
            })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_put(self, req, resp, project_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (company_id, creator_project_role_id, owner_member_id, project_title, project_type, project_description, project_start_date, project_estimated_days,) = request.get_json_or_form(
                "company_id", "creator_project_role_id", "owner_member_id", "project_title", "project_type", "project_description", "project_start_date", "project_estimated_days", req=req)
            author_id = ProjectDA.get_project_member_id(project_id, member_id)
            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            # Check who's the owner now
            current_owner_project_member_id = ProjectDA.get_current_owner(
                project_id)

            # New owner -- First check if alreadty a team member
            new_owner_project_member_id = ProjectDA.get_project_member_id(
                project_id, owner_member_id)
            if not new_owner_project_member_id:
                # Not in the team yet
                new_owner_project_member_id = ProjectDA.create_project_member(
                    {"project_id": project_id, "member_id": owner_member_id, 'privileges': ['approve', 'create', 'view', 'edit']})

            # If there was no owner, or new owner is different
            if not current_owner_project_member_id or new_owner_project_member_id != current_owner_project_member_id:
                ProjectDA.assign_owner(
                    {'project_id': project_id, 'owner_id': new_owner_project_member_id})

            # Update the rest
            updated = ProjectDA.update_project_entry({"project_id": project_id,
                                                      'company_id': company_id,
                                                      'project_title': project_title,
                                                      'project_type': project_type,
                                                      'project_description': project_description,
                                                      'start_date': project_start_date,
                                                      'estimated_days': f"{project_estimated_days} days",
                                                      "author_id": author_id})
            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'Project updated successfully'
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": 'Something went wrong when updating the project'
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_delete(self, req, resp, project_id):
        member_id = req.context.auth['session']['member_id']
        try:
            author_id = ProjectDA.get_project_member_id(project_id, member_id)
            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            deleted = ProjectDA.hard_delete_project_entry(project_id)

            if deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'Project deleted successfully'
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": 'Something went wrong when deleting the project'
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    # Will perform soft-delete of all tasks
    def on_post_soft_delete(self, req, resp, project_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            element_ids = ProjectDA.get_ids_of_project(
                project_id=project_id, tasks_only=False, exclude_status='delete')

            if not element_ids:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'No tasks to delete'
                })

            deleted = []
            for el_id in element_ids:
                ok = ProjectDA.add_element_status_record(
                    element_id=el_id, author_id=author_id, status="delete")
                deleted.append(ok)

            if len(deleted) > 0 and not None in deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'All project tasks marked deleted successfully'
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": 'Something went wrong marking project deleted'
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    # WIll set previous status for all soft-deleted items
    def on_post_project_restore(self, req, resp, project_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            element_ids = ProjectDA.get_ids_of_project(
                project_id=project_id, tasks_only=False)

            restored = []
            for el_id in element_ids:
                last_status = ProjectDA.get_last_status(el_id, 'delete')
                if not last_status:
                    last_status = None
                ok = ProjectDA.add_element_status_record(
                    el_id, author_id, last_status)
                restored.append(ok)

            if len(restored) > 0 and not None in restored:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'All project tasks restored'
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": 'Something went when restoring project tasks'
                })
        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_project_suspend(self, req, resp, project_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            element_ids = ProjectDA.get_ids_of_project(
                project_id=project_id, tasks_only=False, exclude_status='suspend')

            if not element_ids:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'No tasks to delete'
                })

            suspended = []
            for el_id in element_ids:
                ok = ProjectDA.add_element_status_record(
                    element_id=el_id, author_id=author_id, status="suspend")
                suspended.append(ok)

            if len(suspended) > 0 and not None in suspended:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'All project tasks marked suspended successfully'
                })

            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": 'Something went when marking tasks suspended'
                })
        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_project_unsuspend(self, req, resp, project_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            element_ids = ProjectDA.get_ids_of_project(
                project_id=project_id, tasks_only=False)

            restored = []
            for el_id in element_ids:
                last_status = ProjectDA.get_last_status(el_id, 'suspend')
                if not last_status:
                    last_status = None
                ok = ProjectDA.add_element_status_record(
                    el_id, author_id, last_status)
                restored.append(ok)

            if len(restored) > 0 and not None in restored:
                resp.body = json.dumps({
                    "success": True,
                    "description": 'All project tasks restored'
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": 'Something went when restoring project tasks'
                })
        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_member(self, req, resp):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (project_id, members,) = request.get_json_or_form(
                "project_id", "members", req=req)
            group_id = ProjectDA.group_id_by_project_id(project_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            if not members:
                members = list()

            if isinstance(members, list):
                # Member ids of persons already in the project
                onboarded_member_ids = ProjectDA.get_member_ids_for_project(
                    project_id=project_id)

                new_members = set(members) - set(onboarded_member_ids)
                # Last item makes sure we don't delete ourselves
                discarded_members = set(
                    onboarded_member_ids) - set(members) - {member_id}

                if len(new_members) > 0:
                    for member_id in new_members:
                        GroupMembershipDA().create_group_membership(
                            group_id=group_id, member_id=member_id)

                        project_member_id = ProjectDA.create_project_member(
                            {"project_id": project_id, "member_id": member_id, "privileges": ['view']})
                        default_rate = ProjectDA.get_member_default_rate(
                            member_id)
                        contract_id = ProjectDA.create_contract(
                            {'project_member_id': project_member_id, "pay_rate": default_rate["pay_rate"], "currency_code_id": default_rate["currency_code_id"], "rate_type": "hourly", "author_id": author_id})
                        status_updated = ProjectDA.create_contract_status_entry(
                            contract_id=contract_id, contract_status="pending", author_id=author_id)

                if len(discarded_members) > 0:
                    for member_id in discarded_members:
                        GroupMembershipDA().remove_group_member(group_id=group_id, member_id=member_id)
                        discarded_project_member_id = ProjectDA.get_project_member_id(
                            project_id, member_id)
                        contract_id = ProjectDA.get_id_by_project_member(
                            project_member_id=discarded_project_member_id)
                        status_updated = ProjectDA.create_contract_status_entry(
                            contract_id=contract_id, contract_status="cancel", author_id=author_id)
                        ProjectDA.delete_project_member(
                            project_member_id=discarded_project_member_id)

                resp.body = json.dumps({
                    "success": True,
                    "description": 'Team successfully assigned'
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_member_role(self, req, resp):
        try:
            (project_id, roles_data) = request.get_json_or_form(
                "project_id", "roles_data", req=req)

            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)

            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            if len(roles_data) > 0:
                for item in roles_data:
                    (project_member_id, role_ids) = itemgetter(
                        "project_member_id", "role_ids")(item)

                    existing_roles = ProjectDA.get_project_roles_for_member(
                        {"project_id": project_id, "project_member_id": project_member_id})
                    if not existing_roles:
                        existing_roles = []
                    if not role_ids:
                        role_ids = []

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
            logger.exception(err)
            raise err

    @check_session
    def on_post_member_privilege(self, req, resp):
        try:
            (project_id, privileges_data) = request.get_json_or_form(
                "project_id", "privileges_data", req=req)

            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)

            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            # We trigger sending contract invites at this stage as it is the last step of project creation
            contract_ids = ProjectDA.get_active_hourly_contracts_by_project(
                project_id)
            if contract_ids and len(contract_ids) > 0:
                for c_id in contract_ids:
                    invite_id = ProjectDA.create_invite(c_id)
                    if invite_id:
                        ProjectDA.create_invite_status(invite_id, author_id)

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
            logger.exception(err)
            raise err

    # Epics/tremors/stories/tasks
    @check_session
    def on_post_element(self, req, resp):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (project_id, parent_id, element_type, title, description, est_hours, contract_id, rate_type) = request.get_json_or_form(
                "project_id", "parent_id", "element_type", "title", "description", "est_hours", "contract_id", "rate_type", req=req)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'create' not in author_privileges:
                raise NotEnoughPriviliges

            if json.convert_null(contract_id):
                if contract_id not in ProjectDA.get_active_hourly_contracts_by_project(project_id):
                    raise ContractDoesNotBelongProject

            parsed_est_hours = json.convert_null(est_hours)
            element_id = ProjectDA.insert_element({"project_id": project_id, "parent_id": json.convert_null(parent_id), "element_type": element_type,
                                                   "title": title, "description": description, "contract_id": json.convert_null(contract_id), "est_hours": f"{parsed_est_hours} hours" if parsed_est_hours else None,  "rate_type": rate_type, "author_id": author_id,
                                                   "est_rate": None, "currency_code_id": None, "due_date": None})

            # Create define status
            ProjectDA.add_element_status_record(
                element_id=element_id, author_id=author_id, status='define')

            if element_id:
                resp.body = json.dumps({
                    "success": True,
                    "description": f"{element_type.capitalize()} created successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": f"Something went wrong when creating {element_type}"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_put_element(self, req, resp, element_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (project_id, parent_id, element_type, title, description, contract_id, est_hours, element_status) = request.get_json_or_form(
                "project_id", "parent_id", "element_type", "title", "description", "contract_id", "est_hours", "element_status", req=req)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)

            if element_status == 'complete':
                if 'approve' not in author_privileges:
                    raise NotEnoughPriviliges
            else:
                if 'edit' not in author_privileges:
                    raise NotEnoughPriviliges

            updated = ProjectDA.update_element({"element_id": element_id, "project_id": project_id, "parent_id": json.convert_null(
                parent_id), "element_type": element_type, "title": title, "description": description, "contract_id": json.convert_null(contract_id), "est_hours": json.convert_null(est_hours), "author_id": author_id,
                "est_rate": None, "currency_code_id": None, "due_date": None})

            if json.convert_null(element_status):
                last_status = ProjectDA.get_last_status(element_id=element_id)
                if not last_status or last_status != element_status:
                    ProjectDA.add_element_status_record(
                        element_id=element_id, author_id=author_id, status=element_status)

            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": f"{element_type.capitalize()} updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": f"Something went wrong when updating {element_type}"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_delete_element(self, req, resp, element_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_elements_project(element_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            family_ids = ProjectDA.get_ids_of_family(
                element_id=element_id, tasks_only=False, exclude_status="delete")

            deleted = []
            for family_member_id in family_ids:
                item_success = ProjectDA.add_element_status_record(
                    element_id=family_member_id, author_id=author_id, status="delete")
                deleted.append(item_success)

            if None not in deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Items deleted successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deleting items"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_element_restore(self, req, resp, element_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_elements_project(element_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            family_ids = ProjectDA.get_ids_of_family(
                element_id=element_id, tasks_only=False)

            restored = []
            for family_member_id in family_ids:
                last_status = ProjectDA.get_last_status(
                    family_member_id, 'delete')
                if not last_status:
                    last_status = None
                item_success = ProjectDA.add_element_status_record(
                    element_id=family_member_id, author_id=author_id, status=last_status)
                restored.append(item_success)

            if None not in restored:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Items restored successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when restoring items"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_element_suspend(self, req, resp, element_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_elements_project(element_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            family_ids = ProjectDA.get_ids_of_family(
                element_id=element_id, tasks_only=True, exclude_status='suspend')

            suspended = []
            for family_member_id in family_ids:
                item_success = ProjectDA.add_element_status_record(
                    element_id=family_member_id, author_id=author_id, status="suspend")
                suspended.append(item_success)

            if None not in suspended:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Items suspended successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when suspending items"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_element_unsuspend(self, req, resp, element_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_elements_project(element_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            family_ids = ProjectDA.get_ids_of_family(
                element_id=element_id, tasks_only=True)

            unsuspended = []
            for family_member_id in family_ids:
                last_status = ProjectDA.get_last_status(
                    family_member_id, 'suspend')
                if not last_status:
                    last_status = None
                item_success = ProjectDA.add_element_status_record(
                    element_id=family_member_id, author_id=author_id, status=last_status)
                unsuspended.append(item_success)

            if None not in unsuspended:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Items unsuspended successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when unsuspending items"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    # Note
    @check_session
    def on_post_note(self, req, resp):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (element_note, element_id) = request.get_json_or_form(
                "element_note", "element_id", req=req)
            project_id = ProjectDA.get_elements_project(element_id)
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            inserted = ProjectDA.add_note(
                {"project_element_id": element_id, "element_note": element_note, "author_id": author_id})
            if inserted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Comment added successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when creataing comment"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_put_note(self, req, resp, note_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (element_note, element_id) = request.get_json_or_form(
                "element_note", "element_id", req=req)
            project_id = ProjectDA.get_project_by_note_id(note_id)
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            updated = ProjectDA.update_note(
                {"note_id": note_id, "element_note": element_note, "author_id": author_id})
            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Comment updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating comment"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_delete_note(self, req, resp, note_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_project_by_note_id(note_id)
            author_id = ProjectDA.get_project_member_id(project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            deleted = ProjectDA.delete_note(note_id)

            if deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Comment deleted successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deleting comment"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    # Time
    @check_session
    def on_post_time(self, req, resp):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (element_summary, element_time, element_id) = request.get_json_or_form(
                "element_summary", "element_time", "element_id", req=req)
            project_id = ProjectDA.get_elements_project(element_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            inserted = ProjectDA.add_time(
                {"project_element_id": element_id, "element_summary": element_summary, "element_time": element_time, "author_id": author_id})
            if inserted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Time record added successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when adding time record"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_put_time(self, req, resp, time_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_project_by_time_id(time_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            (element_summary, element_time) = request.get_json_or_form(
                "element_summary", "element_time", req=req)

            updated = ProjectDA.update_time(
                {"time_id": time_id, "element_summary": element_summary, "element_time": element_time, "author_id": author_id})
            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "TIme record updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating time record"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_delete_time(self, req, resp, time_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            project_id = ProjectDA.get_project_by_time_id(time_id)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'edit' not in author_privileges:
                raise NotEnoughPriviliges

            deleted = ProjectDA.delete_time(time_id)
            if deleted:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Time record deleted successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deleting time record"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    # Invite
    @check_session
    def on_post_invite_reaction(self, req, resp, invite_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (is_accept, project_id, contract_id) = request.get_json_or_form(
                "isAccept", "project_id", "contract_id", req=req)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            if author_id != ProjectDA.get_project_member_id_by_invite_id(invite_id):
                raise MemberDoesNotBelongToContract

            invite_handled = ProjectDA.create_invite_status(
                invite_id=invite_id, create_by=author_id, invite_status='Accepted' if is_accept else 'Declined')
            contract_updated = ProjectDA.create_contract_status_entry(
                contract_id=contract_id, contract_status='active' if is_accept else 'cancel', author_id=author_id)
            if contract_updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": f"Contract has been {'accepted' if is_accept else 'declined'}"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": f"Something went wrong when {'accepting' if is_accept else 'declining'} contract"
                })
        except Exception as err:
            logger.exception(err)
            raise err

    # Milestones
    @check_session
    def on_post_milestone(self, req, resp):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (project_id, project_member_id, parent_id, title, description, pay_rate, currency_code_id, due_date) = request.get_json_or_form(
                "project_id", "project_member_id", "parent_id", "title", "description", "pay_rate", "currency_code_id", "due_date", req=req)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)
            if 'create' not in author_privileges:
                raise NotEnoughPriviliges

            # if a member is provided => create a pending fixed contract
            contract_id = None
            if (json.convert_null(project_member_id)):
                contract_id = ProjectDA.create_contract(
                    {'project_member_id': project_member_id, "pay_rate": pay_rate, "currency_code_id": currency_code_id, "rate_type": "fixed", "author_id": author_id})
                contract_status_updated = ProjectDA.create_contract_status_entry(
                    contract_id=contract_id, contract_status="pending", author_id=author_id)

            milestone_id = ProjectDA.insert_element({"project_id": project_id, "parent_id": parent_id, "element_type": 'milestone', "title": title,
                                                     "description": description, "contract_id": contract_id, "est_hours": None, "rate_type": "fixed", "author_id": author_id,
                                                     "est_rate": pay_rate, "currency_code_id": currency_code_id, "due_date": due_date})

            # Create define status
            ProjectDA.add_element_status_record(
                element_id=milestone_id, author_id=author_id, status='define')

            # Trigger an invite if contract
            if contract_id:
                invite_id = ProjectDA.create_invite(contract_id)
                if invite_id:
                    ProjectDA.create_invite_status(invite_id, author_id)

            if milestone_id:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Milestone created successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when creating milestone"
                })
        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_put_milestone(self, req, resp, milestone_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (project_id, project_member_id, parent_id, title, description, pay_rate, currency_code_id,  due_date, status) = request.get_json_or_form(
                "project_id", "project_member_id", "parent_id", "title", "description", "pay_rate", "currency_code_id", "due_date", "status", req=req)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)

            if status == 'complete':
                if 'approve' not in author_privileges:
                    raise NotEnoughPriviliges
            else:
                if 'edit' not in author_privileges:
                    raise NotEnoughPriviliges

            # Create new contract if member changed
            assigned_project_member_id = ProjectDA.get_assigned_project_member_id(
                milestone_id)
            contract_id = None
            if project_member_id != assigned_project_member_id:
                contract_id = ProjectDA.create_contract(
                    {'project_member_id': project_member_id, "pay_rate": pay_rate, "currency_code_id": currency_code_id, "rate_type": "fixed", "author_id": author_id})
                contract_status_updated = ProjectDA.create_contract_status_entry(
                    contract_id=contract_id, contract_status="pending", author_id=author_id)
            else:
                contract_id = ProjectDA.get_contract_id_by_element(
                    milestone_id)

                # We want to handle fixed contract status here if it has changed

                new_contract_status = None
                if status == 'complete':
                    new_contract_status = 'final'
                elif status == 'cancel':
                    new_contract_status = 'cancel'
                elif status == 'suspend':
                    new_contract_status = 'suspend'
                elif status == 'in progress':
                    new_contract_status = 'active'

                current_contract_status = ProjectDA.get_current_contract_status(
                    contract_id)
                if new_contract_status != current_contract_status:
                    contract_status_updated = ProjectDA.create_contract_status_entry(
                        contract_id=contract_id, contract_status=new_contract_status, author_id=author_id)

            milestone_updated = ProjectDA.update_element({
                "project_id": project_id,
                "parent_id": parent_id,
                "element_type": 'milestone',
                "title": title,
                "description": description,
                "contract_id": contract_id,
                "est_hours": None,
                "author_id": author_id,
                "element_id": milestone_id,
                "est_rate": pay_rate,
                "currency_code_id": currency_code_id,
                "due_date": due_date
            })

            if json.convert_null(status):
                last_status = ProjectDA.get_last_status(
                    element_id=milestone_id)
                if not last_status or last_status != status:
                    ProjectDA.add_element_status_record(
                        element_id=milestone_id, author_id=author_id, status=status)

            if milestone_updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Milestone updated successfully"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating milestone"
                })

        except Exception as err:
            logger.exception(err)
            raise err

    # Deactivate
    @check_session
    def on_post_deactivate(self, req, resp, project_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound

            current_owner = ProjectDA.get_current_owner(project_id=project_id)

            if current_owner != author_id:
                raise NotProjectOwner

            deactivated = ProjectDA.deactivate_project(project_id=project_id)

            if deactivated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Project deactivated"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when deactivating project"
                })
        except Exception as err:
            logger.exception(err)
            raise err

    # Update contract
    @check_session
    def on_put_contract_rate(self, req, resp, contract_id):
        try:
            member_id = req.context.auth["session"]["member_id"]
            (pay_rate, project_id, currency_code_id) = request.get_json_or_form(
                "pay_rate", "project_id", "currency_code_id", req=req)
            author_id = ProjectDA.get_project_member_id(
                project_id, member_id)

            if not author_id:
                raise ProjectMemberNotFound
            author_privileges = ProjectDA.get_project_member_privileges(
                author_id)

            if 'approve' not in author_privileges:
                raise NotEnoughPriviliges

            updated = ProjectDA.update_contract_rate(
                {"pay_rate": pay_rate, "currency_code_id": currency_code_id, "contract_id": contract_id})

            if updated:
                resp.body = json.dumps({
                    "success": True,
                    "description": "Contract updated"
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                    "description": "Something went wrong when updating contract"
                })
        except Exception as err:
            logger.exception(err)
            raise err
