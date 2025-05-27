# -*- coding: utf-8 -*-

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import phonenumbers

class HrContractInherit(models.Model):
    _inherit = 'hr.contract'

    aat_allowance = fields.Monetary('MI Allowance', copy=False)
    sub_total = fields.Monetary('Sub Total', copy=False)
    emp_code = fields.Char('Employee Code', copy=False)

    @api.model
    def create(self, vals):
        if 'emp_code' in vals and not vals.get('employee_id'):
            emp_code = vals['emp_code']
            employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
            if employee:
                vals['employee_id'] = employee.id
        return super(HrContractInherit, self).create(vals)



class HrSalaryInherit(models.Model):
    _inherit = 'hr.salary.attachment'

    emp_code = fields.Char('Employee Code', copy=False)

    @api.model
    def create(self, vals):
        if 'emp_code' in vals and not vals.get('employee_ids'):
            emp_code = vals['emp_code']
            employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
            if employee:
                vals['employee_ids'] = employee.ids
        return super(HrSalaryInherit, self).create(vals)


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    emp_code = fields.Char('Employee Code', copy=False)

    @api.model
    def create(self, vals):
        if 'emp_code' in vals and not vals.get('employee_id'):
            emp_code = vals['emp_code']
            employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
            if employee:
                vals['employee_id'] = employee.id
        return super(HrLeaveInherit, self).create(vals)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    emp_code = fields.Char('Employee Code', copy=False)

    @api.model
    def create(self, vals):
        if 'emp_code' in vals and not vals.get('employee_id'):
            emp_code = vals['emp_code']
            employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
            if employee:
                vals['employee_id'] = employee.id
        return super(HrAttendance, self).create(vals)
