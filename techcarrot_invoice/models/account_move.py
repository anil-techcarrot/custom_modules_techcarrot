from odoo import api, fields, models, _
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


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    project_code = fields.Char('Project Code', copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    # domain_project_ids = fields.Many2many('project.project', compute='_compute_project_ids')

    # @api.depends('account_id')
    # def _compute_project_ids(self):
    #     for rec in self:
    #         domain = [('stage_id.name', 'not in', ['To Do', 'Cancelled'])]
    #         domain_project_ids = self.env['project.project'].search(domain)
    #         rec.domain_project_ids = domain_project_ids.ids

    def _check_qty_whole_fraction(self):
        qty = self.quantity
        frac_qty = str(self.quantity).split('.')[1]
        frac_qty = int(frac_qty)
        if frac_qty == 0:
            qty = "{:,.2f}".format(self.quantity)
        else:
            digits = f"{self.quantity:.6f}"
            if '.' in digits:
                qty = digits.rstrip('0').rstrip('.')
        return qty


    def inv_action_replace_product_desc(self):
        print('rrrrrrrrrrrrrrrrrrrrrrr')
        return {
            'name': _('Enter Product Desc'),
            'type': 'ir.actions.act_window',
            'res_model': 'inv.edit.product.desc',
            'view_mode': 'form',
            # 'context': {'default_demand_quantity': self.product_uom_qty},
            'target': 'new',
        }

