# -*- coding: utf-8 -*-
import json
import logging
import re
import base64

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── ALL editable fields including ALL tabs ────────────────────────────────────
EDITABLE_FIELDS = [

    # Basic Info — Contact
    'work_phone',
    'private_email',
    'private_phone',
    'private_street',
    'private_street2',
    'private_city',
    'private_zip',
    'private_state_id',
    'whatsapp',
    'linkedin',
    'legal_name',
    'facebook_profile',
    'insta_profile',
    'twitter_profile',

    # ── COUNTRY FIELDS FIX ───────────────────────────────────────────────────
    'country_id',
    'nationality_at_birth_id',
    'issue_countries_id',

    # Basic Info — Personal
    'blood_group',

    # Basic Info — Identity
    'issue_date',
    'expiry_date',

    # Basic Info — Emergency
    'l10n_in_relationship',
    'emergency_phone',
    'e_private_city',

    # Professional — Emergency Contact
    'emergency_contact_person_name',
    'emergency_contact_person_phone',
    'alternate_mobile_number',
    'emergency_contact_person_name_1',
    'emergency_contact_person_phone_1',
    'second_alternative_number',
    'home_land_line_no',

    # Professional — Spouse
    'spouse_passport_no',
    'spouse_passport_issue_date',
    'spouse_passport_expiry_date',
    'spouse_visa_no',
    'spouse_visa_expire_date',
    'spouse_emirates_id_no',
    'spouse_emirates_issue_date',
    'spouse_emirates_id_expiry_date',
    'spouse_aadhar_no',

    # Family — Child
    'dependent_child_name_1',
    'dependent_child_dob_1',
    'dependent_child_passport_no',
    'dependent_child_passport_issue_date_1',
    'dependent_child_passport_expiry_date_1',
    'dependent_child_visa_no_1',
    'dependent_child_visa_expiration_date_1',
    'dependent_child_emirates_id_no_1',
    'dependent_child_emirates_id_issue_date_1',
    'dependent_child_emirates_id_expiry_date_1',
    'dependent_child_aadhar_no_1',

    # Family
    'father_name',
    'father_dob',
    'mother_name',
    'mother_dob',
    'children',
    'career_break_detail',

    # Professional — Nominee
    'employee_nominee_name',
    'employee_nominee_contact_no',
    'domain_worked',
    'primary_skill',
    'secondary_skill',
    'tool_used',

    # Professional — Industry
    'industry_ref_name',
    'industry_ref_email',
    'industry_ref_mob_no',
    'home_country_id_name',
    'home_country_id_number',

    # Family — Languages
    'mother_tongue_name',
    'language_known_name',

    # Professional — Work Location
    'u_private_city',
    'current_address',
    'phone_code_1',
    'house_no',
    'area_name',
    'city',
    'zip_code',

    # Professional — General
    'experience',
    'current_role',
    'industry_start_date',

    # Professional — Last Organisation
    'last_organisation_name',
    'last_location',
    'last_salary_per_annum_currency',
    'last_salary_per_annum_amt',
    'reason_for_leaving',
    'last_report_manager_name',
    'last_report_manager_designation',
    'last_report_manager_mob_no',
    'last_report_manager_mail',

    # Professional — Industry Details
    'previous_company_name',
    'designation',
    'period_in_company',
    'reason_of_leaving',
]

# ── FILE FIELDS ───────────────────────────────────────────────────────────────
FILE_FIELDS = [
    'emirates_id_file',
    'passport_file',
    'other_documents',
    'has_work_permit',
]

EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

# ── ISD CODE VALIDATION ──────────────────────────────────────────────────────
ISD_PATTERN = re.compile(r'^\+[1-9][0-9]{0,2}$')


