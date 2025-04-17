# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id', inverse='_inverse_journal_id', store=True, readonly=False, precompute=True,
        required=True,
        check_company=True,
        domain="[('id', 'in', suitable_journal_ids)]",
    )

    @api.onchange('journal_id')
    def _inverse_journal_id(self):
        self._conditional_add_to_compute('company_id', lambda m: (
            not m.company_id
            or m.company_id != m.journal_id.company_id
        ))
        self._conditional_add_to_compute('currency_id', lambda m: (
            not m.currency_id
            or m.journal_id.currency_id and m.currency_id != m.journal_id.currency_id
        ))

    @api.depends('move_type', 'origin_payment_id', 'statement_line_id')
    def _compute_journal_id(self):
        for move in self.filtered(lambda r: r.journal_id.type not in r._get_valid_journal_types()):
            #GET JOURNAL FOR 3 TYPE OF OPERATION
            invoice_origin = ''
            if move.invoice_origin:
                invoice_origin= move.invoice_origin
            elif move.ref:
                invoice_origin= move.ref
            if invoice_origin:
                if not move.company_id.rental_journal_id:
                    raise UserError(_("Default journal not found for rental."))
                if not move.company_id.subscription_journal_id:
                    raise UserError(_("Default journal not found for subscription."))
                if not move.company_id.sales_journal_id:
                    raise UserError(_("Default journal not found for project."))
                so_obj = self.env['sale.order'].search([('name', '=', invoice_origin)], limit=1)
                if so_obj:
                    if so_obj.is_rental_order == True:
                        move.journal_id = move.company_id.rental_journal_id.id
                    elif so_obj.is_subscription == True:
                        move.journal_id = move.company_id.subscription_journal_id.id
                    else:
                        move.journal_id = move.company_id.sales_journal_id.id
                else:
                    move.journal_id = move._search_default_journal()
            else:
                move.journal_id = move._search_default_journal()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    rental_start_date = fields.Datetime('Rental Start Date')
    rental_return_date = fields.Datetime('Rental Return Date')

    @api.depends('product_id', 'move_id.ref', 'move_id.payment_reference', 'rental_start_date', 'rental_return_date')
    def _compute_name(self):
        def get_name(line):
            values = []
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id
            if not product:
                return False
            if line.journal_id.type == 'sale':
                values.append(product.display_name)
                if product.description_sale:
                    values.append(product.description_sale)
                if line.rental_start_date and line.rental_return_date:
                    s_date = datetime.strptime(str(line.rental_start_date), "%Y-%m-%d %H:%M:%S").date()
                    r_date = datetime.strptime(str(line.rental_return_date), "%Y-%m-%d %H:%M:%S").date()
                    s_date = str(s_date) +' TO '+str(r_date)
                    values.append(s_date)
            elif line.journal_id.type == 'purchase':
                values.append(product.display_name)
                if product.description_purchase:
                    values.append(product.description_purchase)
            return '\n'.join(values)
        term_by_move = (self.move_id.line_ids | self).filtered(lambda l: l.display_type == 'payment_term').sorted(lambda l: l.date_maturity or date.max).grouped('move_id')
        for line in self.filtered(lambda l: l.move_id.inalterable_hash is False):
            if line.rental_start_date and line.rental_return_date:
                if line.display_type == 'product':
                    line.name = get_name(line)
            else:
                if line.display_type == 'payment_term':
                    term_lines = term_by_move.get(line.move_id, self.env['account.move.line'])
                    n_terms = len(line.move_id.invoice_payment_term_id.line_ids)
                    if line.move_id.payment_reference and line.move_id.ref:
                        name = f'{line.move_id.ref} - {line.move_id.payment_reference}'
                    else:
                        name = line.move_id.payment_reference or ''
                    if n_terms > 1:
                        index = term_lines._ids.index(line.id) if line in term_lines else len(term_lines)
                        name = _('%(name)s installment #%(number)s', name=name, number=index + 1).lstrip()
                    if n_terms > 1 or not line.name or line._origin.name == line._origin.move_id.payment_reference or (
                            line._origin.move_id.payment_reference and line._origin.move_id.ref
                            and line._origin.name == f'{line._origin.move_id.ref} - {line._origin.move_id.payment_reference}'
                    ):
                        line.name = name
                if not line.product_id or line.display_type in ('line_section', 'line_note'):
                    continue
                if not line.name or line._origin.name == get_name(line._origin):
                    line.name = get_name(line)