# -*- coding: utf-8 -*-
"""
controllers/portal_employee_profile.py
=======================================
Handles all portal employee profile tab form submissions.
Bidirectional sync:
  - Portal → Employee: POST writes directly to hr.employee via sudo()
  - Employee → Portal: Templates read from employee record on every page load
"""

from odoo import http, fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# FIELD MAPS per tab:  { form_field_name: (odoo_field_name, portal_editable) }
# portal_editable=True  → employee can update from portal
# portal_editable=False → read-only on portal (HR manages in backend only)
# ─────────────────────────────────────────────────────────────────────────────

PERSONAL_FIELDS = {
    # Basic Info
    'employee_first_name':          ('employee_first_name',          True),
    'employee_middle_name':         ('employee_middle_name',          True),
    'employee_last_name':           ('employee_last_name',            True),
    'employee_name_english':        ('employee_name_english',         False),
    'employee_name_arabic':         ('employee_name_arabic',          True),
    'emp_code':                     ('emp_code',                      False),
    'work_email':                   ('work_email',                    False),
    'work_phone':                   ('work_phone',                    False),
    'x_nationality':                ('x_nationality',                 False),
    'nationality_at_birth_id':      ('nationality_at_birth_id',       False),
    'sex':                          ('sex',                           False),
    'birthday':                     ('birthday',                      True),
    'place_of_birth':               ('place_of_birth',                True),
    'marital':                      ('marital',                       False),
    'children':                     ('children',                      False),
    'disabled':                     ('disabled',                      False),
    'legal_name':                   ('legal_name',                    False),
    'blooad_group':                 ('blooad_group',                  True),
    'religion':                     ('religion',                      True),
    'mother_tongue_id':             ('mother_tongue_id',              False),
    'lang':                         ('lang',                          False),
    # Identity
    'x_emirates_id':                ('x_emirates_id',                 True),
    'x_emirates_expiry':            ('x_emirates_expiry',             True),
    'emirates_id_number':           ('emirates_id_number',            True),
    'emirates_issue_date':          ('emirates_issue_date',           True),
    'emirates_expiry_date':         ('emirates_expiry_date',          True),
    'x_passport_number':            ('x_passport_number',             True),
    'x_passport_country':           ('x_passport_country',            True),
    'x_passport_issue':             ('x_passport_issue',              True),
    'x_passport_expiry':            ('x_passport_expiry',             True),
    'issue_date':                   ('issue_date',                    True),
    'issue_countries_id':           ('issue_countries_id',            False),
    'entry_exit_date':              ('entry_exit_date',               False),
    'visa_no':                      ('visa_no',                       False),
    'visa_sponser':                 ('visa_sponser',                  False),
    'visa_issue_date':              ('visa_issue_date',               False),
    'permit_no':                    ('permit_no',                     False),
    'has_work_permit':              ('has_work_permit',               False),
    'home_country_id_name':         ('home_country_id_name',          False),
    'home_country_id_number':       ('home_country_id_number',        False),
    'aadhar_no':                    ('aadhar_no',                     True),
    'pan':                          ('pan',                           True),
    'uan':                          ('uan',                           False),
    'pf_number':                    ('pf_number',                     False),
    # Contact
    'private_email':                ('private_email',                 True),
    'private_phone':                ('private_phone',                 True),
    'country_code_for_personal_mob_no': ('country_code_for_personal_mob_no', True),
    'whatsapp':                     ('whatsapp',                      True),
    'home_land_line_no':            ('home_land_line_no',             True),
    'private_street':               ('private_street',                True),
    'private_street2':              ('private_street2',               True),
    'private_city':                 ('private_city',                  True),
    'private_zip':                  ('private_zip',                   True),
    'country_residences':           ('country_residences',            False),
    'distance_home_work':           ('distance_home_work',            False),
    'e_private_street':             ('e_private_street',              True),
    'u_private_street':             ('u_private_street',              True),
    'house_no':                     ('house_no',                      True),
    'area_name':                    ('area_name',                     True),
    'city':                         ('city',                          False),
    'zip_code':                     ('zip_code',                      True),
    'linkedin':                     ('linkedin',                      True),
    'facebook_profile':             ('facebook_profile',              True),
    'insta_profile':                ('insta_profile',                 True),
    'twitter_profile':              ('twitter_profile',               True),
    # Emergency
    'emergency_contact':            ('emergency_contact',             True),
    'emergency_phone':              ('emergency_phone',               True),
    'emergency_contact_person_name':  ('emergency_contact_person_name',  True),
    'emergency_contact_person_phone': ('emergency_contact_person_phone', True),
    'emergency_contact_person_name_1':  ('emergency_contact_person_name_1',  True),
    'emergency_contact_person_phone_1': ('emergency_contact_person_phone_1', True),
    # Family
    'father_name':                  ('father_name',                   False),
    'father_dob':                   ('father_dob',                    False),
    'dependent_status':             ('dependent_status',              False),
    'mother_name':                  ('mother_name',                   False),
    'mother_dob':                   ('mother_dob',                    False),
    'dependent_status_1':           ('dependent_status_1',            False),
    'spouse_support_no':            ('spouse_support_no',             True),
    'spouse_passport_issue_date':   ('spouse_passport_issue_date',    True),
    'spouse_passport_expiry_date':  ('spouse_passport_expiry_date',   True),
    'spouse_visa_no':               ('spouse_visa_no',                True),
    'spouse_visa_expire_date':      ('spouse_visa_expire_date',       True),
    'spouse_emirates_id_no':        ('spouse_emirates_id_no',         True),
    'spouse_emirates_issue_date':   ('spouse_emirates_issue_date',    True),
    'spouse_emirates_id_expiry_date': ('spouse_emirates_id_expiry_date', True),
    'spouse_aadhar_no':             ('spouse_aadhar_no',              True),
    'dependent_child_name_1':       ('dependent_child_name_1',        True),
    'dependent_child_dob_1':        ('dependent_child_dob_1',         True),
    'dependent_child_passport_no':  ('dependent_child_passport_no',   True),
    'dependent_child_passport_issue_date_1':  ('dependent_child_passport_issue_date_1',  True),
    'dependent_child_passport_expiry_date_1': ('dependent_child_passport_expiry_date_1', True),
    'dependent_child_visa_no_1':    ('dependent_child_visa_no_1',     True),
    'dependent_child_visa_expiration_date_1': ('dependent_child_visa_expiration_date_1', True),
    'dependent_child_emirates_id_no_1':       ('dependent_child_emirates_id_no_1',       True),
    'dependent_child_emirates_id_issue_date_1': ('dependent_child_emirates_id_issue_date_1', True),
    'dependent_child_emirates_id_expiry_date_1': ('dependent_child_emirates_id_expiry_date_1', True),
    'dependent_child_aadhar_no_1':  ('dependent_child_aadhar_no_1',   True),
    # Nominee / Skills
    'employee_nominee_name':        ('employee_nominee_name',         True),
    'employee_nominee_contact_no':  ('employee_nominee_contact_no',   True),
    'domain_worked':                ('domain_worked',                 False),
    'primary_skill':                ('primary_skill',                 False),
    'secondary_skill':              ('secondary_skill',               False),
    'tool_used':                    ('tool_used',                     False),
    'names':                        ('names',                         False),
}

