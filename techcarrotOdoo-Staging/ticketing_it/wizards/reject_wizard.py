# -*- coding: utf-8 -*-

from odoo import models, fields


class ITTicketRejectWizard(models.TransientModel):
    _name = 'it.ticket.reject.wizard'
    _description = 'Reject Ticket Wizard'

    # Ticket that is being rejected through this wizard
    ticket_id = fields.Many2one('it.ticket', 'Ticket', required=True)

    # Reason provided by user for rejecting the ticket
    rejection_reason = fields.Text('Rejection Reason', required=True)

    def action_reject(self):
        """Execute rejection workflow and close the wizard."""

        # Call main ticket reject logic with sudo to ensure access safety
        self.ticket_id.sudo().do_reject(self.rejection_reason)

        # Close wizard after rejection is processed
        return {'type': 'ir.actions.act_window_close'}