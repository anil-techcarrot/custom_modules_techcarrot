# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FIELD_LABELS = {
    'work_phone': 'Work Phone', 'private_email': 'Personal Email',
    'private_phone': 'Personal Phone', 'private_street': 'Address Line 1',
    'private_street2': 'Address Line 2', 'private_city': 'City (Private)',
    'private_zip': 'ZIP Code', 'private_state_id': 'State/Province',
    'whatsapp': 'WhatsApp', 'linkedin': 'LinkedIn',
    'legal_name': 'Legal Name', 'facebook_profile': 'Facebook Profile',
    'insta_profile': 'Instagram Profile', 'twitter_profile': 'Twitter Profile',
    'blood_group': 'Blood Group',
    'issue_date': 'Passport Issue Date', 'expiry_date': 'Passport Expiry Date',
    'l10n_in_relationship': 'Emergency Relationship',
    'emergency_phone': 'Emergency Phone', 'e_private_city': 'Emergency Address',
    'emergency_contact_person_name': 'Emergency Contact Name',
    'emergency_contact_person_phone': 'Emergency Contact Phone',
    'alternate_mobile_number': 'Alternate Mobile',
    'emergency_contact_person_name_1': 'Emergency Contact Name (2)',
    'emergency_contact_person_phone_1': 'Emergency Contact Phone (2)',
    'second_alternative_number': 'Second Alternative Number',
    'home_land_line_no': 'Home Land Line',
    'spouse_passport_no': 'Spouse Passport No',
    'spouse_passport_issue_date': 'Spouse Passport Issue Date',
    'spouse_passport_expiry_date': 'Spouse Passport Expiry Date',
    'spouse_visa_no': 'Spouse Visa No',
    'spouse_visa_expire_date': 'Spouse Visa Expiry Date',
    'spouse_emirates_id_no': 'Spouse Emirates ID No',
    'spouse_emirates_issue_date': 'Spouse Emirates Issue Date',
    'spouse_emirates_id_expiry_date': 'Spouse Emirates ID Expiry Date',
    'spouse_aadhar_no': 'Spouse Aadhar No',
    'dependent_child_name_1': 'Child 1 Name', 'dependent_child_dob_1': 'Child 1 DOB',
    'dependent_child_passport_no': 'Child 1 Passport No',
    'dependent_child_passport_issue_date_1': 'Child 1 Passport Issue Date',
    'dependent_child_passport_expiry_date_1': 'Child 1 Passport Expiry Date',
    'dependent_child_visa_no_1': 'Child 1 Visa No',
    'dependent_child_visa_expiration_date_1': 'Child 1 Visa Expiry Date',
    'dependent_child_emirates_id_no_1': 'Child 1 Emirates ID No',
    'dependent_child_emirates_id_issue_date_1': 'Child 1 Emirates Issue Date',
    'dependent_child_emirates_id_expiry_date_1': 'Child 1 Emirates Expiry Date',
    'dependent_child_aadhar_no_1': 'Child 1 Aadhar No',
    'father_name': 'Father Name', 'father_dob': 'Father DOB',
    'mother_name': 'Mother Name', 'mother_dob': 'Mother DOB',
    'children': 'No. of Children', 'career_break_detail': 'Career Break Detail',
    'employee_nominee_name': 'Nominee Name',
    'employee_nominee_contact_no': 'Nominee Contact No',
    'domain_worked': 'Domains Worked', 'primary_skill': 'Primary Skills',
    'secondary_skill': 'Secondary Skills', 'tool_used': 'Tools Used',
    'industry_ref_name': 'Industry Reference Name',
    'industry_ref_email': 'Industry Reference Email',
    'industry_ref_mob_no': 'Industry Reference Mobile',
    'home_country_id_name': 'Home Country ID Name',
    'home_country_id_number': 'Home Country ID Number',
    'mother_tongue_name': 'Mother Tongue', 'language_known_name': 'Languages Known',
    'u_private_city': 'Address Inside UAE', 'current_address': 'Current Work Address',
    'phone_code_1': 'ISD Code', 'house_no': 'House No / Building',
    'area_name': 'Area / Town', 'city': 'City (Work)', 'zip_code': 'Zip Code',
    'experience': 'Experience', 'current_role': 'Current / Additional Role',
    'industry_start_date': 'Industry Start Date',
    'last_organisation_name': 'Last Organisation Name',
    'last_location': 'Last Location',
    'last_salary_per_annum_currency': 'Last Salary Currency',
    'last_salary_per_annum_amt': 'Last Salary Amount',
    'reason_for_leaving': 'Reason for Leaving',
    'last_report_manager_name': 'Reporting Manager Name',
    'last_report_manager_designation': 'Reporting Manager Designation',
    'last_report_manager_mob_no': 'Reporting Manager Mobile',
    'last_report_manager_mail': 'Reporting Manager Email',
    'previous_company_name': 'Previous Company Name',
    'designation': 'Designation', 'period_in_company': 'Period in Company',
    'reason_of_leaving': 'Reason of Leaving',
    'emirates_id_file': 'Emirates ID Copy',
    'passport_file': 'Passport Copy',
    'other_documents': 'Other Documents',
    'has_work_permit': 'Work Permit File',
}

# ══════════════════════════════════════════════════════════════════
# ISSUE 21 FIX: Selection fields must be written as-is (they are
# already stored as selection key strings like 'b_pos', 'male' etc.)
# The problem was that write() tried to validate 'b_pos' as a string
# field. We must NOT skip these — they are valid selection values.
#
# Fields that are Selection type on hr.employee:
# blood_group, sex, marital, dependent_child_gender_1
#
# These do NOT need type coercion — they are stored as strings.
# But we MUST NOT skip them in write_vals.
# ══════════════════════════════════════════════════════════════════

# Selection fields - kept as string keys, no coercion needed
SELECTION_FIELDS = {
    'blood_group', 'sex', 'marital', 'dependent_child_gender_1',
}

# Fields that must be skipped during approval write
# (read-only, computed, or binary fields handled separately)
SKIP_ON_APPROVE = {
    'csrf_token', 'submit',
    # Binary file fields are written at submission time, not approval
    'emirates_id_file', 'passport_file', 'other_documents', 'has_work_permit',
}