TECHCARROT_FIELDS = {
    'practice':                     ('practice',                      False),
    'sub_practice':                 ('sub_practice',                  False),
    'engagement_location':          ('engagement_location',           False),
    'emp_inside_uae':               ('emp_inside_uae',                False),
    'branch_name':                  ('branch_name',                   False),
    'bank_name':                    ('bank_name',                     False),
    'payroll':                      ('payroll',                       False),
    'doj':                          ('doj',                           False),
    'original_hire_date':           ('original_hire_date',            False),
    'current_address':              ('current_address',               False),
    'phone_code_1':                 ('phone_code_1',                  False),
    'notice_period':                ('notice_period',                 False),
    'resign_date':                  ('resign_date',                   False),
    'end_date':                     ('end_date',                      False),
    'lwd':                          ('lwd',                           False),
    'customer_acc_name':            ('customer_acc_name',             False),
    'candidate_source':             ('candidate_source',              False),
    'current_role':                 ('current_role',                  False),
    'industry_start_date':          ('industry_start_date',           False),
    'experience':                   ('experience',                    False),
    'no_of_carrer_break':           ('no_of_carrer_break',            False),
    'career_break':                 ('career_break',                  False),
    'career_break_detail':          ('career_break_detail',           False),
    'career_break_start_date':      ('career_break_start_date',       False),
    'career_break_end_date':        ('career_break_end_date',         False),
    'last_report_manager_mob_no':   ('last_report_manager_mob_no',    False),
    'industry_ref_name':            ('industry_ref_name',             False),
    'industry_ref_email':           ('industry_ref_email',            False),
    'industry_ref_mob_no':          ('industry_ref_mob_no',           False),
    'previous_company_name':        ('previous_company_name',         False),
    'designation':                  ('designation',                   False),
    'period_in_company':            ('period_in_company',             False),
    'reason_of_leaving':            ('reason_of_leaving',             False),
    'certificate':                  ('certificate',                   False),
    'study_field':                  ('study_field',                   False),
    'institute_name':               ('institute_name',                False),
    'degree_name':                  ('degree_name',                   False),
    'field_of_study':               ('field_of_study',                False),
    'start_date_of_degree':         ('start_date_of_degree',          False),
    'completion_date_of_degree':    ('completion_date_of_degree',     False),
    'year_of_passing':              ('year_of_passing',               False),
    'score':                        ('score',                         False),
    'degree_certificate_legal':     ('degree_certificate_legal',      False),
    'certification_obtained':       ('certification_obtained',        False),
}

