from odoo import api, fields, models
from odoo.osv import expression


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    iban_no = fields.Char('IBAN')

    _sql_constraints = [
        (
            "iban_no_unique",
            "unique(iban_no)","Bank IBAN should be unique.",
        ),
    ]