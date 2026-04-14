"""
controllers/portal_employee_personal.py
========================================
Odoo Controller — handles POST from /my/employee/personal
Writes portal user changes back to hr.employee and returns JSON.
Bidirectional sync is automatic because the portal reads directly
from the employee record via t-att-value, so any change saved here
is immediately visible in both the portal and the backend employee form.

USAGE:
  Place this file in your module's /controllers/ folder.
  Register the route in __init__.py:
      from . import portal_employee_personal
"""

from odoo import http, fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FIELD MAP  →  { form_field_name : (odoo_model_field, writable_by_portal) }
# writable_by_portal = True  → employee can self-update
# writable_by_portal = False → read-only on portal (HR manages in backend)
# ---------------------------------------------------------------------------
PERSONAL_FIELD_MAP = {
    # Basic Information
    "employee_first_name":          ("employee_first_name",          True),
    "employee_middle_name":         ("employee_middle_name",          True),
    "employee_last_name":           ("employee_last_name",            True),
    "employee_name_english":        ("employee_name_english",         False),
    "employee_name_arabic":         ("employee_name_arabic",          True),
    "emp_code":                     ("emp_code",                      False),
    "work_email":                   ("work_email",                    False),
    "work_phone":                   ("work_phone",                    False),
    "x_nationality":                ("x_nationality",                 False),
    "nationality_at_birth_id":      ("nationality_at_birth_id",       False),
    "sex":                          ("sex",                           False),
    "birthday":                     ("birthday",                      True),
    "place_of_birth":               ("place_of_birth",                True),
    "marital":                      ("marital",                       False),
    "children":                     ("children",                      False),
    "disabled":                     ("disabled",                      False),
    "legal_name":                   ("legal_name",                    False),
    "blooad_group":                 ("blooad_group",                  True),
    "religion":                     ("religion",                      True),
    "mother_tongue_id":             ("mother_tongue_id",              False),
    "lang":                         ("lang",                          False),

    # Identity Documents
    "emirates_id_number":           ("emirates_id_number",            True),
    "x_emirates_id":                ("x_emirates_id",                 True),
    "emirates_issue_date":          ("emirates_issue_date",           True),
    "emirates_expiry_date":         ("emirates_expiry_date",          True),
    "x_emirates_expiry":            ("x_emirates_expiry",             True),
    "x_passport_number":            ("x_passport_number",             True),
    "issue_countries_id":           ("issue_countries_id",            False),
    "issue_date":                   ("issue_date",                    True),
    "x_passport_expiry":            ("x_passport_expiry",             True),
    "x_passport_country":           ("x_passport_country",            True),
    "x_passport_issue":             ("x_passport_issue",              True),
    "visa_no":                      ("visa_no",                       False),
    "visa_sponser":                 ("visa_sponser",                  False),
    "visa_issue_date":              ("visa_issue_date",               False),
    "entry_exit_date":              ("entry_exit_date",               False),
    "permit_no":                    ("permit_no",                     False),
    "has_work_permit":              ("has_work_permit",               False),
    "home_country_id_name":         ("home_country_id_name",          False),
    "home_country_id_number":       ("home_country_id_number",        False),
    "aadhar_no":                    ("aadhar_no",                     True),
    "pan":                          ("pan",                           True),
    "uan":                          ("uan",                           False),
    "pf_number":                    ("pf_number",                     False),

    # Contact Information
    "private_email":                ("private_email",                 True),
    "private_phone":                ("private_phone",                 True),
    "country_code_for_personal_mob_no": ("country_code_for_personal_mob_no", True),
    "whatsapp":                     ("whatsapp",                      True),
    "home_land_line_no":            ("home_land_line_no",             True),
    "linkedin":                     ("linkedin",                      True),
    "facebook_profile":             ("facebook_profile",              True),
    "insta_profile":                ("insta_profile",                 True),
    "twitter_profile":              ("twitter_profile",               True),

    # Address
    "private_street":               ("private_street",                True),
    "private_street2":              ("private_street2",               True),
    "private_city":                 ("private_city",                  True),
    "private_state_id":             ("private_state_id",              False),
    "private_zip":                  ("private_zip",                   True),
    "distance_home_work":           ("distance_home_work",            False),
    "country_residences":           ("country_residences",            False),
    "house_no":                     ("house_no",                      True),
    "area_name":                    ("area_name",                     True),
    "city":                         ("city",                          False),
    "states_id":                    ("states_id",                     False),
    "zip_code":                     ("zip_code",                      True),
    "countries_id":                 ("countries_id",                  False),
    "e_private_street":             ("e_private_street",              True),
    "u_private_street":             ("u_private_street",              True),

    # Emergency Contacts
    "emergency_contact":            ("emergency_contact",             True),
    "emergency_phone":              ("emergency_phone",               True),
    "emergency_contact_person_name":  ("emergency_contact_person_name",  True),
    "emergency_contact_person_phone": ("emergency_contact_person_phone", True),
    "emergency_contact_person_name_1":  ("emergency_contact_person_name_1",  True),
    "emergency_contact_person_phone_1": ("emergency_contact_person_phone_1", True),
    "relationship_with_emp_id":     ("relationship_with_emp_id",      False),

    # Family
    "father_name":                  ("father_name",                   False),
    "father_dob":                   ("father_dob",                    False),
    "dependent_status":             ("dependent_status",              False),
    "mother_name":                  ("mother_name",                   False),
    "mother_dob":                   ("mother_dob",                    False),
    "dependent_status_1":           ("dependent_status_1",            False),
    "spouse_support_no":            ("spouse_support_no",             True),
    "spouse_passport_issue_date":   ("spouse_passport_issue_date",    True),
    "spouse_passport_expiry_date":  ("spouse_passport_expiry_date",   True),
    "spouse_visa_no":               ("spouse_visa_no",                True),
    "spouse_visa_expire_date":      ("spouse_visa_expire_date",       True),
    "spouse_emirates_id_no":        ("spouse_emirates_id_no",         True),
    "spouse_emirates_issue_date":   ("spouse_emirates_issue_date",    True),
    "spouse_emirates_id_expiry_date": ("spouse_emirates_id_expiry_date", True),
    "spouse_aadhar_no":             ("spouse_aadhar_no",              True),
    "dependent_child_name_1":       ("dependent_child_name_1",        True),
    "dependent_child_dob_1":        ("dependent_child_dob_1",         True),
    "dependent_child_gender_1":     ("dependent_child_gender_1",      False),
    "dependent_child_passport_no":  ("dependent_child_passport_no",   True),
    "dependent_child_passport_issue_date_1":  ("dependent_child_passport_issue_date_1",  True),
    "dependent_child_passport_expiry_date_1": ("dependent_child_passport_expiry_date_1", True),
    "dependent_child_visa_no_1":    ("dependent_child_visa_no_1",     True),
    "dependent_child_visa_expiration_date_1": ("dependent_child_visa_expiration_date_1", True),
    "dependent_child_emirates_id_no_1":       ("dependent_child_emirates_id_no_1",       True),
    "dependent_child_emirates_id_issue_date_1": ("dependent_child_emirates_id_issue_date_1", True),
    "dependent_child_emirates_id_expiry_date_1": ("dependent_child_emirates_id_expiry_date_1", True),
    "dependent_child_aadhar_no_1":  ("dependent_child_aadhar_no_1",   True),

    # Employee Details / Skills
    "employee_nominee_name":        ("employee_nominee_name",         True),
    "employee_nominee_contact_no":  ("employee_nominee_contact_no",   True),
    "domain_worked":                ("domain_worked",                 False),
    "primary_skill":                ("primary_skill",                 False),
    "secondary_skill":              ("secondary_skill",               False),
    "tool_used":                    ("tool_used",                     False),
    "names":                        ("names",                         False),

    # Education
    "certificate":                  ("certificate",                   False),
    "study_field":                  ("study_field",                   False),
    "institute_name":               ("institute_name",                False),
    "degree_name":                  ("degree_name",                   False),
    "field_of_study":               ("field_of_study",                False),
    "start_date_of_degree":         ("start_date_of_degree",          False),
    "completion_date_of_degree":    ("completion_date_of_degree",     False),
    "year_of_passing":              ("year_of_passing",               False),
    "score":                        ("score",                         False),
    "degree_certificate_legal":     ("degree_certificate_legal",      False),
    "certification_obtained":       ("certification_obtained",        False),

    # Career Details
    "industry_start_date":          ("industry_start_date",           False),
    "experience":                   ("experience",                    False),
    "current_role":                 ("current_role",                  False),
    "no_of_carrer_break":           ("no_of_carrer_break",            False),
    "career_break":                 ("career_break",                  False),
    "career_break_detail":          ("career_break_detail",           False),
    "career_break_start_date":      ("career_break_start_date",       False),
    "career_break_end_date":        ("career_break_end_date",         False),

    # Industry / Reference
    "last_report_manager_mob_no":   ("last_report_manager_mob_no",    False),
    "industry_ref_name":            ("industry_ref_name",             False),
    "industry_ref_email":           ("industry_ref_email",            False),
    "industry_ref_mob_no":          ("industry_ref_mob_no",           False),
    "previous_company_name":        ("previous_company_name",         False),
    "designation":                  ("designation",                   False),
    "period_in_company":            ("period_in_company",             False),
    "reason_of_leaving":            ("reason_of_leaving",             False),
    "candidate_source":             ("candidate_source",              False),

    # TechCarrot General
    "practice":                     ("practice",                      False),
    "sub_practice":                 ("sub_practice",                  False),
    "practice_heads_id":            ("practice_heads_id",             False),
    "engagement_location":          ("engagement_location",           False),
    "emp_inside_uae":               ("emp_inside_uae",                False),
    "branch_name":                  ("branch_name",                   False),
    "bank_name":                    ("bank_name",                     False),
    "payroll":                      ("payroll",                       False),
    "mentor_names_id":              ("mentor_names_id",               False),
    "doj":                          ("doj",                           False),
    "original_hire_date":           ("original_hire_date",            False),
    "current_address":              ("current_address",               False),
    "phone_code_1":                 ("phone_code_1",                  False),
    "employement_status_id":        ("employement_status_id",         False),
    "notice_period":                ("notice_period",                 False),
    "resign_date":                  ("resign_date",                   False),
    "end_date":                     ("end_date",                      False),
    "lwd":                          ("lwd",                           False),
    "customer_acc_name":            ("customer_acc_name",             False),
    "exit_type_id":                 ("exit_type_id",                  False),
    "exit_reason_id":               ("exit_reason_id",                False),
}

