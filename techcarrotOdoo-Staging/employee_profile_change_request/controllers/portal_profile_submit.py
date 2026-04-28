# -*- coding: utf-8 -*-
import json
import logging
import re
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

EDITABLE_FIELDS = [
    'work_phone', 'private_email', 'private_phone',
    'private_street', 'private_street2', 'private_city', 'private_zip',
    'whatsapp', 'linkedin', 'legal_name',
    'facebook_profile', 'insta_profile', 'twitter_profile',
    'l10n_in_relationship', 'emergency_phone', 'e_private_city',
    'emergency_contact_person_name', 'emergency_contact_person_phone',
    'alternate_mobile_number', 'emergency_contact_person_name_1',
    'emergency_contact_person_phone_1', 'second_alternative_number',
    'home_land_line_no',
    'spouse_passport_no', 'spouse_passport_issue_date',
    'spouse_passport_expiry_date', 'spouse_visa_no',
    'spouse_visa_expire_date', 'spouse_emirates_id_no',
    'spouse_emirates_issue_date', 'spouse_emirates_id_expiry_date',
    'spouse_aadhar_no',
    'dependent_child_name_1', 'dependent_child_dob_1',
    'dependent_child_passport_no',
    'dependent_child_passport_issue_date_1',
    'dependent_child_passport_expiry_date_1',
    'dependent_child_visa_no_1',
    'dependent_child_visa_expiration_date_1',
    'dependent_child_emirates_id_no_1',
    'dependent_child_emirates_id_issue_date_1',
    'dependent_child_emirates_id_expiry_date_1',
    'dependent_child_aadhar_no_1',
    'father_name', 'father_dob',
    'mother_name', 'mother_dob',
    'children', 'career_break_detail',
    'employee_nominee_name', 'employee_nominee_contact_no',
    'domain_worked', 'primary_skill', 'secondary_skill', 'tool_used',
    'industry_ref_name', 'industry_ref_email', 'industry_ref_mob_no',
    'home_country_id_name', 'home_country_id_number',
    'mother_tongue_name', 'language_known_name',
    'u_private_city', 'current_address', 'phone_code_1',
    'house_no', 'area_name', 'city', 'zip_code',
    'experience', 'current_role', 'industry_start_date',
    'last_organisation_name', 'last_location',
    'last_salary_per_annum_currency', 'last_salary_per_annum_amt',
    'reason_for_leaving', 'last_report_manager_name',
    'last_report_manager_designation', 'last_report_manager_mob_no',
    'last_report_manager_mail',
]

EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class EmployeePortalProfileSubmit(http.Controller):

    @http.route(
        '/my/employee/personal',
        type='http',
        auth='user',
        website=True,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def portal_employee_personal(self, **post):
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not employee:
            return request.redirect('/my')

        if request.httprequest.method == 'POST':
            return self._handle_post(employee, post)

        countries = request.env['res.country'].sudo().search(
            [], order='name'
        )
        return request.render(
            'employee_self_service_portal'
            '.portal_employee_profile_personal',
            {'employee': employee, 'countries': countries},
        )

    def _handle_post(self, employee, post):
        try:
            # ── Validate email fields ────────────────────────────
            email_fields = [
                'private_email',
                'industry_ref_email',
                'last_report_manager_mail',
            ]
            for field in email_fields:
                val = post.get(field, '').strip()
                if val and not EMAIL_PATTERN.match(val):
                    return request.make_json_response({
                        'success': False,
                        'error': f'Invalid email format: {field}',
                    })

            # ── Collect only editable fields ─────────────────────
            submitted = {}
            for field in EDITABLE_FIELDS:
                val = post.get(field)
                if val is not None and str(val).strip():
                    submitted[field] = str(val).strip()

            if not submitted:
                return request.make_json_response({
                    'success': False,
                    'error': 'No data was submitted.',
                })

            # ── Create change request ────────────────────────────
            req = request.env[
                'hr.profile.change.request'
            ].sudo().create({
                'employee_id':    employee.id,
                'submitted_data': json.dumps(submitted),
                'state':          'draft',
            })

            # ── Submit → state=pending + email to HR ─────────────
            req.action_submit()

            _logger.info(
                'Profile change request %s created for employee %s',
                req.name, employee.name,
            )

            return request.make_json_response({
                'success':   True,
                'reference': req.name,
                'message': (
                    'Your profile update request has been submitted. '
                    'HR will review and notify you by email.'
                ),
            })

        except Exception as e:
            _logger.error(
                'Error creating profile change request for %s: %s',
                employee.name, str(e),
            )
            return request.make_json_response({
                'success': False,
                'error':   str(e),
            })