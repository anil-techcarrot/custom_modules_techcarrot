from odoo import api, fields, models
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    doc_no = fields.Char('Doc No#')
    cust_inv_date = fields.Date('Customer INV Date')

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company = m.company_id or self.env.company
            m.suitable_journal_ids = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                # ('type', '=', journal_type),
            ])

class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_pdf_report_id(self, move):
        return self.env.ref('techcarrot_invoice.action_generate_techcarrot_invoice_report')

    @api.model
    def _get_default_mail_attachments_widget(self, move, mail_template, extra_edis=None, pdf_report=None):
        # \
        # + self._get_placeholder_mail_template_dynamic_attachments_data(move, mail_template, pdf_report=pdf_report) \
        # + self._get_invoice_extra_attachments_data(move) \
        # + self._get_mail_template_attachments_data(mail_template)
        return self._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)