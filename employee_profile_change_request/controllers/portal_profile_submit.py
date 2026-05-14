
# -*- coding: utf-8 -*-
import json
import logging
import re
import base64

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Many2one fields — submitted as integer IDs from country dropdowns ─────────
# These are stored as integer IDs in submitted_data.
# action_approve writes int(v) for these.
MANY2ONE_FIELDS = {
    'nationality_at_birth_id',    # Nationality At Birth
    'country_id',                 # Nationality
    'issue_countries_id',         # Passport Issuing Country
    'countries_id',               # Country (Work Location)
    'father_nationalities_id',    # Father Nationality  ← NEW
    'mother_nationalities_id',    # Mother Nationality  ← NEW
}

# ── ALL editable text/select fields ───────────────────────────────────────────
EDITABLE_FIELDS = [
    # Basic Info — Contact
    'work_phone', 'private_email', 'private_phone',
    'private_street', 'private_street2', 'private_city', 'private_zip',
    'private_state_id',
    'whatsapp', 'linkedin', 'legal_name',
    'facebook_profile', 'insta_profile', 'twitter_profile',

    # Basic Info — Personal
    'blood_group',

    # Basic Info — Identity
    'issue_date', 'expiry_date',
    'emirates_id_number', 'emirates_expiry_date',
    'passport_id', 'identification_id', 'ssnid', 'visa_no', 'permit_no',

    # Basic Info — Country dropdowns (Many2one — sent as int IDs)
    'nationality_at_birth_id',
    'country_id',
    'issue_countries_id',
    'countries_id',

    # Basic Info — Emergency
    'l10n_in_relationship', 'emergency_phone', 'e_private_city',

    # Country Code — now a dropdown in portal
    'phone_code_1',

    # Professional — Emergency Contact
    'emergency_contact_person_name', 'emergency_contact_person_phone',
    'alternate_mobile_number', 'emergency_contact_person_name_1',
    'emergency_contact_person_phone_1', 'second_alternative_number',
    'home_land_line_no',

    # Professional — Spouse
    'spouse_passport_no', 'spouse_passport_issue_date',
    'spouse_passport_expiry_date', 'spouse_visa_no',
    'spouse_visa_expire_date', 'spouse_emirates_id_no',
    'spouse_emirates_issue_date', 'spouse_emirates_id_expiry_date',
    'spouse_aadhar_no',

    # Family — Child
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

    # Family — Father / Mother (text fields)
    'father_name', 'father_dob',
    'mother_name', 'mother_dob',

    # Family — Father / Mother Nationality (Many2one dropdowns) ← NEW
    'father_nationalities_id',
    'mother_nationalities_id',

    'children', 'career_break_detail',
    'marital',

    # Professional — Nominee
    'employee_nominee_name', 'employee_nominee_contact_no',
    'domain_worked', 'primary_skill', 'secondary_skill', 'tool_used',

    # Professional — Industry
    'industry_ref_name', 'industry_ref_email', 'industry_ref_mob_no',
    'home_country_id_name', 'home_country_id_number',

    # Family — Languages
    'mother_tongue_name', 'language_known_name',

    # Professional — Work Location
    'u_private_city', 'current_address',
    'house_no', 'area_name', 'city', 'zip_code',

    # Professional — General
    'experience', 'current_role', 'industry_start_date',

    # Professional — Last Organisation
    'last_organisation_name', 'last_location',
    'last_salary_per_annum_currency', 'last_salary_per_annum_amt',
    'reason_for_leaving', 'last_report_manager_name',
    'last_report_manager_designation', 'last_report_manager_mob_no',
    'last_report_manager_mail',

    # Professional — Industry Details
    'previous_company_name', 'designation', 'period_in_company',
    'reason_of_leaving',
]

# File upload fields
FILE_FIELDS = [
    'emirates_id_file',
    'passport_file',
    'other_documents',
    'has_work_permit',
]

EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
ISD_PATTERN   = re.compile(r'^\+[1-9][0-9]{0,2}$')

