# -*- coding: utf-8 -*-

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import phonenumbers

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    emp_code = fields.Char('Employee Code', copy=False)
    project_id = fields.Many2one('project.project', 'Project', copy=False)