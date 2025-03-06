from odoo import api, fields, models
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"


    def get_company_account_aed(self):
        print('o.company_id.bank_ids------------',self.company_id.bank_ids)
        for bank in self.company_id.bank_ids:
            if bank.currency_id.name == 'AED':
                print('dfdfdf')



    def get_company_account_usd(self):
        print('o.company_id.bank_ids------------',self.company_id.bank_ids)