class EmployeePortalProfileSubmit(http.Controller):

    # =========================================================================
    # HOME
    # =========================================================================
    @http.route(
        '/my/employee',
        type='http',
        auth='user',
        website=True,
        methods=['GET']
    )
    def portal_employee_home(self, **kwargs):
        return request.redirect('/my/employee/personal')

    # =========================================================================
    # MAIN PAGE
    # =========================================================================
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
            [('user_id', '=', request.env.user.id)],
            limit=1
        )

        if not employee:
            return request.redirect('/my')

        # ---------------------------------------------------------------------
        # POST
        # ---------------------------------------------------------------------
        if request.httprequest.method == 'POST':
            return self._handle_post(employee, post)

        # ---------------------------------------------------------------------
        # GET
        # ---------------------------------------------------------------------
        portal_overlay = {}

        if (
            employee.last_portal_submission
            and employee.last_submission_state in ('pending', 'rejected')
        ):
            try:
                portal_overlay = json.loads(employee.last_portal_submission)
            except Exception:
                portal_overlay = {}

        notification = None
        state = employee.last_submission_state

        # ---------------------------------------------------------------------
        # APPROVED
        # ---------------------------------------------------------------------
        if state == 'approved':

            approved_req = request.env[
                'hr.profile.change.request'
            ].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'approved'),
            ], order='review_date desc', limit=1)

            notification = {
                'type': 'success',
                'message': 'Your profile has been updated successfully.',
                'reason': False,
                'request_name': approved_req.name if approved_req else '',
            }

        # ---------------------------------------------------------------------
        # REJECTED
        # ---------------------------------------------------------------------
        elif state == 'rejected':

            rejected_req = request.env[
                'hr.profile.change.request'
            ].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'rejected'),
            ], order='create_date desc', limit=1)

            if rejected_req:
                notification = {
                    'type': 'danger',
                    'message': 'Your profile update request was rejected.',
                    'reason': (
                        rejected_req.rejection_reason
                        or 'No reason provided.'
                    ),
                    'request_name': rejected_req.name,
                }

        # ---------------------------------------------------------------------
        # PENDING
        # ---------------------------------------------------------------------
        elif state == 'pending':

            pending_req = request.env[
                'hr.profile.change.request'
            ].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
            ], order='create_date desc', limit=1)

            if pending_req:
                notification = {
                    'type': 'warning',
                    'message': 'Your profile update request is pending HR review.',
                    'reason': False,
                    'request_name': pending_req.name,
                }

        countries = request.env['res.country'].sudo().search(
            [],
            order='name'
        )

        return request.render(
            'employee_self_service_portal.portal_employee_profile_personal',
            {
                'employee': employee,
                'countries': countries,
                'all_countries': countries,
                'notification': notification,
                'portal_overlay': portal_overlay,
            },
        )

    # =========================================================================
    # HANDLE SAVE
    # =========================================================================
    def _handle_post(self, employee, post):

        try:

            # ================================================================
            # CHECK PENDING REQUEST
            # ================================================================
            pending_request = request.env[
                'hr.profile.change.request'
            ].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
            ], limit=1)

            if pending_request:
                return request.make_json_response({
                    'success': False,
                    'error': (
                        'Your previous request is still pending HR approval.'
                    )
                })

            # ================================================================
            # EMAIL VALIDATION
            # ================================================================
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
                        'error': 'Invalid email format.',
                    })

            # ================================================================
            # ISD VALIDATION
            # ================================================================
            isd_fields = [
                'phone_code_1',
            ]

            for field in isd_fields:

                val = post.get(field, '').strip()

                if val and not ISD_PATTERN.match(val):
                    return request.make_json_response({
                        'success': False,
                        'error': (
                            'ISD code must start with + followed by '
                            '1-3 digits. Example: +91, +971, +1'
                        )
                    })

            # ================================================================
            # COLLECT TEXT VALUES
            # ================================================================
            submitted = {}

            for field in EDITABLE_FIELDS:

                val = post.get(field)

                if val is not None:
                    submitted[field] = str(val).strip()

            # ================================================================
            # FILES
            # ================================================================
            files_submitted = {}

            for field in FILE_FIELDS:

                file_obj = request.httprequest.files.get(field)

                if file_obj and file_obj.filename:
                    files_submitted[field] = file_obj

            # ================================================================
            # NOTHING SUBMITTED
            # ================================================================
            if not submitted and not files_submitted:

                return request.make_json_response({
                    'success': False,
                    'error': 'No data submitted.',
                })

            # ================================================================
            # COMPARE VALUES
            # ================================================================
            changed = {}

            for field, new_val in submitted.items():

                try:

                    current = getattr(employee, field, False)

                    # ========================================================
                    # MANY2ONE FIX
                    # ========================================================
                    if hasattr(current, 'id'):

                        current_id = str(current.id or '').strip()
                        new_id = str(new_val or '').strip()

                        if current_id != new_id:
                            changed[field] = new_val

                    # ========================================================
                    # NORMAL FIELDS
                    # ========================================================
                    else:

                        if current in [False, None]:
                            current_val = ''
                        else:
                            current_val = str(current).strip()

                        new_val = str(new_val).strip()

                        if current_val != new_val:
                            changed[field] = new_val

                except Exception:
                    changed[field] = new_val

            # ================================================================
            # FILE CHANGES
            # ================================================================
            file_changed_fields = {}

            for field, file_obj in files_submitted.items():

                try:

                    file_data = base64.b64encode(
                        file_obj.read()
                    ).decode('utf-8')

                    file_changed_fields[field] = file_data

                    changed[field] = '[FILE] %s' % file_obj.filename

                except Exception as e:

                    _logger.error(
                        'File upload failed for %s : %s',
                        field,
                        str(e)
                    )

            # ================================================================
            # NO CHANGES
            # ================================================================
            if not changed and not file_changed_fields:

                return request.make_json_response({
                    'success': True,
                    'reference': '',
                    'no_change': True,
                    'message': (
                        'No changes detected. '
                        'Your profile is already up to date.'
                    )
                })

            # ================================================================
            # SAVE FILES DIRECTLY
            # ================================================================
            if file_changed_fields:
                employee.sudo().write(file_changed_fields)

            # ================================================================
            # CREATE PROFILE CHANGE REQUEST
            # ================================================================
            reference = ''

            if changed:

                req = request.env[
                    'hr.profile.change.request'
                ].sudo().create({
                    'employee_id': employee.id,
                    'submitted_data': json.dumps(changed),
                    'state': 'draft',
                })

                # ------------------------------------------------------------
                # SUBMIT
                # ------------------------------------------------------------
                if hasattr(req, 'action_submit'):
                    req.action_submit()

                # ------------------------------------------------------------
                # FORCE REFERENCE IF EMPTY
                # ------------------------------------------------------------
                if not req.name or req.name == '/':
                    sequence = request.env['ir.sequence'].sudo().next_by_code(
                        'hr.profile.change.request'
                    )

                    if sequence:
                        req.sudo().write({
                            'name': sequence
                        })

                reference = req.name or ''

                # ------------------------------------------------------------
                # STORE LAST SUBMISSION
                # ------------------------------------------------------------
                employee.sudo().write({
                    'last_portal_submission': json.dumps(changed),
                    'last_submission_state': 'pending',
                })

                _logger.info(
                    'PCR CREATED : %s for %s',
                    reference,
                    employee.name
                )

            # ================================================================
            # SUCCESS RESPONSE
            # ================================================================
            return request.make_json_response({
                'success': True,
                'reference': reference,
                'no_change': False,
                'message': (
                    'Your profile update request '
                    'has been submitted successfully.'
                )
            })

        # ====================================================================
        # ERROR
        # ====================================================================
        except Exception as e:

            _logger.exception(
                'PROFILE UPDATE ERROR : %s',
                str(e)
            )

            return request.make_json_response({
                'success': False,
                'error': str(e),
            })






