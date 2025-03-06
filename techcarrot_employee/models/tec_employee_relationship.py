# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class EmployeeRelationship(models.Model):
    _name = 'employee.relationship'

    name = fields.Char('Employee Relationship Name', copy=False, required=True)

    _sql_constraints = [('unique_employee_relationship', 'unique (name)', 'Employee Relationship name must be unique.')]

