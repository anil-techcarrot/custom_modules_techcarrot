# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class ExitType(models.Model):
    _name = 'exit.type'

    name = fields.Char('Exit Type', copy=False, required=True)

    _sql_constraints = [('unique_exit_type', 'unique (name)', 'Exit Type name must be unique.')]


