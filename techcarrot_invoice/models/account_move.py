from odoo import api, fields, models
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"


    doc_no = fields.Char('Doc No#')
    cust_inv_date = fields.Date('Customer INV Date')


