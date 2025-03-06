# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class TecReligion(models.Model):
    _name = 'tec.religion'

    name = fields.Char('Religion', copy=False, required=True)

    _sql_constraints = [('unique_tec_religion', 'unique (name)', 'Religion name must be unique.')]