# ISD codes list for dropdown
ISD_CODES = [
    ('+1',   'USA / Canada (+1)'),
    ('+7',   'Russia (+7)'),
    ('+20',  'Egypt (+20)'),
    ('+27',  'South Africa (+27)'),
    ('+30',  'Greece (+30)'),
    ('+31',  'Netherlands (+31)'),
    ('+32',  'Belgium (+32)'),
    ('+33',  'France (+33)'),
    ('+34',  'Spain (+34)'),
    ('+36',  'Hungary (+36)'),
    ('+39',  'Italy (+39)'),
    ('+40',  'Romania (+40)'),
    ('+41',  'Switzerland (+41)'),
    ('+43',  'Austria (+43)'),
    ('+44',  'UK (+44)'),
    ('+45',  'Denmark (+45)'),
    ('+46',  'Sweden (+46)'),
    ('+47',  'Norway (+47)'),
    ('+48',  'Poland (+48)'),
    ('+49',  'Germany (+49)'),
    ('+51',  'Peru (+51)'),
    ('+52',  'Mexico (+52)'),
    ('+54',  'Argentina (+54)'),
    ('+55',  'Brazil (+55)'),
    ('+56',  'Chile (+56)'),
    ('+57',  'Colombia (+57)'),
    ('+58',  'Venezuela (+58)'),
    ('+60',  'Malaysia (+60)'),
    ('+61',  'Australia (+61)'),
    ('+62',  'Indonesia (+62)'),
    ('+63',  'Philippines (+63)'),
    ('+64',  'New Zealand (+64)'),
    ('+65',  'Singapore (+65)'),
    ('+66',  'Thailand (+66)'),
    ('+81',  'Japan (+81)'),
    ('+82',  'South Korea (+82)'),
    ('+84',  'Vietnam (+84)'),
    ('+86',  'China (+86)'),
    ('+90',  'Turkey (+90)'),
    ('+91',  'India (+91)'),
    ('+92',  'Pakistan (+92)'),
    ('+93',  'Afghanistan (+93)'),
    ('+94',  'Sri Lanka (+94)'),
    ('+95',  'Myanmar (+95)'),
    ('+98',  'Iran (+98)'),
    ('+212', 'Morocco (+212)'),
    ('+213', 'Algeria (+213)'),
    ('+216', 'Tunisia (+216)'),
    ('+218', 'Libya (+218)'),
    ('+220', 'Gambia (+220)'),
    ('+221', 'Senegal (+221)'),
    ('+234', 'Nigeria (+234)'),
    ('+249', 'Sudan (+249)'),
    ('+254', 'Kenya (+254)'),
    ('+256', 'Uganda (+256)'),
    ('+255', 'Tanzania (+255)'),
    ('+260', 'Zambia (+260)'),
    ('+263', 'Zimbabwe (+263)'),
    ('+966', 'Saudi Arabia (+966)'),
    ('+967', 'Yemen (+967)'),
    ('+968', 'Oman (+968)'),
    ('+970', 'Palestine (+970)'),
    ('+971', 'UAE (+971)'),
    ('+972', 'Israel (+972)'),
    ('+973', 'Bahrain (+973)'),
    ('+974', 'Qatar (+974)'),
    ('+975', 'Bhutan (+975)'),
    ('+976', 'Mongolia (+976)'),
    ('+977', 'Nepal (+977)'),
    ('+994', 'Azerbaijan (+994)'),
    ('+995', 'Georgia (+995)'),
    ('+996', 'Kyrgyzstan (+996)'),
    ('+998', 'Uzbekistan (+998)'),
]


