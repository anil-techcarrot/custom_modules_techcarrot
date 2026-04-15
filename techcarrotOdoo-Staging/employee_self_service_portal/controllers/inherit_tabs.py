# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

MY_EMPLOYEE_URL = '/my/employee'


class EmployeePortalPayroll(http.Controller):

    # =====================================================
    # Get Logged Employee
    # =====================================================
    def _get_employee(self):
        return request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

    # =====================================================
    # Payroll Page (GET + POST)
    # =====================================================
    @http.route(
        MY_EMPLOYEE_URL + '/payroll',
        type='http',
        auth='user',
        website=True,
        methods=['GET', 'POST']
    )
    def portal_employee_payroll(self, **post):

        employee = self._get_employee()

        if not employee:
            return request.redirect('/my')

        # =====================================================
        # POST → Save Data
        # =====================================================
        if request.httprequest.method == 'POST':
            try:
                vals = {}

                # -------------------------------
                # Contract Overview
                # -------------------------------
                if post.get('contract_date_start'):
                    vals['contract_date_start'] = post.get('contract_date_start')

                if post.get('wage_type'):
                    vals['wage_type'] = post.get('wage_type')

                # ⚠️ DO NOT allow portal to change relational HR config
                # safer to comment these unless required
                # if post.get('contract_type_id'):
                #     vals['contract_type_id'] = int(post.get('contract_type_id'))

                # if post.get('structure_type_id'):
                #     vals['structure_type_id'] = int(post.get('structure_type_id'))

                # -------------------------------
                # Annual Leave
                # -------------------------------
                if post.get('l10n_ae_number_of_leave_days'):
                    try:
                        vals['l10n_ae_number_of_leave_days'] = float(
                            post.get('l10n_ae_number_of_leave_days')
                        )
                    except:
                        pass

                # -------------------------------
                # Tax
                # -------------------------------
                if post.get('l10n_in_tds'):
                    try:
                        vals['l10n_in_tds'] = float(post.get('l10n_in_tds'))
                    except:
                        pass

                # -------------------------------
                # Manual Salary Components
                # -------------------------------
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
                        try:
                            vals[field] = float(post.get(field))
                        except:
                            pass

                # -------------------------------
                # WRITE VALUES
                # -------------------------------
                if vals:
                    employee.sudo().write(vals)

                # 👉 IMPORTANT: return redirect (not JSON)
                return request.redirect('/my/employee/payroll')

            except Exception as e:
                _logger.exception("Payroll update error")

                return request.render(
                    'employee_self_service_portal.portal_employee_profile_payroll',
                    {
                        'employee': employee,
                        'section': 'payroll',
                        'error': str(e),
                    }
                )

        # =====================================================
        # GET → Load Page
        # =====================================================
        return request.render(
            'employee_self_service_portal.portal_employee_profile_payroll',
            {
                'employee': employee,
                'section': 'payroll',
            }
        )