#
# # -*- coding: utf-8 -*-
# import json
# import logging
# import re
# import base64
#
# from odoo import http
# from odoo.http import request
#
# _logger = logging.getLogger(__name__)
#
# # ── ALL editable fields including ALL tabs ────────────────────────────────────
# EDITABLE_FIELDS = [
#
#     # Basic Info — Contact
#     'work_phone', 'private_email', 'private_phone',
#     'private_street', 'private_street2', 'private_city', 'private_zip',
#     'private_state_id',
#     'whatsapp', 'linkedin', 'legal_name',
#     'facebook_profile', 'insta_profile', 'twitter_profile',
#
#     # Basic Info — Personal
#     'blood_group',
#
#     # Basic Info — Identity
#     'issue_date', 'expiry_date',
#
#     # Basic Info — Emergency
#     'l10n_in_relationship', 'emergency_phone', 'e_private_city',
#
#     # Professional — Emergency Contact
#     'emergency_contact_person_name',
#     'emergency_contact_person_phone',
#     'alternate_mobile_number',
#     'emergency_contact_person_name_1',
#     'emergency_contact_person_phone_1',
#     'second_alternative_number',
#     'home_land_line_no',
#
#     # Professional — Spouse
#     'spouse_passport_no',
#     'spouse_passport_issue_date',
#     'spouse_passport_expiry_date',
#     'spouse_visa_no',
#     'spouse_visa_expire_date',
#     'spouse_emirates_id_no',
#     'spouse_emirates_issue_date',
#     'spouse_emirates_id_expiry_date',
#     'spouse_aadhar_no',
#
#     # Family — Child
#     'dependent_child_name_1',
#     'dependent_child_dob_1',
#     'dependent_child_passport_no',
#     'dependent_child_passport_issue_date_1',
#     'dependent_child_passport_expiry_date_1',
#     'dependent_child_visa_no_1',
#     'dependent_child_visa_expiration_date_1',
#     'dependent_child_emirates_id_no_1',
#     'dependent_child_emirates_id_issue_date_1',
#     'dependent_child_emirates_id_expiry_date_1',
#     'dependent_child_aadhar_no_1',
#
#     # Family
#     'father_name',
#     'father_dob',
#     'mother_name',
#     'mother_dob',
#     'children',
#     'career_break_detail',
#
#     # Professional — Nominee
#     'employee_nominee_name',
#     'employee_nominee_contact_no',
#     'domain_worked',
#     'primary_skill',
#     'secondary_skill',
#     'tool_used',
#
#     # Professional — Industry
#     'industry_ref_name',
#     'industry_ref_email',
#     'industry_ref_mob_no',
#     'home_country_id_name',
#     'home_country_id_number',
#
#     # Family — Languages
#     'mother_tongue_name',
#     'language_known_name',
#
#     # Professional — Work Location
#     'u_private_city',
#     'current_address',
#     'phone_code_1',
#     'house_no',
#     'area_name',
#     'city',
#     'zip_code',
#
#     # Professional — General
#     'experience',
#     'current_role',
#     'industry_start_date',
#
#     # Professional — Last Organisation
#     'last_organisation_name',
#     'last_location',
#     'last_salary_per_annum_currency',
#     'last_salary_per_annum_amt',
#     'reason_for_leaving',
#     'last_report_manager_name',
#     'last_report_manager_designation',
#     'last_report_manager_mob_no',
#     'last_report_manager_mail',
#
#     # Professional — Industry Details
#     'previous_company_name',
#     'designation',
#     'period_in_company',
#     'reason_of_leaving',
# ]
#
# # ── FILE FIELDS ───────────────────────────────────────────────────────────────
# FILE_FIELDS = [
#     'emirates_id_file',
#     'passport_file',
#     'other_documents',
#     'has_work_permit',
# ]
#
# EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
#
# # ── ISD CODE VALIDATION ──────────────────────────────────────────────────────
# ISD_PATTERN = re.compile(r'^\+[1-9][0-9]{0,2}$')
#
#
# class EmployeePortalProfileSubmit(http.Controller):
#
#     # =========================================================================
#     # HOME
#     # =========================================================================
#     @http.route(
#         '/my/employee',
#         type='http',
#         auth='user',
#         website=True,
#         methods=['GET']
#     )
#     def portal_employee_home(self, **kwargs):
#         return request.redirect('/my/employee/personal')
#
#     # =========================================================================
#     # MAIN PAGE
#     # =========================================================================
#     @http.route(
#         '/my/employee/personal',
#         type='http',
#         auth='user',
#         website=True,
#         methods=['GET', 'POST'],
#         csrf=False,
#     )
#     def portal_employee_personal(self, **post):
#
#         employee = request.env['hr.employee'].sudo().search(
#             [('user_id', '=', request.env.user.id)],
#             limit=1
#         )
#
#         if not employee:
#             return request.redirect('/my')
#
#         # ---------------------------------------------------------------------
#         # POST
#         # ---------------------------------------------------------------------
#         if request.httprequest.method == 'POST':
#             return self._handle_post(employee, post)
#
#         # ---------------------------------------------------------------------
#         # GET
#         # ---------------------------------------------------------------------
#         portal_overlay = {}
#
#         if (
#             employee.last_portal_submission
#             and employee.last_submission_state in ('pending', 'rejected')
#         ):
#             try:
#                 portal_overlay = json.loads(employee.last_portal_submission)
#             except Exception:
#                 portal_overlay = {}
#
#         notification = None
#         state = employee.last_submission_state
#
#         # ---------------------------------------------------------------------
#         # APPROVED
#         # ---------------------------------------------------------------------
#         if state == 'approved':
#
#             approved_req = request.env[
#                 'hr.profile.change.request'
#             ].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'approved'),
#             ], order='review_date desc', limit=1)
#
#             notification = {
#                 'type': 'success',
#                 'message': 'Your profile has been updated successfully.',
#                 'reason': False,
#                 'request_name': approved_req.name if approved_req else '',
#             }
#
#         # ---------------------------------------------------------------------
#         # REJECTED
#         # ---------------------------------------------------------------------
#         elif state == 'rejected':
#
#             rejected_req = request.env[
#                 'hr.profile.change.request'
#             ].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'rejected'),
#             ], order='create_date desc', limit=1)
#
#             if rejected_req:
#                 notification = {
#                     'type': 'danger',
#                     'message': 'Your profile update request was rejected.',
#                     'reason': (
#                         rejected_req.rejection_reason
#                         or 'No reason provided.'
#                     ),
#                     'request_name': rejected_req.name,
#                 }
#
#         # ---------------------------------------------------------------------
#         # PENDING
#         # ---------------------------------------------------------------------
#         elif state == 'pending':
#
#             pending_req = request.env[
#                 'hr.profile.change.request'
#             ].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'pending'),
#             ], order='create_date desc', limit=1)
#
#             if pending_req:
#                 notification = {
#                     'type': 'warning',
#                     'message': 'Your profile update request is pending HR review.',
#                     'reason': False,
#                     'request_name': pending_req.name,
#                 }
#
#         countries = request.env['res.country'].sudo().search(
#             [],
#             order='name'
#         )
#
#         return request.render(
#             'employee_self_service_portal.portal_employee_profile_personal',
#             {
#                 'employee': employee,
#                 'countries': countries,
#                 'notification': notification,
#                 'portal_overlay': portal_overlay,
#             },
#         )
#
#     # =========================================================================
#     # HANDLE SAVE
#     # =========================================================================
#     def _handle_post(self, employee, post):
#
#         try:
#
#             # ================================================================
#             # CHECK PENDING REQUEST
#             # ================================================================
#             pending_request = request.env[
#                 'hr.profile.change.request'
#             ].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'pending'),
#             ], limit=1)
#
#             if pending_request:
#                 return request.make_json_response({
#                     'success': False,
#                     'error': (
#                         'Your previous request is still pending HR approval.'
#                     )
#                 })
#
#             # ================================================================
#             # EMAIL VALIDATION
#             # ================================================================
#             email_fields = [
#                 'private_email',
#                 'industry_ref_email',
#                 'last_report_manager_mail',
#             ]
#
#             for field in email_fields:
#
#                 val = post.get(field, '').strip()
#
#                 if val and not EMAIL_PATTERN.match(val):
#                     return request.make_json_response({
#                         'success': False,
#                         'error': 'Invalid email format.',
#                     })
#
#             # ================================================================
#             # ISD VALIDATION
#             # ================================================================
#             isd_fields = [
#                 'phone_code_1',
#             ]
#
#             for field in isd_fields:
#
#                 val = post.get(field, '').strip()
#
#                 if val and not ISD_PATTERN.match(val):
#                     return request.make_json_response({
#                         'success': False,
#                         'error': (
#                             'ISD code must start with + followed by '
#                             '1-3 digits. Example: +91, +971, +1'
#                         )
#                     })
#
#             # ================================================================
#             # COLLECT TEXT VALUES
#             # ================================================================
#             submitted = {}
#
#             for field in EDITABLE_FIELDS:
#
#                 val = post.get(field)
#
#                 if val is not None:
#                     submitted[field] = str(val).strip()
#
#             # ================================================================
#             # FILES
#             # ================================================================
#             files_submitted = {}
#
#             for field in FILE_FIELDS:
#
#                 file_obj = request.httprequest.files.get(field)
#
#                 if file_obj and file_obj.filename:
#                     files_submitted[field] = file_obj
#
#             # ================================================================
#             # NOTHING SUBMITTED
#             # ================================================================
#             if not submitted and not files_submitted:
#
#                 return request.make_json_response({
#                     'success': False,
#                     'error': 'No data submitted.',
#                 })
#
#             # ================================================================
#             # COMPARE VALUES
#             # ================================================================
#             changed = {}
#
#             for field, new_val in submitted.items():
#
#                 try:
#                     current = getattr(employee, field, False)
#
#                     # Many2one
#                     if hasattr(current, 'name'):
#                         current_val = current.name or ''
#
#                     # Empty
#                     elif current in [False, None]:
#                         current_val = ''
#
#                     else:
#                         current_val = str(current)
#
#                     # --------------------------------------------------------
#                     # FIX DATE COMPARISON
#                     # --------------------------------------------------------
#                     current_val = str(current_val).strip()
#                     new_val = str(new_val).strip()
#
#                     if current_val != new_val:
#                         changed[field] = new_val
#
#                 except Exception:
#                     changed[field] = new_val
#
#             # ================================================================
#             # FILE CHANGES
#             # ================================================================
#             file_changed_fields = {}
#
#             for field, file_obj in files_submitted.items():
#
#                 try:
#
#                     file_data = base64.b64encode(
#                         file_obj.read()
#                     ).decode('utf-8')
#
#                     file_changed_fields[field] = file_data
#
#                     changed[field] = '[FILE] %s' % file_obj.filename
#
#                 except Exception as e:
#
#                     _logger.error(
#                         'File upload failed for %s : %s',
#                         field,
#                         str(e)
#                     )
#
#             # ================================================================
#             # NO CHANGES
#             # ================================================================
#             if not changed and not file_changed_fields:
#
#                 return request.make_json_response({
#                     'success': True,
#                     'reference': '',
#                     'no_change': True,
#                     'message': (
#                         'No changes detected. '
#                         'Your profile is already up to date.'
#                     )
#                 })
#
#             # ================================================================
#             # SAVE FILES DIRECTLY
#             # ================================================================
#             if file_changed_fields:
#                 employee.sudo().write(file_changed_fields)
#
#             # ================================================================
#             # CREATE PROFILE CHANGE REQUEST
#             # ================================================================
#             reference = ''
#
#             if changed:
#
#                 req = request.env[
#                     'hr.profile.change.request'
#                 ].sudo().create({
#                     'employee_id': employee.id,
#                     'submitted_data': json.dumps(changed),
#                     'state': 'draft',
#                 })
#
#                 # ------------------------------------------------------------
#                 # SUBMIT
#                 # ------------------------------------------------------------
#                 if hasattr(req, 'action_submit'):
#                     req.action_submit()
#
#                 # ------------------------------------------------------------
#                 # FORCE REFERENCE IF EMPTY
#                 # ------------------------------------------------------------
#                 if not req.name or req.name == '/':
#                     sequence = request.env['ir.sequence'].sudo().next_by_code(
#                         'hr.profile.change.request'
#                     )
#
#                     if sequence:
#                         req.sudo().write({
#                             'name': sequence
#                         })
#
#                 reference = req.name or ''
#
#                 # ------------------------------------------------------------
#                 # STORE LAST SUBMISSION
#                 # ------------------------------------------------------------
#                 employee.sudo().write({
#                     'last_portal_submission': json.dumps(changed),
#                     'last_submission_state': 'pending',
#                 })
#
#                 _logger.info(
#                     'PCR CREATED : %s for %s',
#                     reference,
#                     employee.name
#                 )
#
#             # ================================================================
#             # SUCCESS RESPONSE
#             # ================================================================
#             return request.make_json_response({
#                 'success': True,
#                 'reference': reference,
#                 'no_change': False,
#                 'message': (
#                     'Your profile update request '
#                     'has been submitted successfully.'
#                 )
#             })
#
#         # ====================================================================
#         # ERROR
#         # ====================================================================
#         except Exception as e:
#
#             _logger.exception(
#                 'PROFILE UPDATE ERROR : %s',
#                 str(e)
#             )
#
#             return request.make_json_response({
#                 'success': False,
#                 'error': str(e),
#             })