class HrProfileChangeRequest(models.Model):
    _name = 'hr.profile.change.request'
    _description = 'Employee Profile Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    _check_company_auto = False

    # ── Core fields ───────────────────────────────────────────────
    name = fields.Char(
        string='Reference', required=True, copy=False,
        readonly=True, default='New',
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee', string='Employee',
        required=True, ondelete='cascade', tracking=True,
        check_company=False,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        related='employee_id.department_id',
        string='Department', store=True, readonly=True,
    )
    work_location_id = fields.Many2one(
        related='employee_id.work_location_id',
        string='Work Location', store=True, readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft',    'Draft'),
            ('pending',  'Pending HR Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status', default='draft', tracking=True, index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    submitted_data = fields.Text(string='Submitted Data (JSON)', readonly=True)
    changed_fields_display = fields.Html(
        string='Submitted Changes',
        compute='_compute_changed_fields_display',
        sanitize=False,
    )
    submission_date = fields.Datetime(
        string='Submitted On', default=fields.Datetime.now, readonly=True,
    )
    review_date      = fields.Datetime(string='Reviewed On', readonly=True)
    reviewed_by      = fields.Many2one(comodel_name='res.users', string='Reviewed By', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    trail_ids        = fields.One2many(
        comodel_name='hr.profile.change.request.trail',
        inverse_name='request_id', string='Audit Trail', readonly=True,
    )

    # ── Document upload tracking fields ──────────────────────────
    has_emirates_id_doc = fields.Boolean(
        string='Emirates ID Uploaded',
        compute='_compute_doc_flags', store=True,
    )
    has_passport_doc = fields.Boolean(
        string='Passport Uploaded',
        compute='_compute_doc_flags', store=True,
    )
    has_other_doc = fields.Boolean(
        string='Other Doc Uploaded',
        compute='_compute_doc_flags', store=True,
    )
    has_work_permit_doc = fields.Boolean(
        string='Work Permit Uploaded',
        compute='_compute_doc_flags', store=True,
    )
    has_any_doc = fields.Boolean(
        string='Has Any Document',
        compute='_compute_doc_flags', store=True,
    )
    total_docs_uploaded = fields.Integer(
        string='Total Documents Uploaded',
        compute='_compute_doc_flags', store=True,
    )

    @api.depends('submitted_data')
    def _compute_doc_flags(self):
        doc_field_map = {
            'emirates_id_file': 'has_emirates_id_doc',
            'passport_file':    'has_passport_doc',
            'other_documents':  'has_other_doc',
            'has_work_permit':  'has_work_permit_doc',
        }
        for rec in self:
            flags = {f: False for f in doc_field_map.values()}
            if rec.submitted_data:
                try:
                    data = json.loads(rec.submitted_data)
                    for field_name, flag_name in doc_field_map.items():
                        val = data.get(field_name, '')
                        if val and str(val).strip() not in ('', 'False', 'None', 'false'):
                            flags[flag_name] = True
                except Exception:
                    pass
            for flag_name, value in flags.items():
                setattr(rec, flag_name, value)
            rec.total_docs_uploaded = sum(1 for v in flags.values() if v)
            rec.has_any_doc = any(flags.values())

    # ── HR Reviewer helpers ───────────────────────────────────────
    def _get_hr_reviewer_users(self):
        """Get all HR Reviewer users via SQL (Odoo 17/19 compatible)."""
        try:
            hr_group = self.env.ref(
                'employee_profile_change_request.group_profile_change_hr_reviewer',
                raise_if_not_found=False,
            )
            if not hr_group:
                _logger.warning('HR Reviewer group not found.')
                return self.env['res.users']
            self.env.cr.execute(
                'SELECT uid FROM res_groups_users_rel WHERE gid = %s',
                [hr_group.id]
            )
            user_ids = [row[0] for row in self.env.cr.fetchall()]
            if not user_ids:
                _logger.warning('No users in HR Reviewer group (id=%s)', hr_group.id)
                return self.env['res.users']
            hr_users = self.env['res.users'].sudo().browse(user_ids)
            _logger.info('HR Reviewer users found: %s',
                         [(u.name, u.work_email or u.email) for u in hr_users])
            return hr_users
        except Exception as e:
            _logger.error('_get_hr_reviewer_users error: %s', e)
            return self.env['res.users']

    def _is_hr_reviewer(self):
        """Return True if current user is in HR Reviewer group."""
        try:
            hr_group = self.env.ref(
                'employee_profile_change_request.group_profile_change_hr_reviewer',
                raise_if_not_found=False,
            )
            if not hr_group:
                return False
            self.env.cr.execute(
                'SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s',
                [hr_group.id, self.env.uid]
            )
            return bool(self.env.cr.fetchone())
        except Exception:
            return False

    # ── ORM overrides — ONE definition each, infinite-loop safe ──
    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo()).search(
                domain, offset=offset, limit=limit, order=order,
            )
        return super().search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def search_count(self, domain, limit=None):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo()).search_count(
                domain, limit=limit,
            )
        return super().search_count(domain, limit=limit)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Accept **kwargs — prevents TypeError on ORM internal active_test= calls."""
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo())._search(
                domain, offset=offset, limit=limit, order=order, **kwargs
            )
        return super()._search(
            domain, offset=offset, limit=limit, order=order, **kwargs
        )

    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo()).read_group(
                domain, fields, groupby,
                offset=offset, limit=limit,
                orderby=orderby, lazy=lazy,
            )
        return super().read_group(
            domain, fields, groupby,
            offset=offset, limit=limit,
            orderby=orderby, lazy=lazy,
        )

    # ── Sequence ──────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name_val = vals.get('name', '')
            if not name_val or not name_val.startswith('PCR/'):
                seq = self.env['ir.sequence'].sudo().next_by_code(
                    'hr.profile.change.request'
                )
                if seq:
                    vals['name'] = seq
                else:
                    _logger.error('Sequence hr.profile.change.request not found!')
        return super().create(vals_list)

    # ── Diff table ────────────────────────────────────────────────
    @api.depends('submitted_data', 'employee_id')
    def _compute_changed_fields_display(self):
        for rec in self:
            if not rec.submitted_data:
                rec.changed_fields_display = '<p class="text-muted">No data submitted yet.</p>'
                continue
            try:
                data = json.loads(rec.submitted_data)
                rows = ''
                for key, new_val in data.items():
                    label = FIELD_LABELS.get(key, key.replace('_', ' ').title())
                    # File upload markers
                    if new_val and str(new_val).startswith('[FILE:'):
                        current = '—'
                        new_val_str = str(new_val)
                        is_changed = True
                    else:
                        try:
                            current = getattr(rec.employee_id, key, '') or ''
                            if hasattr(current, 'name'):
                                current = current.name or ''
                            current = str(current)
                        except Exception:
                            current = '—'
                        new_val_str = str(new_val) if new_val else '—'
                        is_changed = new_val_str != current
                    row_style = 'background:#fffde7;' if is_changed else ''
                    badge = (
                        '<span style="background:#ff9800;color:white;padding:2px 6px;'
                        'border-radius:3px;font-size:11px;">CHANGED</span>'
                        if is_changed else ''
                    )
                    rows += (
                        f'<tr style="{row_style}">'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;"><strong>{label}</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;color:#888;">{current or "—"}</td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;color:#2e7d32;font-weight:600;">{new_val_str}</td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;text-align:center;">{badge}</td>'
                        f'</tr>'
                    )
                rec.changed_fields_display = (
                    '<div style="overflow-x:auto;">'
                    '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;">'
                    '<thead><tr style="background:#4e73df;color:white;">'
                    '<th style="padding:10px 12px;text-align:left;border:1px solid #3a5ec9;">Field</th>'
                    '<th style="padding:10px 12px;text-align:left;border:1px solid #3a5ec9;">Current Value</th>'
                    '<th style="padding:10px 12px;text-align:left;border:1px solid #3a5ec9;">Submitted Value</th>'
                    '<th style="padding:10px 12px;text-align:center;border:1px solid #3a5ec9;">Status</th>'
                    f'</tr></thead><tbody>{rows}</tbody></table></div>'
                    '<p style="font-size:11px;color:#999;margin-top:8px;">'
                    '⚠ Highlighted rows indicate values that differ from current record.</p>'
                )
            except Exception as e:
                rec.changed_fields_display = f'<p class="text-danger">Error: {e}</p>'

    # ── Submit ────────────────────────────────────────────────────
    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'pending'})
        self.employee_id.sudo().write({
            'last_portal_submission': self.submitted_data,
            'last_submission_state':  'pending',
        })
        self._add_trail(action='submitted', note=f'Submitted by {self.employee_id.name}')
        self._send_mail_to_hr()
        return True

    # ── Approve ───────────────────────────────────────────────────
    def action_approve(self):
        """
        Approve employee profile change request
        """

        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_('Only pending requests can be approved.'))

        try:
            data = json.loads(self.submitted_data or '{}')
        except Exception:
            raise UserError(_('Submitted data is corrupted.'))

        write_vals = {}

        for k, v in data.items():

            # ============================================================
            # SKIP SYSTEM FIELDS
            # ============================================================
            if k in SKIP_ON_APPROVE:
                continue

            # ============================================================
            # SKIP FILE MARKERS
            # ============================================================
            if v and str(v).startswith('[FILE:'):
                continue

            # ============================================================
            # SKIP EMPTY VALUES
            # ============================================================
            if v is None or v == '':
                continue

            # ============================================================
            # MANY2ONE COUNTRY FIELDS FIX
            # ============================================================
            if k in [
                'country_id',
                'nationality_at_birth_id',
                'issue_countries_id',
            ]:

                try:
                    write_vals[k] = int(v)

                except Exception:

                    _logger.warning(
                        'PCR %s: Invalid Many2one value for %s: %s',
                        self.name,
                        k,
                        v
                    )

                continue

            # ============================================================
            # SELECTION FIELD VALIDATION
            # ============================================================
            if k in SELECTION_FIELDS:

                field_obj = self.employee_id._fields.get(k)

                if field_obj and hasattr(field_obj, 'selection'):

                    sel = field_obj.selection

                    if callable(sel):
                        valid_keys = [s[0] for s in sel(self.employee_id)]
                    else:
                        valid_keys = [s[0] for s in sel]

                    if v not in valid_keys:
                        _logger.warning(
                            'PCR %s: Skipping invalid selection value for %s: %r',
                            self.name,
                            k,
                            v
                        )

                        continue

                write_vals[k] = v
                continue

            # ============================================================
            # INTEGER FIELDS
            # ============================================================
            if k in ['children']:

                try:
                    write_vals[k] = int(v)
                except Exception:
                    pass

                continue

            # ============================================================
            # FLOAT FIELDS
            # ============================================================
            if k in ['last_salary_per_annum_amt']:

                try:
                    write_vals[k] = float(v)
                except Exception:
                    pass

                continue

            # ============================================================
            # NORMAL FIELDS
            # ============================================================
            write_vals[k] = v

        # ================================================================
        # WRITE VALUES TO EMPLOYEE
        # ================================================================
        if write_vals:

            try:

                self.employee_id.sudo().write(write_vals)

                _logger.info(
                    'PCR %s approved — %d fields written to %s: %s',
                    self.name,
                    len(write_vals),
                    self.employee_id.name,
                    list(write_vals.keys())
                )

            except Exception as e:

                _logger.error(
                    'PCR %s: Error writing fields: %s',
                    self.name,
                    e
                )

                raise UserError(_(
                    'Error writing approved data to employee record: %s'
                ) % str(e))

        # ================================================================
        # UPDATE REQUEST STATUS
        # ================================================================
        self.write({
            'state': 'approved',
            'reviewed_by': self.env.user.id,
            'review_date': fields.Datetime.now(),
        })

        # ================================================================
        # ADD AUDIT TRAIL
        # ================================================================
        self._add_trail(
            action='approved',
            note=(
                f'Approved by {self.env.user.name}. '
                f'{len(write_vals)} field(s) written.'
            ),
        )

        # ================================================================
        # SEND MAIL
        # ================================================================
        self._send_mail_to_employee('approved')

        # ================================================================
        # CLEAR PENDING DATA
        # ================================================================
        self.employee_id.sudo().write({
            'last_portal_submission': False,
            'last_submission_state': 'approved',
        })

        return True

    # ── Reject ────────────────────────────────────────────────────
    def action_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Profile Change Request'),
            'res_model': 'hr.profile.change.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    # ── Re-open ───────────────────────────────────────────────────
    def action_reset_to_pending(self):
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError(_('Only rejected requests can be re-opened.'))
        self.write({
            'state': 'pending',
            'rejection_reason': False,
            'reviewed_by': False,
            'review_date': False,
        })
        self.employee_id.sudo().write({
            'last_submission_state':  False,
            'last_portal_submission': False,
        })
        self._add_trail(action='reopened', note=f'Re-opened by {self.env.user.name}')
        return True

    def _add_trail(self, action, note, reason=None):
        self.env['hr.profile.change.request.trail'].sudo().create({
            'request_id':  self.id,
            'action':      action,
            'note':        note,
            'reason':      reason or '',
            'user_id':     self.env.user.id,
            'action_date': fields.Datetime.now(),
        })

    # ── Send mail to HR ───────────────────────────────────────────
    def _send_mail_to_hr(self):
        try:
            hr_users = self._get_hr_reviewer_users()
            if not hr_users:
                _logger.warning('PCR %s: No HR Reviewer users — mail not sent.', self.name)
                return
            hr_emails, hr_names_list = [], []
            for u in hr_users:
                best_email = (
                    u.work_email
                    or u.partner_id.email
                    or (u.login if '@' in (u.login or '') else None)
                )
                if best_email:
                    hr_emails.append(best_email)
                    hr_names_list.append(u.name)
            if not hr_emails:
                _logger.warning('PCR %s: HR Reviewers have no email.', self.name)
                return
            email_to = ', '.join(hr_emails)
            hr_names = ', '.join(hr_names_list)
            mail = self.env['mail.mail'].sudo().create({
                'subject':    f'New Profile Change Request: {self.name} — {self.employee_id.name}',
                'email_to':   email_to,
                'email_from': (
                    self.employee_id.company_id.email
                    or 'notifications@techcarrot-fz-llc1.odoo.com'
                ),
                'auto_delete': False,
                'body_html': f'''
                <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;
                            border:1px solid #ddd;border-radius:8px;overflow:hidden;">
                    <div style="background:#4e73df;padding:24px 28px;">
                        <h2 style="color:white;margin:0;font-size:20px;">📋 New Profile Change Request</h2>
                        <p style="color:#c8d8ff;margin:6px 0 0;font-size:13px;">
                            Action required — please review and approve or reject</p>
                    </div>
                    <div style="padding:24px;background:#f9f9f9;">
                        <p>Dear HR Team,</p>
                        <p><b>{self.employee_id.name}</b> has submitted a profile update request.</p>
                        <table style="width:100%;border-collapse:collapse;margin:16px 0;background:white;">
                            <tr style="background:#eef2ff;">
                                <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;width:38%;">Reference</td>
                                <td style="padding:10px 14px;border:1px solid #ddd;">{self.name}</td>
                            </tr>
                            <tr>
                                <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Employee</td>
                                <td style="padding:10px 14px;border:1px solid #ddd;">{self.employee_id.name}</td>
                            </tr>
                            <tr style="background:#eef2ff;">
                                <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Company</td>
                                <td style="padding:10px 14px;border:1px solid #ddd;">{self.company_id.name if self.company_id else '—'}</td>
                            </tr>
                            <tr>
                                <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Department</td>
                                <td style="padding:10px 14px;border:1px solid #ddd;">{self.department_id.name or '—'}</td>
                            </tr>
                            <tr style="background:#eef2ff;">
                                <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Submitted On</td>
                                <td style="padding:10px 14px;border:1px solid #ddd;">{self.submission_date}</td>
                            </tr>
                        </table>
                        <p>Go to: <b>Profile Change Requests → Pending Review</b></p>
                        <p style="color:#999;font-size:11px;">Sent to: {hr_names}</p>
                    </div>
                </div>''',
            })
            mail.sudo().send()
            _logger.info('PCR %s: HR notification sent to %s', self.name, email_to)
        except Exception as e:
            _logger.warning('PCR %s: Failed to send HR notification: %s', self.name, e)

    # ── Send mail to Employee ─────────────────────────────────────
    def _send_mail_to_employee(self, status):
        try:
            emp_user = self.employee_id.user_id
            emp_email = (
                (emp_user.login if emp_user and '@' in (emp_user.login or '') else None)
                or self.employee_id.work_email
                or self.employee_id.private_email
            )
            if not emp_email:
                _logger.warning('PCR %s: Employee has no email.', self.name)
                return
            if status == 'approved':
                subject = f'Profile Update Approved - {self.name}'
                body = (
                    f'<div style="font-family:Arial,sans-serif;max-width:600px;">'
                    f'<div style="background:#1cc88a;padding:20px;">'
                    f'<h2 style="color:white;margin:0;">✅ Profile Update Approved</h2></div>'
                    f'<div style="padding:20px;background:#f9f9f9;">'
                    f'<p>Dear <b>{self.employee_id.name}</b>,</p>'
                    f'<p>Your request <b>{self.name}</b> has been <b style="color:#1cc88a;">APPROVED</b>.</p>'
                    f'<p>Your profile has been updated successfully.</p>'
                    f'<p>Approved by: <b>{self.reviewed_by.name if self.reviewed_by else "HR"}</b></p>'
                    f'<p><a href="/my/employee/personal" style="background:#1cc88a;color:white;'
                    f'padding:10px 24px;border-radius:6px;text-decoration:none;">View My Profile</a></p>'
                    f'</div></div>'
                )
            else:
                subject = f'Profile Update Rejected - {self.name}'
                body = (
                    f'<div style="font-family:Arial,sans-serif;max-width:600px;">'
                    f'<div style="background:#e74a3b;padding:20px;">'
                    f'<h2 style="color:white;margin:0;">❌ Profile Update Rejected</h2></div>'
                    f'<div style="padding:20px;background:#f9f9f9;">'
                    f'<p>Dear <b>{self.employee_id.name}</b>,</p>'
                    f'<p>Your request <b>{self.name}</b> has been <b style="color:#e74a3b;">REJECTED</b>.</p>'
                    f'<p><b>Reason:</b> {self.rejection_reason or "No reason provided"}</p>'
                    f'<p><a href="/my/employee/personal" style="background:#e74a3b;color:white;'
                    f'padding:10px 24px;border-radius:6px;text-decoration:none;">Go to My Profile</a></p>'
                    f'</div></div>'
                )
            mail = self.env['mail.mail'].sudo().create({
                'subject':     subject,
                'email_to':    emp_email,
                'email_from':  'notifications@techcarrot-fz-llc1.odoo.com',
                'auto_delete': False,
                'body_html':   body,
            })
            mail.sudo().send()
            _logger.info('PCR %s: Employee notification (%s) sent to %s', self.name, status, emp_email)
        except Exception as e:
            _logger.warning('PCR %s: Failed to send employee notification: %s', self.name, e)








# # -*- coding: utf-8 -*-
# import json
# import logging
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
#
# _logger = logging.getLogger(__name__)
#
# FIELD_LABELS = {
#     'work_phone': 'Work Phone', 'private_email': 'Personal Email',
#     'private_phone': 'Personal Phone', 'private_street': 'Address Line 1',
#     'private_street2': 'Address Line 2', 'private_city': 'City (Private)',
#     'private_zip': 'ZIP Code', 'private_state_id': 'State/Province',
#     'whatsapp': 'WhatsApp', 'linkedin': 'LinkedIn',
#     'legal_name': 'Legal Name', 'facebook_profile': 'Facebook Profile',
#     'insta_profile': 'Instagram Profile', 'twitter_profile': 'Twitter Profile',
#     'blood_group': 'Blood Group',
#     'issue_date': 'Passport Issue Date', 'expiry_date': 'Passport Expiry Date',
#     'l10n_in_relationship': 'Emergency Relationship',
#     'emergency_phone': 'Emergency Phone', 'e_private_city': 'Emergency Address',
#     'emergency_contact_person_name': 'Emergency Contact Name',
#     'emergency_contact_person_phone': 'Emergency Contact Phone',
#     'alternate_mobile_number': 'Alternate Mobile',
#     'emergency_contact_person_name_1': 'Emergency Contact Name (2)',
#     'emergency_contact_person_phone_1': 'Emergency Contact Phone (2)',
#     'second_alternative_number': 'Second Alternative Number',
#     'home_land_line_no': 'Home Land Line',
#     'spouse_passport_no': 'Spouse Passport No',
#     'spouse_passport_issue_date': 'Spouse Passport Issue Date',
#     'spouse_passport_expiry_date': 'Spouse Passport Expiry Date',
#     'spouse_visa_no': 'Spouse Visa No',
#     'spouse_visa_expire_date': 'Spouse Visa Expiry Date',
#     'spouse_emirates_id_no': 'Spouse Emirates ID No',
#     'spouse_emirates_issue_date': 'Spouse Emirates Issue Date',
#     'spouse_emirates_id_expiry_date': 'Spouse Emirates ID Expiry Date',
#     'spouse_aadhar_no': 'Spouse Aadhar No',
#     'dependent_child_name_1': 'Child 1 Name', 'dependent_child_dob_1': 'Child 1 DOB',
#     'dependent_child_passport_no': 'Child 1 Passport No',
#     'dependent_child_passport_issue_date_1': 'Child 1 Passport Issue Date',
#     'dependent_child_passport_expiry_date_1': 'Child 1 Passport Expiry Date',
#     'dependent_child_visa_no_1': 'Child 1 Visa No',
#     'dependent_child_visa_expiration_date_1': 'Child 1 Visa Expiry Date',
#     'dependent_child_emirates_id_no_1': 'Child 1 Emirates ID No',
#     'dependent_child_emirates_id_issue_date_1': 'Child 1 Emirates Issue Date',
#     'dependent_child_emirates_id_expiry_date_1': 'Child 1 Emirates Expiry Date',
#     'dependent_child_aadhar_no_1': 'Child 1 Aadhar No',
#     'father_name': 'Father Name', 'father_dob': 'Father DOB',
#     'mother_name': 'Mother Name', 'mother_dob': 'Mother DOB',
#     'children': 'No. of Children', 'career_break_detail': 'Career Break Detail',
#     'employee_nominee_name': 'Nominee Name',
#     'employee_nominee_contact_no': 'Nominee Contact No',
#     'domain_worked': 'Domains Worked', 'primary_skill': 'Primary Skills',
#     'secondary_skill': 'Secondary Skills', 'tool_used': 'Tools Used',
#     'industry_ref_name': 'Industry Reference Name',
#     'industry_ref_email': 'Industry Reference Email',
#     'industry_ref_mob_no': 'Industry Reference Mobile',
#     'home_country_id_name': 'Home Country ID Name',
#     'home_country_id_number': 'Home Country ID Number',
#     'mother_tongue_name': 'Mother Tongue', 'language_known_name': 'Languages Known',
#     'u_private_city': 'Address Inside UAE', 'current_address': 'Current Work Address',
#     'phone_code_1': 'ISD Code', 'house_no': 'House No / Building',
#     'area_name': 'Area / Town', 'city': 'City (Work)', 'zip_code': 'Zip Code',
#     'experience': 'Experience', 'current_role': 'Current / Additional Role',
#     'industry_start_date': 'Industry Start Date',
#     'last_organisation_name': 'Last Organisation Name',
#     'last_location': 'Last Location',
#     'last_salary_per_annum_currency': 'Last Salary Currency',
#     'last_salary_per_annum_amt': 'Last Salary Amount',
#     'reason_for_leaving': 'Reason for Leaving',
#     'last_report_manager_name': 'Reporting Manager Name',
#     'last_report_manager_designation': 'Reporting Manager Designation',
#     'last_report_manager_mob_no': 'Reporting Manager Mobile',
#     'last_report_manager_mail': 'Reporting Manager Email',
#     'previous_company_name': 'Previous Company Name',
#     'designation': 'Designation', 'period_in_company': 'Period in Company',
#     'reason_of_leaving': 'Reason of Leaving',
#     'emirates_id_file': 'Emirates ID Copy',
#     'passport_file': 'Passport Copy',
#     'other_documents': 'Other Documents',
#     'has_work_permit': 'Work Permit File',
# }
#
# # ══════════════════════════════════════════════════════════════════
# # ISSUE 21 FIX: Selection fields must be written as-is (they are
# # already stored as selection key strings like 'b_pos', 'male' etc.)
# # The problem was that write() tried to validate 'b_pos' as a string
# # field. We must NOT skip these — they are valid selection values.
# #
# # Fields that are Selection type on hr.employee:
# # blood_group, sex, marital, dependent_child_gender_1
# #
# # These do NOT need type coercion — they are stored as strings.
# # But we MUST NOT skip them in write_vals.
# # ══════════════════════════════════════════════════════════════════
#
# # Selection fields - kept as string keys, no coercion needed
# SELECTION_FIELDS = {
#     'blood_group', 'sex', 'marital', 'dependent_child_gender_1',
# }
#
# # Fields that must be skipped during approval write
# # (read-only, computed, or binary fields handled separately)
# SKIP_ON_APPROVE = {
#     'csrf_token', 'submit',
#     # Binary file fields are written at submission time, not approval
#     'emirates_id_file', 'passport_file', 'other_documents', 'has_work_permit',
# }
#
#
# class HrProfileChangeRequest(models.Model):
#     _name = 'hr.profile.change.request'
#     _description = 'Employee Profile Change Request'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'create_date desc'
#     _rec_name = 'name'
#
#     _check_company_auto = False
#
#     # ── Core fields ───────────────────────────────────────────────
#     name = fields.Char(
#         string='Reference', required=True, copy=False,
#         readonly=True, default='New',
#     )
#     employee_id = fields.Many2one(
#         comodel_name='hr.employee', string='Employee',
#         required=True, ondelete='cascade', tracking=True,
#         check_company=False,
#     )
#     department_id = fields.Many2one(
#         comodel_name='hr.department',
#         related='employee_id.department_id',
#         string='Department', store=True, readonly=True,
#     )
#     work_location_id = fields.Many2one(
#         related='employee_id.work_location_id',
#         string='Work Location', store=True, readonly=True,
#     )
#     state = fields.Selection(
#         selection=[
#             ('draft',    'Draft'),
#             ('pending',  'Pending HR Review'),
#             ('approved', 'Approved'),
#             ('rejected', 'Rejected'),
#         ],
#         string='Status', default='draft', tracking=True, index=True,
#     )
#     company_id = fields.Many2one(
#         'res.company', string='Company',
#         default=lambda self: self.env.company,
#     )
#     submitted_data = fields.Text(string='Submitted Data (JSON)', readonly=True)
#     changed_fields_display = fields.Html(
#         string='Submitted Changes',
#         compute='_compute_changed_fields_display',
#         sanitize=False,
#     )
#     submission_date = fields.Datetime(
#         string='Submitted On', default=fields.Datetime.now, readonly=True,
#     )
#     review_date      = fields.Datetime(string='Reviewed On', readonly=True)
#     reviewed_by      = fields.Many2one(comodel_name='res.users', string='Reviewed By', readonly=True)
#     rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
#     trail_ids        = fields.One2many(
#         comodel_name='hr.profile.change.request.trail',
#         inverse_name='request_id', string='Audit Trail', readonly=True,
#     )
#
#     # ── Document upload tracking fields ──────────────────────────
#     has_emirates_id_doc = fields.Boolean(
#         string='Emirates ID Uploaded',
#         compute='_compute_doc_flags', store=True,
#     )
#     has_passport_doc = fields.Boolean(
#         string='Passport Uploaded',
#         compute='_compute_doc_flags', store=True,
#     )
#     has_other_doc = fields.Boolean(
#         string='Other Doc Uploaded',
#         compute='_compute_doc_flags', store=True,
#     )
#     has_work_permit_doc = fields.Boolean(
#         string='Work Permit Uploaded',
#         compute='_compute_doc_flags', store=True,
#     )
#     has_any_doc = fields.Boolean(
#         string='Has Any Document',
#         compute='_compute_doc_flags', store=True,
#     )
#     total_docs_uploaded = fields.Integer(
#         string='Total Documents Uploaded',
#         compute='_compute_doc_flags', store=True,
#     )
#
#     @api.depends('submitted_data')
#     def _compute_doc_flags(self):
#         doc_field_map = {
#             'emirates_id_file': 'has_emirates_id_doc',
#             'passport_file':    'has_passport_doc',
#             'other_documents':  'has_other_doc',
#             'has_work_permit':  'has_work_permit_doc',
#         }
#         for rec in self:
#             flags = {f: False for f in doc_field_map.values()}
#             if rec.submitted_data:
#                 try:
#                     data = json.loads(rec.submitted_data)
#                     for field_name, flag_name in doc_field_map.items():
#                         val = data.get(field_name, '')
#                         if val and str(val).strip() not in ('', 'False', 'None', 'false'):
#                             flags[flag_name] = True
#                 except Exception:
#                     pass
#             for flag_name, value in flags.items():
#                 setattr(rec, flag_name, value)
#             rec.total_docs_uploaded = sum(1 for v in flags.values() if v)
#             rec.has_any_doc = any(flags.values())
#
#     # ── HR Reviewer helpers ───────────────────────────────────────
#     def _get_hr_reviewer_users(self):
#         """Get all HR Reviewer users via SQL (Odoo 17/19 compatible)."""
#         try:
#             hr_group = self.env.ref(
#                 'employee_profile_change_request.group_profile_change_hr_reviewer',
#                 raise_if_not_found=False,
#             )
#             if not hr_group:
#                 _logger.warning('HR Reviewer group not found.')
#                 return self.env['res.users']
#             self.env.cr.execute(
#                 'SELECT uid FROM res_groups_users_rel WHERE gid = %s',
#                 [hr_group.id]
#             )
#             user_ids = [row[0] for row in self.env.cr.fetchall()]
#             if not user_ids:
#                 _logger.warning('No users in HR Reviewer group (id=%s)', hr_group.id)
#                 return self.env['res.users']
#             hr_users = self.env['res.users'].sudo().browse(user_ids)
#             _logger.info('HR Reviewer users found: %s',
#                          [(u.name, u.work_email or u.email) for u in hr_users])
#             return hr_users
#         except Exception as e:
#             _logger.error('_get_hr_reviewer_users error: %s', e)
#             return self.env['res.users']
#
#     def _is_hr_reviewer(self):
#         """Return True if current user is in HR Reviewer group."""
#         try:
#             hr_group = self.env.ref(
#                 'employee_profile_change_request.group_profile_change_hr_reviewer',
#                 raise_if_not_found=False,
#             )
#             if not hr_group:
#                 return False
#             self.env.cr.execute(
#                 'SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s',
#                 [hr_group.id, self.env.uid]
#             )
#             return bool(self.env.cr.fetchone())
#         except Exception:
#             return False
#
#     # ── ORM overrides — ONE definition each, infinite-loop safe ──
#     @api.model
#     def search(self, domain, offset=0, limit=None, order=None):
#         if self._is_hr_reviewer() and not self.env.su:
#             return super(HrProfileChangeRequest, self.sudo()).search(
#                 domain, offset=offset, limit=limit, order=order,
#             )
#         return super().search(domain, offset=offset, limit=limit, order=order)
#
#     @api.model
#     def search_count(self, domain, limit=None):
#         if self._is_hr_reviewer() and not self.env.su:
#             return super(HrProfileChangeRequest, self.sudo()).search_count(
#                 domain, limit=limit,
#             )
#         return super().search_count(domain, limit=limit)
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         """Accept **kwargs — prevents TypeError on ORM internal active_test= calls."""
#         if self._is_hr_reviewer() and not self.env.su:
#             return super(HrProfileChangeRequest, self.sudo())._search(
#                 domain, offset=offset, limit=limit, order=order, **kwargs
#             )
#         return super()._search(
#             domain, offset=offset, limit=limit, order=order, **kwargs
#         )
#
#     def read_group(self, domain, fields, groupby, offset=0, limit=None,
#                    orderby=False, lazy=True):
#         if self._is_hr_reviewer() and not self.env.su:
#             return super(HrProfileChangeRequest, self.sudo()).read_group(
#                 domain, fields, groupby,
#                 offset=offset, limit=limit,
#                 orderby=orderby, lazy=lazy,
#             )
#         return super().read_group(
#             domain, fields, groupby,
#             offset=offset, limit=limit,
#             orderby=orderby, lazy=lazy,
#         )
#
#     # ── Sequence ──────────────────────────────────────────────────
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             name_val = vals.get('name', '')
#             if not name_val or not name_val.startswith('PCR/'):
#                 seq = self.env['ir.sequence'].sudo().next_by_code(
#                     'hr.profile.change.request'
#                 )
#                 if seq:
#                     vals['name'] = seq
#                 else:
#                     _logger.error('Sequence hr.profile.change.request not found!')
#         return super().create(vals_list)
#
#     # ── Diff table ────────────────────────────────────────────────
#     @api.depends('submitted_data', 'employee_id')
#     def _compute_changed_fields_display(self):
#         for rec in self:
#             if not rec.submitted_data:
#                 rec.changed_fields_display = '<p class="text-muted">No data submitted yet.</p>'
#                 continue
#             try:
#                 data = json.loads(rec.submitted_data)
#                 rows = ''
#                 for key, new_val in data.items():
#                     label = FIELD_LABELS.get(key, key.replace('_', ' ').title())
#                     # File upload markers
#                     if new_val and str(new_val).startswith('[FILE:'):
#                         current = '—'
#                         new_val_str = str(new_val)
#                         is_changed = True
#                     else:
#                         try:
#                             current = getattr(rec.employee_id, key, '') or ''
#                             if hasattr(current, 'name'):
#                                 current = current.name or ''
#                             current = str(current)
#                         except Exception:
#                             current = '—'
#                         new_val_str = str(new_val) if new_val else '—'
#                         is_changed = new_val_str != current
#                     row_style = 'background:#fffde7;' if is_changed else ''
#                     badge = (
#                         '<span style="background:#ff9800;color:white;padding:2px 6px;'
#                         'border-radius:3px;font-size:11px;">CHANGED</span>'
#                         if is_changed else ''
#                     )
#                     rows += (
#                         f'<tr style="{row_style}">'
#                         f'<td style="padding:8px 12px;border:1px solid #ddd;"><strong>{label}</strong></td>'
#                         f'<td style="padding:8px 12px;border:1px solid #ddd;color:#888;">{current or "—"}</td>'
#                         f'<td style="padding:8px 12px;border:1px solid #ddd;color:#2e7d32;font-weight:600;">{new_val_str}</td>'
#                         f'<td style="padding:8px 12px;border:1px solid #ddd;text-align:center;">{badge}</td>'
#                         f'</tr>'
#                     )
#                 rec.changed_fields_display = (
#                     '<div style="overflow-x:auto;">'
#                     '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;">'
#                     '<thead><tr style="background:#4e73df;color:white;">'
#                     '<th style="padding:10px 12px;text-align:left;border:1px solid #3a5ec9;">Field</th>'
#                     '<th style="padding:10px 12px;text-align:left;border:1px solid #3a5ec9;">Current Value</th>'
#                     '<th style="padding:10px 12px;text-align:left;border:1px solid #3a5ec9;">Submitted Value</th>'
#                     '<th style="padding:10px 12px;text-align:center;border:1px solid #3a5ec9;">Status</th>'
#                     f'</tr></thead><tbody>{rows}</tbody></table></div>'
#                     '<p style="font-size:11px;color:#999;margin-top:8px;">'
#                     '⚠ Highlighted rows indicate values that differ from current record.</p>'
#                 )
#             except Exception as e:
#                 rec.changed_fields_display = f'<p class="text-danger">Error: {e}</p>'
#
#     # ── Submit ────────────────────────────────────────────────────
#     def action_submit(self):
#         self.ensure_one()
#         self.write({'state': 'pending'})
#         self.employee_id.sudo().write({
#             'last_portal_submission': self.submitted_data,
#             'last_submission_state':  'pending',
#         })
#         self._add_trail(action='submitted', note=f'Submitted by {self.employee_id.name}')
#         self._send_mail_to_hr()
#         return True
#
#     # ── Approve ───────────────────────────────────────────────────
#     def action_approve(self):
#         """
#         ISSUE 21 FIX:
#         blood_group, sex, marital are Selection fields on hr.employee.
#         Their values from the portal form are the selection KEY strings
#         (e.g. 'b_pos', 'male', 'married') which are exactly what
#         hr.employee.write() expects.
#
#         The previous error was:
#           ValueError: Wrong value for hr.employee.blood_group: 'b_pos'
#
#         This was caused by the field being present in submitted_data
#         as 'b_pos' (string) but NOT being excluded from write_vals,
#         so write() received it. BUT the real cause was that blood_group
#         was NOT in the portal EDITABLE_FIELDS in the controller, so it
#         was submitted as a raw form value.
#
#         FIX: We validate Selection field values before writing.
#         If the value is not a valid selection key, we skip it.
#         """
#         self.ensure_one()
#         if self.state != 'pending':
#             raise UserError(_('Only pending requests can be approved.'))
#         try:
#             data = json.loads(self.submitted_data or '{}')
#         except Exception:
#             raise UserError(_('Submitted data is corrupted.'))
#
#         write_vals = {}
#
#         for k, v in data.items():
#             # Skip system/file fields
#             if k in SKIP_ON_APPROVE:
#                 continue
#             # Skip file markers
#             if v and str(v).startswith('[FILE:'):
#                 continue
#             # Skip empty values
#             if v is None or v == '':
#                 continue
#
#             # ── Selection field validation (ISSUE 21 FIX) ──────────
#             if k in SELECTION_FIELDS:
#                 # Get valid selection keys from the field definition
#                 field_obj = self.employee_id._fields.get(k)
#                 if field_obj and hasattr(field_obj, 'selection'):
#                     sel = field_obj.selection
#                     # selection can be a list of (key, label) or a method
#                     if callable(sel):
#                         valid_keys = [s[0] for s in sel(self.employee_id)]
#                     else:
#                         valid_keys = [s[0] for s in sel]
#                     if v not in valid_keys:
#                         _logger.warning(
#                             'PCR %s: Skipping invalid selection value for %s: %r (valid: %s)',
#                             self.name, k, v, valid_keys
#                         )
#                         continue
#                 write_vals[k] = v
#                 continue
#
#             write_vals[k] = v
#
#         # ── Integer coercions ──────────────────────────────────────
#         for f in ('children',):
#             if f in write_vals:
#                 try:    write_vals[f] = int(write_vals[f])
#                 except: write_vals.pop(f, None)
#
#         # ── Float coercions ────────────────────────────────────────
#         for f in ('last_salary_per_annum_amt',):
#             if f in write_vals:
#                 try:    write_vals[f] = float(write_vals[f])
#                 except: write_vals.pop(f, None)
#
#         # ── Write to employee ──────────────────────────────────────
#         if write_vals:
#             try:
#                 self.employee_id.sudo().write(write_vals)
#                 _logger.info(
#                     'PCR %s approved — %d fields written to %s: %s',
#                     self.name, len(write_vals), self.employee_id.name,
#                     list(write_vals.keys())
#                 )
#             except Exception as e:
#                 _logger.error('PCR %s: Error writing fields: %s', self.name, e)
#                 raise UserError(_(
#                     'Error writing approved data to employee record: %s\n\n'
#                     'Fields attempted: %s'
#                 ) % (str(e), ', '.join(write_vals.keys())))
#
#         self.write({
#             'state': 'approved',
#             'reviewed_by': self.env.user.id,
#             'review_date': fields.Datetime.now(),
#         })
#         self._add_trail(
#             action='approved',
#             note=f'Approved by {self.env.user.name}. {len(write_vals)} field(s) written.',
#         )
#         self._send_mail_to_employee('approved')
#         self.employee_id.sudo().write({
#             'last_portal_submission': False,
#             'last_submission_state':  'approved',
#         })
#         return True
#
#     # ── Reject ────────────────────────────────────────────────────
#     def action_reject(self):
#         self.ensure_one()
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Reject Profile Change Request'),
#             'res_model': 'hr.profile.change.request.reject.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {'default_request_id': self.id},
#         }
#
#     # ── Re-open ───────────────────────────────────────────────────
#     def action_reset_to_pending(self):
#         self.ensure_one()
#         if self.state != 'rejected':
#             raise UserError(_('Only rejected requests can be re-opened.'))
#         self.write({
#             'state': 'pending',
#             'rejection_reason': False,
#             'reviewed_by': False,
#             'review_date': False,
#         })
#         self.employee_id.sudo().write({
#             'last_submission_state':  False,
#             'last_portal_submission': False,
#         })
#         self._add_trail(action='reopened', note=f'Re-opened by {self.env.user.name}')
#         return True
#
#     def _add_trail(self, action, note, reason=None):
#         self.env['hr.profile.change.request.trail'].sudo().create({
#             'request_id':  self.id,
#             'action':      action,
#             'note':        note,
#             'reason':      reason or '',
#             'user_id':     self.env.user.id,
#             'action_date': fields.Datetime.now(),
#         })
#
#     # ── Send mail to HR ───────────────────────────────────────────
#     def _send_mail_to_hr(self):
#         try:
#             hr_users = self._get_hr_reviewer_users()
#             if not hr_users:
#                 _logger.warning('PCR %s: No HR Reviewer users — mail not sent.', self.name)
#                 return
#             hr_emails, hr_names_list = [], []
#             for u in hr_users:
#                 best_email = (
#                     u.work_email
#                     or u.partner_id.email
#                     or (u.login if '@' in (u.login or '') else None)
#                 )
#                 if best_email:
#                     hr_emails.append(best_email)
#                     hr_names_list.append(u.name)
#             if not hr_emails:
#                 _logger.warning('PCR %s: HR Reviewers have no email.', self.name)
#                 return
#             email_to = ', '.join(hr_emails)
#             hr_names = ', '.join(hr_names_list)
#             mail = self.env['mail.mail'].sudo().create({
#                 'subject':    f'New Profile Change Request: {self.name} — {self.employee_id.name}',
#                 'email_to':   email_to,
#                 'email_from': (
#                     self.employee_id.company_id.email
#                     or 'notifications@techcarrot-fz-llc1.odoo.com'
#                 ),
#                 'auto_delete': False,
#                 'body_html': f'''
#                 <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;
#                             border:1px solid #ddd;border-radius:8px;overflow:hidden;">
#                     <div style="background:#4e73df;padding:24px 28px;">
#                         <h2 style="color:white;margin:0;font-size:20px;">📋 New Profile Change Request</h2>
#                         <p style="color:#c8d8ff;margin:6px 0 0;font-size:13px;">
#                             Action required — please review and approve or reject</p>
#                     </div>
#                     <div style="padding:24px;background:#f9f9f9;">
#                         <p>Dear HR Team,</p>
#                         <p><b>{self.employee_id.name}</b> has submitted a profile update request.</p>
#                         <table style="width:100%;border-collapse:collapse;margin:16px 0;background:white;">
#                             <tr style="background:#eef2ff;">
#                                 <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;width:38%;">Reference</td>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;">{self.name}</td>
#                             </tr>
#                             <tr>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Employee</td>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;">{self.employee_id.name}</td>
#                             </tr>
#                             <tr style="background:#eef2ff;">
#                                 <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Company</td>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;">{self.company_id.name if self.company_id else '—'}</td>
#                             </tr>
#                             <tr>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Department</td>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;">{self.department_id.name or '—'}</td>
#                             </tr>
#                             <tr style="background:#eef2ff;">
#                                 <td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Submitted On</td>
#                                 <td style="padding:10px 14px;border:1px solid #ddd;">{self.submission_date}</td>
#                             </tr>
#                         </table>
#                         <p>Go to: <b>Profile Change Requests → Pending Review</b></p>
#                         <p style="color:#999;font-size:11px;">Sent to: {hr_names}</p>
#                     </div>
#                 </div>''',
#             })
#             mail.sudo().send()
#             _logger.info('PCR %s: HR notification sent to %s', self.name, email_to)
#         except Exception as e:
#             _logger.warning('PCR %s: Failed to send HR notification: %s', self.name, e)
#
#     # ── Send mail to Employee ─────────────────────────────────────
#     def _send_mail_to_employee(self, status):
#         try:
#             emp_user = self.employee_id.user_id
#             emp_email = (
#                 (emp_user.login if emp_user and '@' in (emp_user.login or '') else None)
#                 or self.employee_id.work_email
#                 or self.employee_id.private_email
#             )
#             if not emp_email:
#                 _logger.warning('PCR %s: Employee has no email.', self.name)
#                 return
#             if status == 'approved':
#                 subject = f'Profile Update Approved - {self.name}'
#                 body = (
#                     f'<div style="font-family:Arial,sans-serif;max-width:600px;">'
#                     f'<div style="background:#1cc88a;padding:20px;">'
#                     f'<h2 style="color:white;margin:0;">✅ Profile Update Approved</h2></div>'
#                     f'<div style="padding:20px;background:#f9f9f9;">'
#                     f'<p>Dear <b>{self.employee_id.name}</b>,</p>'
#                     f'<p>Your request <b>{self.name}</b> has been <b style="color:#1cc88a;">APPROVED</b>.</p>'
#                     f'<p>Your profile has been updated successfully.</p>'
#                     f'<p>Approved by: <b>{self.reviewed_by.name if self.reviewed_by else "HR"}</b></p>'
#                     f'<p><a href="/my/employee/personal" style="background:#1cc88a;color:white;'
#                     f'padding:10px 24px;border-radius:6px;text-decoration:none;">View My Profile</a></p>'
#                     f'</div></div>'
#                 )
#             else:
#                 subject = f'Profile Update Rejected - {self.name}'
#                 body = (
#                     f'<div style="font-family:Arial,sans-serif;max-width:600px;">'
#                     f'<div style="background:#e74a3b;padding:20px;">'
#                     f'<h2 style="color:white;margin:0;">❌ Profile Update Rejected</h2></div>'
#                     f'<div style="padding:20px;background:#f9f9f9;">'
#                     f'<p>Dear <b>{self.employee_id.name}</b>,</p>'
#                     f'<p>Your request <b>{self.name}</b> has been <b style="color:#e74a3b;">REJECTED</b>.</p>'
#                     f'<p><b>Reason:</b> {self.rejection_reason or "No reason provided"}</p>'
#                     f'<p><a href="/my/employee/personal" style="background:#e74a3b;color:white;'
#                     f'padding:10px 24px;border-radius:6px;text-decoration:none;">Go to My Profile</a></p>'
#                     f'</div></div>'
#                 )
#             mail = self.env['mail.mail'].sudo().create({
#                 'subject':     subject,
#                 'email_to':    emp_email,
#                 'email_from':  'notifications@techcarrot-fz-llc1.odoo.com',
#                 'auto_delete': False,
#                 'body_html':   body,
#             })
#             mail.sudo().send()
#             _logger.info('PCR %s: Employee notification (%s) sent to %s', self.name, status, emp_email)
#         except Exception as e:
#             _logger.warning('PCR %s: Failed to send employee notification: %s', self.name, e)
#
#
