from odoo import models, fields
class StagingSanitizeLog(models.Model):
    _name        = 'staging.sanitize.log'
    _description = 'Staging DB Sanitization Log'
    _order       = 'create_date desc'
    _rec_name    = 'create_date'

    # ── When & Where ──────────────────────────────
    create_date   = fields.Datetime('Sanitized On',   readonly=True)
    database_name = fields.Char('Database Name',      readonly=True)
    status        = fields.Char('Status',             readonly=True)

    # ── Operations ────────────────────────────────
    sign_document_deleted  = fields.Integer('Sign Docs Deleted',      readonly=True)
    payslip_deleted        = fields.Integer('Payslips Deleted',       readonly=True)
    employee_updated       = fields.Integer('Employees Updated',      readonly=True)
    attachment_deleted     = fields.Integer('Attachments Deleted',    readonly=True)
    mail_tracking_deleted  = fields.Integer('Mail Tracking Deleted',  readonly=True)
    gl_entries_deleted     = fields.Integer('GL Entries Deleted',     readonly=True)
    gl_details             = fields.Text('GL Series Details',         readonly=True)

    # ── Errors ────────────────────────────────────
    error_count   = fields.Integer('Total Errors',  readonly=True)
    error_details = fields.Text('Error Details',    readonly=True)