# # -*- coding: utf-8 -*-
# import json
# import logging
# import re
# import base64
#
# from odoo import http
# from odoo.http import request
#
# _logger = logging.getLogger(__name__)
#
# # ── ALL EDITABLE FIELDS ───────────────────────────────────────────────────────
# EDITABLE_FIELDS = [
#
#     # Basic Info
#     'work_phone',
#     'private_email',
#     'private_phone',
#     'private_street',
#     'private_street2',
#     'private_city',
#     'private_zip',
#     'private_state_id',
#     'whatsapp',
#     'linkedin',
#     'legal_name',
#     'facebook_profile',
#     'insta_profile',
#     'twitter_profile',
#
#     # Country Fields
#     'country_id',
#     'nationality_at_birth_id',
#     'issue_countries_id',
#
#     # Personal
#     'blood_group',
#
#     # Identity
#     'issue_date',
#     'expiry_date',
#
#     # Emergency
#     'l10n_in_relationship',
#     'emergency_phone',
#     'e_private_city',
#
#     # Professional
#     'emergency_contact_person_name',
#     'emergency_contact_person_phone',
#     'alternate_mobile_number',
#     'emergency_contact_person_name_1',
#     'emergency_contact_person_phone_1',
#     'second_alternative_number',
#     'home_land_line_no',
#
#     # Spouse
#     'spouse_passport_no',
#     'spouse_passport_issue_date',
#     'spouse_passport_expiry_date',
#     'spouse_visa_no',
#     'spouse_visa_expire_date',
#     'spouse_emirates_id_no',
#     'spouse_emirates_issue_date',
#     'spouse_emirates_id_expiry_date',
#     'spouse_aadhar_no',
#
#     # Child
#     'dependent_child_name_1',
#     'dependent_child_dob_1',
#     'dependent_child_passport_no',
#     'dependent_child_passport_issue_date_1',
#     'dependent_child_passport_expiry_date_1',
#     'dependent_child_visa_no_1',
#     'dependent_child_visa_expiration_date_1',
#     'dependent_child_emirates_id_no_1',
#     'dependent_child_emirates_id_issue_date_1',
#     'dependent_child_emirates_id_expiry_date_1',
#     'dependent_child_aadhar_no_1',
#
#     # Family
#     'father_name',
#     'father_dob',
#     'mother_name',
#     'mother_dob',
#     'children',
#     'career_break_detail',
#
#     # Nominee
#     'employee_nominee_name',
#     'employee_nominee_contact_no',
#     'domain_worked',
#     'primary_skill',
#     'secondary_skill',
#     'tool_used',
#
#     # Industry
#     'industry_ref_name',
#     'industry_ref_email',
#     'industry_ref_mob_no',
#     'home_country_id_name',
#     'home_country_id_number',
#
#     # Languages
#     'mother_tongue_name',
#     'language_known_name',
#
#     # Work Location
#     'u_private_city',
#     'current_address',
#     'phone_code_1',
#     'house_no',
#     'area_name',
#     'city',
#     'zip_code',
#
#     # General
#     'experience',
#     'current_role',
#     'industry_start_date',
#
#     # Last Organization
#     'last_organisation_name',
#     'last_location',
#     'last_salary_per_annum_currency',
#     'last_salary_per_annum_amt',
#     'reason_for_leaving',
#     'last_report_manager_name',
#     'last_report_manager_designation',
#     'last_report_manager_mob_no',
#     'last_report_manager_mail',
#
#     # Industry Details
#     'previous_company_name',
#     'designation',
#     'period_in_company',
#     'reason_of_leaving',
# ]
#
# # ── FILE FIELDS ───────────────────────────────────────────────────────────────
# FILE_FIELDS = [
#     'emirates_id_file',
#     'passport_file',
#     'other_documents',
#     'has_work_permit',
# ]
#
# EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
# ISD_PATTERN = re.compile(r'^\+[1-9][0-9]{0,2}$')
#
#
# class EmployeePortalProfileSubmit(http.Controller):
#
#     @http.route(
#         '/my/employee',
#         type='http',
#         auth='user',
#         website=True,
#         methods=['GET']
#     )
#     def portal_employee_home(self, **kwargs):
#         return request.redirect('/my/employee/personal')
#
#     @http.route(
#         '/my/employee/personal',
#         type='http',
#         auth='user',
#         website=True,
#         methods=['GET', 'POST'],
#         csrf=False,
#     )
#     def portal_employee_personal(self, **post):
#
#         employee = request.env['hr.employee'].sudo().search(
#             [('user_id', '=', request.env.user.id)],
#             limit=1
#         )
#
#         if not employee:
#             return request.redirect('/my')
#
#         if request.httprequest.method == 'POST':
#             return self._handle_post(employee, post)
#
#         portal_overlay = {}
#
#         if (
#             employee.last_portal_submission
#             and employee.last_submission_state in ('pending', 'rejected')
#         ):
#             try:
#                 portal_overlay = json.loads(employee.last_portal_submission)
#             except Exception:
#                 portal_overlay = {}
#
#         countries = request.env['res.country'].sudo().search([], order='name')
#
#         return request.render(
#             'employee_self_service_portal.portal_employee_profile_personal',
#             {
#                 'employee': employee,
#                 'countries': countries,
#                 'all_countries': countries,
#                 'portal_overlay': portal_overlay,
#             },
#         )
#
#     # =========================================================================
#     # HANDLE SAVE
#     # =========================================================================
#     def _handle_post(self, employee, post):
#
#         try:
#
#             # ─────────────────────────────────────────────────────────────
#             # CHECK PENDING
#             # ─────────────────────────────────────────────────────────────
#             pending_request = request.env[
#                 'hr.profile.change.request'
#             ].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'pending'),
#             ], limit=1)
#
#             if pending_request:
#                 return request.make_json_response({
#                     'success': False,
#                     'error': 'Previous request still pending approval.'
#                 })
#
#             # ─────────────────────────────────────────────────────────────
#             # EMAIL VALIDATION
#             # ─────────────────────────────────────────────────────────────
#             for field in [
#                 'private_email',
#                 'industry_ref_email',
#                 'last_report_manager_mail'
#             ]:
#
#                 val = post.get(field, '').strip()
#
#                 if val and not EMAIL_PATTERN.match(val):
#                     return request.make_json_response({
#                         'success': False,
#                         'error': 'Invalid email format.'
#                     })
#
#             # ─────────────────────────────────────────────────────────────
#             # ISD VALIDATION
#             # ─────────────────────────────────────────────────────────────
#             phone_code = post.get('phone_code_1', '').strip()
#
#             if phone_code and not ISD_PATTERN.match(phone_code):
#                 return request.make_json_response({
#                     'success': False,
#                     'error': 'Invalid ISD Code.'
#                 })
#
#             # ─────────────────────────────────────────────────────────────
#             # COLLECT VALUES
#             # ─────────────────────────────────────────────────────────────
#             submitted = {}
#
#             for field in EDITABLE_FIELDS:
#
#                 value = post.get(field)
#
#                 if value is not None:
#                     submitted[field] = str(value).strip()
#
#             # ─────────────────────────────────────────────────────────────
#             # COMPARE VALUES
#             # ─────────────────────────────────────────────────────────────
#             changed = {}
#
#             MANY2ONE_FIELDS = [
#                 'country_id',
#                 'nationality_at_birth_id',
#                 'issue_countries_id',
#                 'private_state_id',
#             ]
#
#             for field, new_val in submitted.items():
#
#                 current = getattr(employee, field, False)
#
#                 # MANY2ONE
#                 if field in MANY2ONE_FIELDS:
#
#                     current_val = str(current.id) if current else ''
#
#                     if str(new_val).strip() != str(current_val).strip():
#                         changed[field] = int(new_val) if new_val else False
#
#                 else:
#
#                     current_val = ''
#
#                     if current not in [False, None]:
#                         current_val = str(current).strip()
#
#                     if str(new_val).strip() != current_val:
#                         changed[field] = new_val
#
#             # ─────────────────────────────────────────────────────────────
#             # FILES
#             # ─────────────────────────────────────────────────────────────
#             file_changed_fields = {}
#
#             for field in FILE_FIELDS:
#
#                 file_obj = request.httprequest.files.get(field)
#
#                 if file_obj and file_obj.filename:
#
#                     file_data = base64.b64encode(
#                         file_obj.read()
#                     ).decode('utf-8')
#
#                     file_changed_fields[field] = file_data
#
#                     changed[field] = '[FILE] %s' % file_obj.filename
#
#             # ─────────────────────────────────────────────────────────────
#             # NO CHANGES
#             # ─────────────────────────────────────────────────────────────
#             if not changed and not file_changed_fields:
#
#                 return request.make_json_response({
#                     'success': True,
#                     'no_change': True,
#                     'reference': '',
#                     'message': 'No changes detected.'
#                 })
#
#             # ─────────────────────────────────────────────────────────────
#             # SAVE FILES
#             # ─────────────────────────────────────────────────────────────
#             if file_changed_fields:
#                 employee.sudo().write(file_changed_fields)
#
#             # ─────────────────────────────────────────────────────────────
#             # CREATE REQUEST
#             # ─────────────────────────────────────────────────────────────
#             req = request.env[
#                 'hr.profile.change.request'
#             ].sudo().create({
#                 'employee_id': employee.id,
#                 'submitted_data': json.dumps(changed),
#                 'state': 'draft',
#             })
#
#             # FORCE SEQUENCE
#             if not req.name or req.name == '/':
#
#                 sequence = request.env[
#                     'ir.sequence'
#                 ].sudo().next_by_code(
#                     'hr.profile.change.request'
#                 )
#
#                 if sequence:
#                     req.sudo().write({
#                         'name': sequence
#                     })
#
#             # SUBMIT
#             if hasattr(req, 'action_submit'):
#                 req.action_submit()
#
#             reference = req.name or ''
#
#             employee.sudo().write({
#                 'last_portal_submission': json.dumps(changed),
#                 'last_submission_state': 'pending',
#             })
#
#             return request.make_json_response({
#                 'success': True,
#                 'reference': reference,
#                 'no_change': False,
#                 'message': 'Profile update submitted successfully.'
#             })
#
#         except Exception as e:
#
#             _logger.exception('PROFILE UPDATE ERROR')
#
#             return request.make_json_response({
#                 'success': False,
#                 'error': str(e)
#             })