class EmployeePortalProfileSubmit(http.Controller):

    @http.route('/my/employee', type='http', auth='user', website=True, methods=['GET'])
    def portal_employee_home(self, **kwargs):
        return request.redirect('/my/employee/personal')

    @http.route(
        '/my/employee/personal',
        type='http', auth='user', website=True,
        methods=['GET', 'POST'], csrf=False,
    )
    def portal_employee_personal(self, **post):
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not employee:
            return request.redirect('/my')

        if request.httprequest.method == 'POST':
            return self._handle_post(employee, post)

        # portal_overlay: only for pending/rejected
        portal_overlay = {}
        if (employee.last_portal_submission
                and employee.last_submission_state in ('pending', 'rejected')):
            try:
                portal_overlay = json.loads(employee.last_portal_submission)
            except Exception:
                portal_overlay = {}

        notification = None
        state = employee.last_submission_state

        if state == 'approved':
            approved_req = request.env['hr.profile.change.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'approved'),
            ], order='review_date desc', limit=1)
            notification = {
                'type':         'success',
                'message':      'Your profile has been updated by HR successfully.',
                'reason':       False,
                'request_name': approved_req.name if approved_req else '',
            }
        elif state == 'rejected':
            rejected_req = request.env['hr.profile.change.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'rejected'),
            ], order='create_date desc', limit=1)
            if rejected_req:
                notification = {
                    'type':         'danger',
                    'message':      'Your profile update request was rejected by HR.',
                    'reason':       rejected_req.rejection_reason or 'No reason provided.',
                    'request_name': rejected_req.name,
                }
        elif state == 'pending':
            pending_req = request.env['hr.profile.change.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
            ], order='create_date desc', limit=1)
            if pending_req:
                notification = {
                    'type':         'warning',
                    'message':      'Your profile change request is awaiting HR review.',
                    'reason':       False,
                    'request_name': pending_req.name,
                }

        countries = request.env['res.country'].sudo().search([], order='name')

        return request.render(
            'employee_self_service_portal.portal_employee_profile_personal',
            {
                'employee':       employee,
                'countries':      countries,
                'all_countries':  countries,
                'isd_codes':      ISD_CODES,
                'notification':   notification,
                'portal_overlay': portal_overlay,
            },
        )

    def _handle_post(self, employee, post):
        try:
            # ── Block if pending ──────────────────────────────────
            pending_req = request.env['hr.profile.change.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
            ], limit=1)
            if pending_req:
                return request.make_json_response({
                    'success': False,
                    'error': 'Your previous request is still pending HR approval.',
                })

            # ── Email validation ──────────────────────────────────
            for field in ['private_email', 'industry_ref_email', 'last_report_manager_mail']:
                val = post.get(field, '').strip()
                if val and not EMAIL_PATTERN.match(val):
                    return request.make_json_response({
                        'success': False,
                        'error': f'Invalid email format: {field}'
                    })

            # ── ISD validation (now a dropdown — value is e.g. "+91") ─
            isd_val = post.get('phone_code_1', '').strip()
            if isd_val and not ISD_PATTERN.match(isd_val):
                return request.make_json_response({
                    'success': False,
                    'error': 'ISD code must start with + followed by 1-3 digits (e.g. +91, +971)'
                })

            # ── Collect and compare all fields ────────────────────
            changed = {}

            for field in EDITABLE_FIELDS:
                val = post.get(field)
                if val is None:
                    continue
                new_val = str(val).strip()

                # ── Many2one country / nationality dropdowns ───────
                if field in MANY2ONE_FIELDS:
                    try:
                        new_id = int(new_val) if new_val else 0
                    except (ValueError, TypeError):
                        continue

                    current_rec = getattr(employee, field, False)
                    current_id  = current_rec.id if current_rec else 0

                    if new_id and new_id != current_id:
                        # Store as integer string — action_approve does int() on write
                        changed[field] = str(new_id)
                    continue

                # ── Regular text/select fields ────────────────────
                try:
                    current = getattr(employee, field, None)
                    if hasattr(current, 'name'):
                        current_str = str(current.name or '').strip()
                    elif current in (False, None):
                        current_str = ''
                    else:
                        current_str = str(current).strip()

                    if new_val != current_str:
                        changed[field] = new_val
                except Exception:
                    if new_val:
                        changed[field] = new_val

            # ── File uploads ──────────────────────────────────────
            file_changed_fields = {}
            for field in FILE_FIELDS:
                file_obj = request.httprequest.files.get(field)
                if file_obj and file_obj.filename:
                    try:
                        file_data = base64.b64encode(file_obj.read()).decode('utf-8')
                        file_changed_fields[field] = file_data
                        changed[field] = f'[FILE:{file_obj.filename}]'
                    except Exception as e:
                        _logger.warning('File upload failed for %s: %s', field, e)

            if not changed and not file_changed_fields:
                return request.make_json_response({
                    'success':   True,
                    'reference': '',
                    'no_change': True,
                    'message':   'No changes detected. Your profile is already up to date.',
                })

            # ── Write files directly to employee ──────────────────
            if file_changed_fields:
                employee.sudo().write(file_changed_fields)

            # ── Create PCR ────────────────────────────────────────
            ref = ''
            if changed:
                req = request.env['hr.profile.change.request'].sudo().create({
                    'employee_id':    employee.id,
                    'submitted_data': json.dumps(changed),
                    'state':          'draft',
                })
                req.action_submit()
                ref = req.name
                _logger.info('PCR %s created for %s — changed fields: %s',
                             ref, employee.name, list(changed.keys()))

            return request.make_json_response({
                'success':   True,
                'reference': ref,
                'no_change': False,
                'message':   (
                    'Your changes have been submitted. HR will review and notify you.'
                    if ref else
                    'Your documents have been uploaded successfully.'
                ),
            })

        except Exception as e:
            _logger.error('Profile change error for %s: %s', employee.name, str(e))
            return request.make_json_response({'success': False, 'error': str(e)})