# Date fields that need conversion from string to date object
DATE_FIELDS = {
    "birthday", "emirates_issue_date", "emirates_expiry_date", "x_emirates_expiry",
    "issue_date", "x_passport_expiry", "x_passport_issue", "visa_issue_date",
    "entry_exit_date", "spouse_passport_issue_date", "spouse_passport_expiry_date",
    "spouse_visa_expire_date", "spouse_emirates_issue_date", "spouse_emirates_id_expiry_date",
    "dependent_child_dob_1", "dependent_child_passport_issue_date_1",
    "dependent_child_passport_expiry_date_1", "dependent_child_visa_expiration_date_1",
    "dependent_child_emirates_id_issue_date_1", "dependent_child_emirates_id_expiry_date_1",
    "industry_start_date", "start_date_of_degree", "completion_date_of_degree",
    "career_break_start_date", "career_break_end_date", "doj", "original_hire_date",
    "resign_date", "end_date", "lwd", "father_dob", "mother_dob",
}

# Boolean fields
BOOL_FIELDS = {"disabled", "emp_inside_uae"}

# Integer fields
INT_FIELDS = {"children", "notice_period", "no_of_carrer_break"}


class PortalEmployeePersonal(http.Controller):

    @http.route('/my/employee/personal', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_personal(self, **kwargs):
        """
        GET  → render the personal details page (handled by the QWeb template).
        POST → receive form data, validate, write to hr.employee, return JSON.
        """
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not employee:
            return request.make_response(
                '{"success": false, "error": "No employee record found"}',
                headers=[('Content-Type', 'application/json')]
            )

        if request.httprequest.method == 'POST':
            return self._handle_post(employee, kwargs)

        # GET — render template
        return request.render('employee_self_service_portal.portal_employee_profile_personal', {
            'employee': employee,
        })

    def _handle_post(self, employee, post_data):
        """
        Builds an Odoo write dict from POST data, filtering to only
        portal-writable fields, then calls employee.write().
        Returns JSON {success: true} or {success: false, error: "..."}.
        """
        write_vals = {}

        for form_name, (odoo_field, writable) in PERSONAL_FIELD_MAP.items():
            if not writable:
                continue  # Skip HR-managed fields

            raw_value = post_data.get(form_name)
            if raw_value is None:
                continue  # Not submitted

            # Type coercions
            if form_name in DATE_FIELDS:
                value = fields.Date.from_string(raw_value) if raw_value else False
            elif form_name in BOOL_FIELDS:
                value = raw_value in ('1', 'true', 'True', True)
            elif form_name in INT_FIELDS:
                try:
                    value = int(raw_value) if raw_value else 0
                except ValueError:
                    value = 0
            else:
                value = raw_value.strip() if raw_value else False

            write_vals[odoo_field] = value

        if not write_vals:
            return request.make_response(
                '{"success": false, "error": "No writable fields submitted"}',
                headers=[('Content-Type', 'application/json')]
            )

        try:
            employee.sudo().write(write_vals)
            _logger.info("Portal personal update: employee %s, fields: %s",
                         employee.name, list(write_vals.keys()))
            return request.make_response(
                '{"success": true}',
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error("Portal personal update error for employee %s: %s",
                          employee.name, str(e))
            return request.make_response(
                f'{{"success": false, "error": "{str(e)}"}}',
                headers=[('Content-Type', 'application/json')]
            )


"""
=============================================================================
HOW BIDIRECTIONAL SYNC WORKS
=============================================================================

PORTAL  →  EMPLOYEE MODULE:
  - When portal user saves, the POST handler above calls employee.sudo().write()
  - This writes directly to the hr.employee record in the Odoo database
  - The next time the HR user opens the employee form in the backend, 
    they see the updated values immediately — no extra sync needed.

EMPLOYEE MODULE  →  PORTAL:
  - The portal template reads fields via t-att-value="employee.field_name"
  - Every page load fetches the current value from hr.employee
  - Any HR change in the backend is immediately reflected on the portal
    when the employee refreshes their profile page.

=============================================================================
ADDING MORE EDITABLE FIELDS
=============================================================================

1. In the XML template: the field's <input> or <select> name must match
   the form_name key in PERSONAL_FIELD_MAP.

2. In this controller: set the writable flag to True for the field.

3. In the JS EDITABLE_FIELDS array: add the field name so it gets 
   unlocked when the user toggles Edit Mode.

4. Ensure the corresponding field exists on hr.employee (either standard
   Odoo field or a custom x_ field defined in your module).

=============================================================================
SECURITY NOTES
=============================================================================

- The controller uses sudo() only for reading/writing to hr.employee.
  The user authentication is still checked via auth='user'.
- Only fields with writable=True in PERSONAL_FIELD_MAP are ever written,
  regardless of what the portal form submits — this prevents tampering.
- Sensitive HR fields (wage, contract, company, approvers, etc.) are 
  always writable=False and will never be written through this endpoint.
"""