# # -*- coding: utf-8 -*-
# import json
# import logging
# import re
# from odoo import http
# from odoo.http import request
#
# _logger = logging.getLogger(__name__)
#
# # ── ALL editable fields including ALL tabs ────────────────────────────────────
# EDITABLE_FIELDS = [
#     # Basic Info — Contact
#     'work_phone', 'private_email', 'private_phone',
#     'private_street', 'private_street2', 'private_city', 'private_zip',
#     'private_state_id',
#     'whatsapp', 'linkedin', 'legal_name',
#     'facebook_profile', 'insta_profile', 'twitter_profile',
#
#     # Basic Info — Personal
#     'blood_group',
#
#     # Basic Info — Identity (editable ones)
#     'issue_date', 'expiry_date',
#
#     # Basic Info — Emergency
#     'l10n_in_relationship', 'emergency_phone', 'e_private_city',
#
#     # Professional — Emergency Contact
#     'emergency_contact_person_name', 'emergency_contact_person_phone',
#     'alternate_mobile_number', 'emergency_contact_person_name_1',
#     'emergency_contact_person_phone_1', 'second_alternative_number',
#     'home_land_line_no',
#
#     # Professional — Spouse
#     'spouse_passport_no', 'spouse_passport_issue_date',
#     'spouse_passport_expiry_date', 'spouse_visa_no',
#     'spouse_visa_expire_date', 'spouse_emirates_id_no',
#     'spouse_emirates_issue_date', 'spouse_emirates_id_expiry_date',
#     'spouse_aadhar_no',
#
#     # Family — Child
#     'dependent_child_name_1', 'dependent_child_dob_1',
#     'dependent_child_passport_no',
#     'dependent_child_passport_issue_date_1',
#     'dependent_child_passport_expiry_date_1',
#     'dependent_child_visa_no_1',
#     'dependent_child_visa_expiration_date_1',
#     'dependent_child_emirates_id_no_1',
#     'dependent_child_emirates_id_issue_date_1',
#     'dependent_child_emirates_id_expiry_date_1',
#     'dependent_child_aadhar_no_1',
#
#     # Family
#     'father_name', 'father_dob',
#     'mother_name', 'mother_dob',
#     'children', 'career_break_detail',
#
#     # Professional — Nominee
#     'employee_nominee_name', 'employee_nominee_contact_no',
#     'domain_worked', 'primary_skill', 'secondary_skill', 'tool_used',
#
#     # Professional — Industry
#     'industry_ref_name', 'industry_ref_email', 'industry_ref_mob_no',
#     'home_country_id_name', 'home_country_id_number',
#
#     # Family — Languages
#     'mother_tongue_name', 'language_known_name',
#
#     # Professional — Work Location
#     'u_private_city', 'current_address', 'phone_code_1',
#     'house_no', 'area_name', 'city', 'zip_code',
#
#     # Professional — General
#     'experience', 'current_role', 'industry_start_date',
#
#     # Professional — Last Organisation
#     'last_organisation_name', 'last_location',
#     'last_salary_per_annum_currency', 'last_salary_per_annum_amt',
#     'reason_for_leaving', 'last_report_manager_name',
#     'last_report_manager_designation', 'last_report_manager_mob_no',
#     'last_report_manager_mail',
#
#     # Professional — Career
#     'career_break_detail',
#
#     # Professional — Industry Details
#     'previous_company_name', 'designation', 'period_in_company',
#     'reason_of_leaving',
# ]
#
# # File upload fields — handled separately
# FILE_FIELDS = [
#     'emirates_id_file',
#     'passport_file',
#     'other_documents',
#     'has_work_permit',
# ]
#
# EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
#
#
# class EmployeePortalProfileSubmit(http.Controller):
#
#     @http.route('/my/employee', type='http', auth='user', website=True, methods=['GET'])
#     def portal_employee_home(self, **kwargs):
#         return request.redirect('/my/employee/personal')
#
#     @http.route(
#         '/my/employee/personal',
#         type='http', auth='user', website=True,
#         methods=['GET', 'POST'], csrf=False,
#     )
#     def portal_employee_personal(self, **post):
#         employee = request.env['hr.employee'].sudo().search(
#             [('user_id', '=', request.env.user.id)], limit=1
#         )
#         if not employee:
#             return request.redirect('/my')
#
#         if request.httprequest.method == 'POST':
#             return self._handle_post(employee, post)
#
#         # portal_overlay: only for pending/rejected
#         portal_overlay = {}
#         if (employee.last_portal_submission
#                 and employee.last_submission_state in ('pending', 'rejected')):
#             try:
#                 portal_overlay = json.loads(employee.last_portal_submission)
#             except Exception:
#                 portal_overlay = {}
#
#         notification = None
#         state = employee.last_submission_state
#
#         if state == 'approved':
#             approved_req = request.env['hr.profile.change.request'].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'approved'),
#             ], order='review_date desc', limit=1)
#             notification = {
#                 'type':         'success',
#                 'message':      'Your profile has been updated by HR successfully.',
#                 'reason':       False,
#                 'request_name': approved_req.name if approved_req else '',
#             }
#         elif state == 'rejected':
#             rejected_req = request.env['hr.profile.change.request'].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'rejected'),
#             ], order='create_date desc', limit=1)
#             if rejected_req:
#                 notification = {
#                     'type':         'danger',
#                     'message':      'Your profile update request was rejected by HR.',
#                     'reason':       rejected_req.rejection_reason or 'No reason provided.',
#                     'request_name': rejected_req.name,
#                 }
#         elif state == 'pending':
#             pending_req = request.env['hr.profile.change.request'].sudo().search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'pending'),
#             ], order='create_date desc', limit=1)
#             if pending_req:
#                 notification = {
#                     'type':         'warning',
#                     'message':      'Your profile change request is awaiting HR review.',
#                     'reason':       False,
#                     'request_name': pending_req.name,
#                 }
#
#         countries = request.env['res.country'].sudo().search([], order='name')
#
#         return request.render(
#             'employee_self_service_portal.portal_employee_profile_personal',
#             {
#                 'employee':       employee,
#                 'countries':      countries,
#                 'notification':   notification,
#                 'portal_overlay': portal_overlay,
#             },
#         )
#
#     def _handle_post(self, employee, post):
#         try:
#             # ── Validate email fields ─────────────────────────────
#             for field in ['private_email', 'industry_ref_email', 'last_report_manager_mail']:
#                 val = post.get(field, '').strip()
#                 if val and not EMAIL_PATTERN.match(val):
#                     return request.make_json_response({
#                         'success': False,
#                         'error': f'Invalid email format: {field}'
#                     })
#
#             # ── Collect text/select fields ────────────────────────
#             submitted = {}
#             for field in EDITABLE_FIELDS:
#                 val = post.get(field)
#                 if val is not None and str(val).strip():
#                     submitted[field] = str(val).strip()
#
#             # ── Collect uploaded file fields ──────────────────────
#             # Issue 20 fix: check request.httprequest.files for actual uploads
#             files_submitted = {}
#             for field in FILE_FIELDS:
#                 file_obj = request.httprequest.files.get(field)
#                 if file_obj and file_obj.filename:
#                     files_submitted[field] = file_obj
#
#             if not submitted and not files_submitted:
#                 return request.make_json_response({
#                     'success': False,
#                     'error': 'No data was submitted.'
#                 })
#
#             # ── Compare text fields against current values ────────
#             # Issue 21 fix: include blood_group, issue_date, expiry_date
#             changed = {}
#             for field, new_val in submitted.items():
#                 try:
#                     current = getattr(employee, field, None)
#                     if hasattr(current, 'name'):
#                         current_str = str(current.name) if current else ''
#                     elif current is False or current is None:
#                         current_str = ''
#                     else:
#                         current_str = str(current)
#                     if new_val.strip() != current_str.strip():
#                         changed[field] = new_val
#                 except Exception:
#                     changed[field] = new_val
#
#             # ── Write uploaded files directly to employee record ──
#             # Issue 20 fix: files are written immediately on submission
#             # They are stored as binary on the employee record
#             file_changed_fields = {}
#             for field, file_obj in files_submitted.items():
#                 try:
#                     import base64
#                     file_data = base64.b64encode(file_obj.read()).decode('utf-8')
#                     file_changed_fields[field] = file_data
#                     # Mark in submitted_data that a file was uploaded
#                     changed[field] = f'[FILE:{file_obj.filename}]'
#                 except Exception as e:
#                     _logger.warning('Failed to read uploaded file %s: %s', field, e)
#
#             if not changed and not file_changed_fields:
#                 return request.make_json_response({
#                     'success': True, 'reference': '',
#                     'message': 'No changes detected. Nothing was saved.',
#                     'no_change': True,
#                 })
#
#             # ── Write files directly to employee ──────────────────
#             if file_changed_fields:
#                 employee.sudo().write(file_changed_fields)
#
#             # ── Create PCR for text field changes ─────────────────
#             # Include file upload markers in submitted_data
#             if changed:
#                 req = request.env['hr.profile.change.request'].sudo().create({
#                     'employee_id':    employee.id,
#                     'submitted_data': json.dumps(changed),
#                     'state':          'draft',
#                 })
#                 req.action_submit()
#                 ref = req.name
#                 _logger.info(
#                     'PCR %s created for %s — %d field(s), %d file(s)',
#                     ref, employee.name, len(changed), len(file_changed_fields)
#                 )
#             else:
#                 # Only files were uploaded, no text changes
#                 ref = ''
#
#             return request.make_json_response({
#                 'success':   True,
#                 'reference': ref,
#                 'message':   (
#                     'Your changes have been submitted. HR will review and notify you.'
#                     if ref else
#                     'Your documents have been uploaded successfully.'
#                 ),
#             })
#
#         except Exception as e:
#             _logger.error(
#                 'Error processing profile change for %s: %s',
#                 employee.name, str(e)
#             )
#             return request.make_json_response({'success': False, 'error': str(e)})
#
#
#
