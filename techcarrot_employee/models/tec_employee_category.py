# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class EmployeeCategory(models.Model):
    _name = 'employee.category'

    name = fields.Char('Employee Category', copy=False, required=True)

    _sql_constraints = [('unique_employee_category', 'unique (name)', 'Employee Category must be unique.')]