# Date fields — need string → date conversion
DATE_FIELDS = {
    'birthday', 'x_emirates_expiry', 'emirates_issue_date', 'emirates_expiry_date',
    'x_passport_issue', 'x_passport_expiry', 'issue_date', 'entry_exit_date',
    'visa_issue_date', 'father_dob', 'mother_dob',
    'spouse_passport_issue_date', 'spouse_passport_expiry_date',
    'spouse_visa_expire_date', 'spouse_emirates_issue_date',
    'spouse_emirates_id_expiry_date', 'dependent_child_dob_1',
    'dependent_child_passport_issue_date_1', 'dependent_child_passport_expiry_date_1',
    'dependent_child_visa_expiration_date_1', 'dependent_child_emirates_id_issue_date_1',
    'dependent_child_emirates_id_expiry_date_1', 'doj', 'original_hire_date',
    'resign_date', 'end_date', 'lwd', 'industry_start_date',
    'start_date_of_degree', 'completion_date_of_degree',
    'career_break_start_date', 'career_break_end_date',
}

BOOL_FIELDS = {'disabled', 'emp_inside_uae'}
INT_FIELDS  = {'children', 'notice_period', 'no_of_carrer_break'}


def _get_employee():
    """Return the hr.employee record for the currently logged-in portal user."""
    return request.env['hr.employee'].sudo().search(
        [('user_id', '=', request.env.user.id)], limit=1
    )


def _build_write_vals(post_data, field_map):
    """
    Build a dict of {odoo_field: value} from POST data,
    only including fields marked as portal_editable=True.
    """
    write_vals = {}
    for form_name, (odoo_field, editable) in field_map.items():
        if not editable:
            continue
        raw = post_data.get(form_name)
        if raw is None:
            continue
        if form_name in DATE_FIELDS:
            value = fields.Date.from_string(raw) if raw else False
        elif form_name in BOOL_FIELDS:
            value = raw in ('1', 'true', 'True', True)
        elif form_name in INT_FIELDS:
            try:
                value = int(raw) if raw else 0
            except ValueError:
                value = 0
        else:
            value = raw.strip() if raw else False
        write_vals[odoo_field] = value
    return write_vals


def _json_response(success, error=None):
    import json
    body = json.dumps({'success': success, 'error': error} if error else {'success': success})
    return request.make_response(body, headers=[('Content-Type', 'application/json')])


