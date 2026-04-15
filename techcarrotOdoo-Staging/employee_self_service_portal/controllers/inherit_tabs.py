# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

MY_EMPLOYEE_URL = '/my/employee'


class EmployeePortalPayroll(http.Controller):

    def _get_employee(self):
        """Get logged-in employee"""
        return request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

    # =====================================================
    # Payroll Page (GET + POST)
    # =====================================================
    @http.route(MY_EMPLOYEE_URL + '/payroll', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_payroll(self, **post):
        """
        Payroll tab — GET renders the page, POST saves allowed fields.
        Read-only fields (salary, allowances) are shown but not writable
        from portal — HR manages them in the backend.
        Portal → Employee: writes directly to hr.employee via sudo()
        Employee → Portal: template reads fresh from hr.employee on every load
        """
        employee = self._get_employee()

        if not employee:
            return request.redirect('/my')

        # ── POST: Save editable payroll fields ───────────────────────────────
        if request.httprequest.method == 'POST':
            try:
                vals = {}

                # =======================
                # Contract Overview
                # =======================
                if post.get('contract_date_start'):
                    vals['contract_date_start'] = post.get('contract_date_start')

                if post.get('wage_type'):
                    vals['wage_type'] = post.get('wage_type')

                if post.get('contract_type_id'):
                    vals['contract_type_id'] = int(post.get('contract_type_id'))

                if post.get('structure_type_id'):
                    vals['structure_type_id'] = int(post.get('structure_type_id'))

                # =======================
                # Annual Leave
                # =======================
                if post.get('l10n_ae_number_of_leave_days'):
                    vals['l10n_ae_number_of_leave_days'] = float(
                        post.get('l10n_ae_number_of_leave_days')
                    )

                # =======================
                # Tax
                # =======================
                if post.get('l10n_in_tds'):
                    vals['l10n_in_tds'] = float(post.get('l10n_in_tds'))

                # =======================
                # Manual Salary Components
                # =======================
                float_fields = [
                    'basic_salary_manual',
                    'hra_manual',
                    'flexi_manual',
                    'statutory_manual',
                    'gratuity_manual',
                    'pf_manual',
                    'medical_manual',
                ]

                for field in float_fields:
                    if post.get(field):
                        vals[field] = float(post.get(field))

                # =======================
                # WRITE VALUES
                # =======================
                employee.sudo().write(vals)

                return request.make_json_response({
                    'success': True,
                    'message': 'Payroll details updated successfully'
                })

            except Exception as e:
                _logger.exception("Payroll update error")
                return request.make_json_response({
                    'success': False,
                    'error': str(e)
                })

        # =======================
        # GET (Load Page)
        # =======================
        return request.render(
            'employee_self_service_portal.portal_employee_profile_payroll',
            {
                'employee': employee,
                'section': 'payroll',
            }
        )