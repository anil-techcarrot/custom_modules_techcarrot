# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class SubPractice(models.Model):
    _name = 'sub.practice'

    name = fields.Char('Sub Practice', copy=False, required=True)

    _sql_constraints = [('unique_sub_practice', 'unique (name)', 'Sub Practice must be unique.')]