class PortalEmployeeProfile(http.Controller):

    # ── PERSONAL DETAILS TAB ──────────────────────────────────────────────────
    @http.route('/my/employee/personal', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def personal(self, **kwargs):
        employee = _get_employee()
        if not employee:
            return _json_response(False, 'No employee record found for this user.')

        if request.httprequest.method == 'POST':
            write_vals = _build_write_vals(kwargs, PERSONAL_FIELDS)
            if not write_vals:
                return _json_response(False, 'No editable fields submitted.')
            try:
                employee.write(write_vals)
                _logger.info('Portal personal update: employee=%s fields=%s', employee.name, list(write_vals))
                return _json_response(True)
            except Exception as e:
                _logger.error('Portal personal update error employee=%s: %s', employee.name, e)
                return _json_response(False, str(e))

        return request.render(
            'employee_self_service_portal.portal_employee_profile_personal',
            {'employee': employee}
        )

    # ── TECHCARROT TAB ────────────────────────────────────────────────────────
    @http.route('/my/employee/techcarrot', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def techcarrot(self, **kwargs):
        employee = _get_employee()
        if not employee:
            return _json_response(False, 'No employee record found for this user.')

        if request.httprequest.method == 'POST':
            write_vals = _build_write_vals(kwargs, TECHCARROT_FIELDS)
            if not write_vals:
                return _json_response(False, 'No editable fields submitted.')
            try:
                employee.write(write_vals)
                _logger.info('Portal techcarrot update: employee=%s fields=%s', employee.name, list(write_vals))
                return _json_response(True)
            except Exception as e:
                _logger.error('Portal techcarrot update error employee=%s: %s', employee.name, e)
                return _json_response(False, str(e))

        return request.render(
            'employee_self_service_portal.portal_employee_profile_techcarrot',
            {'employee': employee}
        )

    # ── EXPERIENCE TAB ────────────────────────────────────────────────────────
    @http.route('/my/employee/experience', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def experience(self, **kwargs):
        employee = _get_employee()
        if not employee:
            return _json_response(False, 'No employee record found for this user.')

        if request.httprequest.method == 'POST':
            # Experience tab fields — add your experience fields here
            EXPERIENCE_FIELDS = {
                'primary_skill':   ('primary_skill',   True),
                'secondary_skill': ('secondary_skill', True),
                'domain_worked':   ('domain_worked',   True),
                'tool_used':       ('tool_used',        True),
                'names':           ('names',            True),
            }
            write_vals = _build_write_vals(kwargs, EXPERIENCE_FIELDS)
            try:
                if write_vals:
                    employee.write(write_vals)
                return _json_response(True)
            except Exception as e:
                return _json_response(False, str(e))

        return request.render(
            'employee_self_service_portal.portal_employee_profile_experience',
            {'employee': employee}
        )

    # ── CERTIFICATION TAB ─────────────────────────────────────────────────────
    @http.route('/my/employee/certification', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def certification(self, **kwargs):
        employee = _get_employee()
        if not employee:
            return _json_response(False, 'No employee record found for this user.')

        if request.httprequest.method == 'POST':
            CERTIFICATION_FIELDS = {
                'certificate':              ('certificate',              False),
                'study_field':              ('study_field',              False),
                'institute_name':           ('institute_name',           False),
                'degree_name':              ('degree_name',              False),
                'field_of_study':           ('field_of_study',           False),
                'start_date_of_degree':     ('start_date_of_degree',     False),
                'completion_date_of_degree': ('completion_date_of_degree', False),
                'year_of_passing':          ('year_of_passing',           False),
                'score':                    ('score',                    False),
                'certification_obtained':   ('certification_obtained',   False),
                'degree_certificate_legal': ('degree_certificate_legal', False),
            }
            write_vals = _build_write_vals(kwargs, CERTIFICATION_FIELDS)
            try:
                if write_vals:
                    employee.write(write_vals)
                return _json_response(True)
            except Exception as e:
                return _json_response(False, str(e))

        return request.render(
            'employee_self_service_portal.portal_employee_profile_certification',
            {'employee': employee}
        )

    # ── BANK DETAILS TAB ──────────────────────────────────────────────────────
    @http.route('/my/employee/bank', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def bank(self, **kwargs):
        employee = _get_employee()
        if not employee:
            return _json_response(False, 'No employee record found for this user.')

        if request.httprequest.method == 'POST':
            # Bank details are on res.partner.bank — handle separately
            # For now just return success; implement bank account creation below
            try:
                bank_name = kwargs.get('bank_name', '').strip()
                acc_number = kwargs.get('acc_number', '').strip()
                ifsc = kwargs.get('ifsc_code', '').strip()

                if acc_number and bank_name:
                    existing = request.env['res.partner.bank'].sudo().search([
                        ('partner_id', '=', employee.address_home_id.id),
                        ('acc_number', '=', acc_number),
                    ], limit=1)
                    if not existing:
                        request.env['res.partner.bank'].sudo().create({
                            'partner_id': employee.address_home_id.id or employee.user_id.partner_id.id,
                            'acc_number': acc_number,
                            'bank_name': bank_name,
                            'ifsc_code': ifsc,
                        })
                return _json_response(True)
            except Exception as e:
                return _json_response(False, str(e))

        bank_accounts = request.env['res.partner.bank'].sudo().search([
            ('partner_id', '=', employee.address_home_id.id or employee.user_id.partner_id.id)
        ])
        return request.render(
            'employee_self_service_portal.portal_employee_profile_bank',
            {'employee': employee, 'bank_accounts': bank_accounts}
        )