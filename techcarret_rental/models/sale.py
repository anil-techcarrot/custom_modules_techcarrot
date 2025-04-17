# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        self._check_amount_is_positive()
        has_rental_order=False
        has_invoice_lines=False
        for sale in self.sale_order_ids:
            if sale.is_rental_order == True:
                has_rental_order=True
            if sale.rental_inv_line_ids:
                has_invoice_lines=True
        if has_rental_order==True and has_invoice_lines==True:
            for sale in self.sale_order_ids:
                count=0
                for rental in sale.rental_inv_line_ids:
                    if count==0 and rental.state=='draft':
                        sale._cron_create_rental_month_invoices(rental)
                    count = count + 1
        else:
            invoices = self._create_invoices(self.sale_order_ids)
            return self.sale_order_ids.action_view_invoice(invoices=invoices)
