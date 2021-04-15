import json

from app.util.db import source
import logging

logger = logging.getLogger(__name__)

def init_procedures():
    weekly_billing_hourly_procedure_query = f'''
        CREATE OR REPLACE FUNCTION get_weekly_billing_of_hourly_contract(owner_id integer, start_date date, end_date date)
            RETURNS TABLE(id integer, project_title VARCHAR, member_hours json)
          AS $$
        BEGIN
        RETURN QUERY
        with hourly_contracts as (
          select p2.id, p2.project_title
            from project_element_time pet
            left join project_element pe on pet.project_element_id = pe.id 
            left join project_owner_xref pox on pox.project_id = pe.project_id 
            left join project p2 on p2.id = pox.project_id 
            where pet.create_date between $2 and $3 and pox.owner_id = $1
            group by p2.id, p2.project_title
        ) 
        select 
          project_members_due.id,
          project_members_due.project_title,
          coalesce (json_agg(json_build_object(
            'member_id', project_members_due.member_id,
            'first_name', project_members_due.first_name,
            'last_name', project_members_due.last_name,
            'role', project_members_due.role,
            'date_hours', project_members_due.date_hours
          )), '[]') as member_hours
        from (
          select
          project_member_dates_due.id,
          project_member_dates_due.project_title,
          project_member_dates_due.member_id,
          project_member_dates_due.first_name,
          project_member_dates_due.last_name,
          project_member_dates_due.role,
          coalesce(json_agg(json_build_object(
            'create_date', project_member_dates_due.create_date,
            'hours', project_member_dates_due.hours,
            'rate', project_member_dates_due.pay_rate,
            'due', project_member_dates_due.due
          )), '[]') as date_hours
          from (
            select hourly_contracts.id, hourly_contracts.project_title, pm.member_id, member.first_name, member.last_name, job_title.name as role, pet2.create_date, sum(extract(EPOCH from pet2.element_time)/60) as hours, pmc.pay_rate , sum(extract(EPOCH from pet2.element_time*pmc.pay_rate)/3600) as due
            from project_element_time pet2 
            left join project_element pe2 on pe2.id = pet2.project_element_id 
            right join hourly_contracts on hourly_contracts.id = pe2.project_id
            left join project_member_contract pmc on pmc.id = pe2.contract_id 
            left join project_member pm on pm.id = pmc.project_member_id 
            left join member on member.id = pm.member_id
            left join job_title on job_title.id = member.job_title_id 
            where pet2.create_date between $2 and $3
            group by hourly_contracts.id, hourly_contracts.project_title, pm.member_id, pet2.create_date, pmc.pay_rate, member.first_name, member.last_name, job_title.name
          ) as project_member_dates_due
          group by project_member_dates_due.id, project_member_dates_due.project_title, project_member_dates_due.member_id, project_member_dates_due.first_name, project_member_dates_due.last_name, project_member_dates_due.role
        ) as project_members_due
        group by project_members_due.id, project_members_due.project_title;
        END;
        $$
        LANGUAGE plpgsql;
    '''

    weekly_billing_fixed_procedure_query = f'''
        CREATE OR REPLACE FUNCTION get_weekly_billing_of_fixed_contract(owner_id integer, start_date date, end_date date)
        	RETURNS TABLE(id integer, title varchar, total_cost numeric, paid_this_week numeric, total_paid numeric, pending numeric, this_week_pending numeric, milestone_info json)
        AS $$
        BEGIN
        RETURN QUERY

        with parent_contracts as (	select pe.parent_id
          from project_element_status pes 
          left join project_element pe on pes.project_element_id = pe.id
          left join project_owner_xref pox on pox.project_id = pe.project_id and pox.owner_id = $1
          where pes.element_status = 'complete' and pes.update_date between $2 and $3 and pe.element_type = 'milestone'
          group by pe.parent_id 
        )
        select pe2.id, pe2.title, sum(pe3.est_rate) as total_cost, sum(case  when pi1.id is null then 0 else pe3.est_rate end) as paid_this_week, sum(case when pi2.id is null then 0 else pe3.est_rate end) as total_paid, sum(case when pi2.id is null then pe3.est_rate else 0 end) as pending, sum(case when pi3.id is null then 0 else pe3.est_rate end) as this_week_pending,
          COALESCE(json_agg(json_build_object(
                                    'id', pe3.id,
                                    'title', pe3.title ,
                                    'status', pes2.element_status,
                                    'member_id', member.id,
                                    'first_name', member.first_name,
                                    'last_name', member.last_name,
                                    'create_date', pe3.create_date,
                                    'update_date', pes2.update_date,
                                    'role', job_title.name
                                )), '[]') AS milestone_info
        from project_element pe2
        right join parent_contracts on pe2.id = parent_contracts.parent_id
        left join project_element pe3 on pe3.parent_id = pe2.id
        left join project_element_status pes2 on pe3.id = pes2.project_element_id and pes2.element_status = 'complete'
        left join project_member_contract pmc2 on pe3.contract_id = pmc2.id
        left join project_member pm on pmc2.project_member_id = pm.id
        left join member on pm.member_id = member.id
        left join job_title on job_title.id = member.job_title_id 
        left join project_invoice pi1 on pi1.project_element_id = pe3.id and pi1.paid_date between $2 and $3 and pi1.inv_status = 'paid'
        left join project_invoice pi2 on pi2.project_element_id = pe3.id and pi2.inv_status = 'paid'
        left join project_invoice pi3 on pi3.project_element_id = pe3.id and pi3.create_date between $2 and $3 and pi3.inv_status = 'pending'
        group by pe2.id, pe2.title;
          END;
          $$
        LANGUAGE plpgsql;
    '''
  
    source.execute(weekly_billing_hourly_procedure_query, None)
    source.execute(weekly_billing_fixed_procedure_query, None)

