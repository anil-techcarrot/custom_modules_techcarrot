# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class EmployeePractice(models.Model):
    _name = 'employee.practice'

    name = fields.Char('Practice', copy=False, required=True)

    _sql_constraints = [('unique_employee_practice', 'unique (name)', 'Practice name must be unique.')]


