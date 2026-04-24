# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ITTicketType(models.Model):
    _name = 'it.ticket.type'
    _description = 'IT Ticket Type'
    _rec_name = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Ticket type code must be unique!')
    ]


class ITTicket(models.Model):
    _name = 'it.ticket'
    _description = 'IT Support Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ======================
    # BASIC FIELDS
    # ======================

    name = fields.Char(
        string='Ticket Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self._get_current_employee(),
        tracking=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        related='employee_id.user_id.partner_id',
        store=True,
        readonly=True
    )

    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )

    # ======================
    # DETAILS
    # ======================

    # ticket_type = fields.Selection([
    #     ('hardware', 'Hardware Issue'),
    #     ('software', 'Software Issue'),
    #     ('social_media', 'Social Media Access'),
    #     ('network', 'Network Issue'),
    #     ('other', 'Other'),
    # ], required=True, tracking=True, string='Ticket Type')
    ticket_type_id = fields.Many2one(
        'it.ticket.type',
        string='Ticket Type Id',
        required=True,
        tracking=True
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', required=True, tracking=True, string='Priority')

    subject = fields.Char(required=True, tracking=True, string='Subject')
    description = fields.Html(required=True, string='Description')
    required_date = fields.Date(string='Required By Date')
    user_id = fields.Many2one('res.users', string="Assigned To")
    # ======================
    # STATE
    # ======================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approval', 'Pending Line Manager'),
        # ('category_manager_approval', 'Pending Category Manager'),
        ('it_approval', 'Pending IT Manager'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], default='manager_approval', tracking=True, string='Status')

    # ======================
    # APPROVERS
    # ======================

    line_manager_id = fields.Many2one(
        'res.users',
        compute='_compute_line_manager',
        store=True,
        string='Line Manager'
    )

    it_manager_id = fields.Many2one(
        'res.users',
        compute='_compute_it_manager',
        store=True,
        string='IT Manager'
    )

    # ===== UPDATED =====
    assigned_to_id = fields.Many2one(
        'res.users',
        string="Assigned To",
        tracking=True
    )
    suggested_assigned_to_id = fields.Many2one(
        'res.users',
        string="Suggested IT Support",
        compute="_compute_suggested_assignee"
    )
    # ======================
    # DATES
    # ======================

    submitted_date = fields.Date(readonly=True, string='Submitted Date')
    manager_approval_date = fields.Date(readonly=True, string='Manager Approval Date')
    # category_manager_approval_date = fields.Date(readonly=True, string='Category Manager Approval Date')
    it_approval_date = fields.Date(readonly=True, string='IT Approval Date')
    done_date = fields.Date(readonly=True, string='Completion Date')
    month_solved = fields.Char(string="Month", compute='_compute_month_solved', store=True)
    last_reminder_sent = fields.Date(
        readonly=True,
        string='Last Reminder Sent'
    )
    duration = fields.Selection([
        ('3m', '3 Months'),
        ('6m', '6 Months'),
        ('12m', '1 Year'),
        ('custom', 'Custom Date')
    ], default='3m', string="Access Duration")

    custom_expiry_date = fields.Date(string="Custom Date")

    access_start_date = fields.Date()
    access_end_date = fields.Date()
    access_finish_date = fields.Date()
    # ======================
    # REJECTION
    # ======================

    rejection_reason = fields.Text(readonly=True, string='Rejection Reason')
    rejected_by_id = fields.Many2one('res.users', readonly=True, string='Rejected By')
    rejected_date = fields.Datetime(readonly=True, string='Rejection Date')

    # =========================================================
    # HELPER: GET FROM EMAIL DYNAMICALLY FROM ODOO SETTINGS
    # =========================================================
    allowed_it_users = fields.Many2many(
        "res.users", compute="_compute_allowed_it_users"
    )

    show_it_manager = fields.Boolean(
        string="Visible to IT Manager",
        compute="_compute_show_to_it_manager",
        store=True,  # <-- important!
    )
    show_it_teams = fields.Boolean(
        string="Visible to IT team",
        compute="_compute_show_to_it_team",
        store=True,  # <-- important!
    )
    is_line_manager = fields.Boolean(compute="_compute_user_roles")
    is_it_manager = fields.Boolean(compute="_compute_user_roles")
    show_to_line_manager = fields.Boolean(
        compute="_compute_show_line_manager"
    )

    line_manager_user_id = fields.Many2one('res.users', string='Line Manager User')  # New field

    # ======================
    # REPORTING FIELDS (DAYS)
    # ======================

    manager_processing_days = fields.Float(
        string="Manager Processing (Days)",
        compute="_compute_processing_days",
        store=True,
        aggregator="avg"
    )

    it_processing_days = fields.Float(
        string="IT Manager Processing (Days)",
        compute="_compute_processing_days",
        store=True,
        aggregator="avg"
    )

    it_team_processing_days = fields.Float(
        string="IT Team Processing (Days)",
        compute="_compute_processing_days",
        store=True,
        aggregator="avg"
    )
    status_category = fields.Selection(
        [('open', 'Open'), ('closed', 'Closed')],
        string='Status Category',
        compute='_compute_status_category',
        store=True
    )
    open_count = fields.Integer(string="Open Count", compute="_compute_counts", store=True)
    closed_count = fields.Integer(string="Closed Count", compute="_compute_counts", store=True)
    is_social_media = fields.Boolean(compute="_compute_is_social_media")
    # statusbar_states = fields.Char(
    #     compute='_compute_statusbar_states'
    # )
    workflow_level = fields.Selection(
        [
            ('0', '0'),
            ('1', '1'),
            ('2', '2'),
            # ('3', '3'),  # ✅ ADD
            # ('4', '4'),  # ✅ ADD
        ],
        compute='_compute_workflow_level',
        store=True
    )
    # category_manager_id = fields.Many2one(
    #     'res.users',
    #     string="Category Manager",
    #     tracking=True
    # )

    # Compute workflow level dynamically based on ticket type configuration
    @api.depends('ticket_type_id')
    def _compute_workflow_level(self):
        for rec in self:
            config = self.env['it.ticket.workflow.config'].search([
                ('ticket_type_id', '=', rec.ticket_type_id.id)
            ], limit=1)

            rec.workflow_level = config.workflow_level if config else '0'


    can_edit = fields.Boolean(compute="_compute_can_edit", store=False)

    # Determine if current user can edit ticket based on role and state
    @api.depends('state', 'assigned_to_id', 'line_manager_id')
    def _compute_can_edit(self):
        for rec in self:
            user = self.env.user

            rec.can_edit = False  # default

            # 1. Pending IT Manager
            if rec.state == 'it_approval' and user.has_group('ticketing_it.group_it_manager'):
                _logger.info("IT Manager can edit")
                rec.can_edit = True

            # 2. Pending Category Manager
            # elif rec.state == 'category_manager_approval' and user.has_group('ticketing_it.group_category_manager'):
            #     rec.can_edit = True

            # 3. Pending Line Manager
            elif rec.state == 'manager_approval' and rec.line_manager_id.user_id == user:
                _logger.info("Line Manager can edit")
                rec.can_edit = False

            # 4. Assigned / In Progress → only assignee
            elif rec.state in ['assigned', 'in_progress'] and rec.assigned_to_id == user:
                _logger.info("Assignee can edit")
                rec.can_edit = False

            # 5. Done / Rejected → no one
            elif rec.state in ['done', 'rejected']:
                _logger.info("Noone can edit")
                rec.can_edit = True
                _logger.info("rec.can_edit %s", rec.can_edit)

    # Identify if ticket belongs to social media category
    def _compute_is_social_media(self):
        social_media = self.env.ref('ticketing_it.type_social', raise_if_not_found=False)
        for rec in self:
            rec.is_social_media = rec.ticket_type_id == social_media

    # Auto-suggest first IT team member if ticket is unassigned
    @api.depends()
    def _compute_suggested_assignee(self):

        it_team = self.env.ref('ticketing_it.group_it_team', raise_if_not_found=False)

        first_user = False
        if it_team and it_team.user_ids:
            first_user = it_team.user_ids[0]

        for rec in self:
            if not rec.assigned_to_id and first_user:
                rec.assigned_to_id = first_user

    # Compute open and closed ticket counts for reporting
    @api.depends('state')
    def _compute_counts(self):
        for rec in self:
            rec.open_count = 1 if rec.status_category == 'open' else 0
            rec.closed_count = 1 if rec.status_category == 'closed' else 0

    # Categorize tickets as open or closed based on state
    @api.depends('state')
    def _compute_status_category(self):
        open_count = defaultdict(int)
        closed_count = defaultdict(int)

        for rec in self:
            # Compute status
            if rec.state in ['done', 'rejected']:
                rec.status_category = 'closed'
                closed_count[rec.ticket_type_id.code] += 1
                _logger.info("rec.ticket_type_id.code: %s | closed_count[rec.ticket_type_id]: %s",
                             rec.ticket_type_id.code, closed_count[rec.ticket_type_id.code])
            else:
                rec.status_category = 'open'
                open_count[rec.ticket_type_id.code] += 1
                _logger.info("rec.ticket_type_id.code: %s | open_count[rec.ticket_type_id]: %s",
                             rec.ticket_type_id.code,
                             open_count[rec.ticket_type_id.code])

        # Log counts
        _logger.info("===== Ticket Counts by Type =====")
        _logger.info("Open Tickets:")
        for ttype, count in open_count.items():
            _logger.info("Type: %s | Count: %s", ttype, count)

        _logger.info("Closed Tickets:")
        for ttype, count in closed_count.items():
            _logger.info("Type: %s | Count: %s", ttype, count)

    # Calculate processing durations for manager, IT manager, and IT team
    @api.depends(
        'submitted_date',
        'manager_approval_date',
        'it_approval_date',
        'done_date'
    )
    def _compute_processing_days(self):
        for rec in self:
            rec.manager_processing_days = (
                (rec.manager_approval_date - rec.submitted_date).total_seconds() / 86400
                if rec.submitted_date and rec.manager_approval_date else 0.0
            )

            rec.it_processing_days = (
                (rec.it_approval_date - rec.manager_approval_date).total_seconds() / 86400
                if rec.manager_approval_date and rec.it_approval_date else 0.0
            )

            rec.it_team_processing_days = (
                (rec.done_date - rec.it_approval_date).total_seconds() / 86400
                if rec.it_approval_date and rec.done_date else 0.0
            )

    # Resolve and assign line manager user from employee hierarchy
    @api.depends('employee_id')
    def _compute_show_line_manager(self):
        for ticket in self:
            _logger.info("Ticket: %s | Employee: %s", ticket.id,
                         ticket.employee_id.name if ticket.employee_id else None)
            if ticket.employee_id and ticket.employee_id.parent_id:
                manager_email = ticket.employee_id.parent_id.work_email
                _logger.info("Line Manager Email: %s", manager_email)
                if manager_email:
                    user = self.env['res.users'].search([('email', '=', manager_email)], limit=1)
                    if user:
                        _logger.info("Found user: %s | ID: %s", user.name, user.id)
                        ticket.line_manager_user_id = user.id
                    else:
                        _logger.warning("No user found with email: %s", manager_email)
                        ticket.line_manager_user_id = False
                else:
                    _logger.warning("Line manager has no email")
                    ticket.line_manager_user_id = False
            else:
                _logger.info("No employee or parent (line manager) for ticket")
                ticket.line_manager_user_id = False

    # Identify if current user is line manager or IT manager
    @api.depends('line_manager_id')
    def _compute_user_roles(self):
        for rec in self:
            # 🔍 DEBUG LOG
            _logger.info(
                "line_manager_id.user_id: %s | self.env.user: %s | rec.line_manager_id: %s",
                rec.line_manager_id.user_id,
                self.env.user,
                rec.line_manager_id,
            )
            rec.is_line_manager = (
                rec.line_manager_id == self.env.user
                if rec.line_manager_id
                else False
            )

            rec.is_it_manager = self.env.user.has_group(
                'ticketing_it.group_it_manager'
            )

            # 🔍 DEBUG LOG
            _logger.info(
                "Ticket: %s | User: %s | is_line_manager: %s | is_it_manager: %s",
                rec.name,
                self.env.user.name,
                rec.is_line_manager,
                rec.is_it_manager
            )

    # Control visibility of ticket for IT manager based on state
    @api.depends('state')
    def _compute_show_to_it_manager(self):
        for ticket in self:
            ticket.show_it_manager = ticket.state not in ['draft', 'manager_approval']
            # DEBUG LOGGING
            _logger.info("Ticket ID: %s | State: %s | Visible to IT Manager: %s",
                         ticket.id, ticket.state, ticket.show_it_manager)

    # Control visibility of ticket for IT team based on state
    @api.depends('state')
    def _compute_show_to_it_team(self):
        for ticket in self:
            ticket.show_it_teams = ticket.state in ['assigned', 'done']
            _logger.info("Ticket ID: %s | State: %s | Visible to IT team: %s",
                         ticket.id, ticket.state, ticket.show_it_teams)

    # Compute list of users allowed for IT assignment
    @api.depends()
    def _compute_allowed_it_users(self):
        it_team_group = self.env.ref("ticketing_it.group_it_team")
        for ticket in self:
            ticket.allowed_it_users = it_team_group.user_ids

    # Fetch default sender email dynamically from system configuration
    def _get_from_email(self):
        """
        Get central FROM email from Odoo settings.
        Admin sets once in Settings → General Settings → Default From Email.
        Never hardcoded in code.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        default_from = ICP.get_param('mail.default.from')
        catchall_domain = ICP.get_param('mail.catchall.domain')

        if default_from:
            if catchall_domain and '@' not in default_from:
                return '{}@{}'.format(default_from, catchall_domain)
            return default_from

        company_email = self.env.company.email
        if company_email:
            return company_email

        return False

    # =========================================================
    # HELPER: FIND IT MANAGER VIA SQL
    # Uses raw SQL on res_groups_users_rel table.
    # This is the ONLY reliable method in all Odoo 17 versions.
    # groups_id domain search is broken in this Odoo build.
    # Admin assigns IT Manager in Settings → Users → Groups button.
    # No names or emails hardcoded anywhere.
    # =========================================================
    # Retrieve IT manager using direct SQL query on group-user relation
    def _find_it_manager(self):
        """
        Find IT Manager user via direct SQL on the groups-users relation table.
        Works in all Odoo 17 versions — avoids the broken groups_id domain search.
        """
        it_manager_group = self.env.ref(
            'ticketing_it.group_it_manager',
            raise_if_not_found=False
        )
        if not it_manager_group:
            _logger.error(
                "IT Manager group 'ticketing_it.group_it_manager' not found. "
                "Check security/security.xml in your module."
            )
            return False

        # Direct SQL — bypasses the broken domain search entirely
        self.env.cr.execute("""
            SELECT ru.id
            FROM res_users ru
            JOIN res_groups_users_rel rel ON rel.uid = ru.id
            WHERE rel.gid = %s
              AND ru.active = true
              AND ru.share = false
            ORDER BY ru.id
            LIMIT 1
        """, (it_manager_group.id,))

        row = self.env.cr.fetchone()
        if row:
            user = self.env['res.users'].sudo().browse(row[0])
            _logger.info(
                "IT Manager found via SQL: %s | Email: %s",
                user.name, user.email
            )
            return user

        _logger.warning(
            "No IT Manager found in group. "
            "Go to Settings → Users → [your IT manager user] → "
            "Groups button → Add 'IT Manager' group."
        )
        return False

    # =========================================================
    # DISPLAY NAME
    # =========================================================
    # Customize display name combining ticket number and subject
    def _compute_display_name(self):
        """Odoo 17+ uses _compute_display_name instead of name_get"""
        for record in self:
            name = record.name or 'New'
            if record.subject:
                record.display_name = f"{name} - {record.subject}"
            else:
                record.display_name = name

    # =========================================================
    # DEFAULT EMPLOYEE
    # =========================================================
    # Get employee record linked to current logged-in user
    def _get_current_employee(self):
        """Get current user's employee record"""
        return self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)],
            limit=1
        )


    # Compute line manager from employee's parent hierarchy
    @api.depends('employee_id', 'employee_id.parent_id', 'employee_id.parent_id.user_id')
    def _compute_line_manager(self):
        """Compute line manager from employee's parent"""
        for rec in self:
            if rec.employee_id and rec.employee_id.parent_id and rec.employee_id.parent_id.user_id:
                rec.line_manager_id = rec.employee_id.parent_id.user_id
            else:
                rec.line_manager_id = False

    # Assign IT manager using SQL-based lookup helper
    @api.depends('department_id')
    def _compute_it_manager(self):
        """
        Get IT Manager via SQL — safe for all Odoo 17 versions.
        groups_id domain search is broken in this Odoo build, so we use SQL.
        """
        it_manager = self._find_it_manager()
        for rec in self:
            rec.it_manager_id = it_manager if it_manager else False

    # =========================================================
    # CREATE (AUTO-SUBMIT FOR PORTAL USERS)
    # =========================================================
    # Override create to assign sequence, set workflow state, and trigger emails
    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            _logger.info('Entered ticket creation: %s', vals)
            # Sequence
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code('it.ticket') or _("New")
                _logger.info(vals['name'])
            ticket_type_id = vals.get('ticket_type_id')
            workflow_level = self._get_workflow_level(ticket_type_id)
            # category_manager = self._get_category_manager(ticket_type_id)

            # Workflow Logic (ONLY VALUES HERE)
            if workflow_level == '0':
                it_team = self.env.ref('ticketing_it.group_it_team')
                user = it_team.user_ids[:1]

                vals.update({
                    'state': 'assigned',
                    'assigned_to_id': user.id if user else False,
                    'submitted_date': fields.Datetime.now(),
                    'workflow_level': workflow_level,
                })

            elif workflow_level == '1':
                vals.update({
                    'state': 'it_approval',
                    'submitted_date': fields.Datetime.now(),
                    'workflow_level': workflow_level,
                })

            elif workflow_level == '2':
                vals.update({
                    'state': 'manager_approval',
                    'submitted_date': fields.Datetime.now(),
                    'workflow_level': workflow_level,
                })

            # elif workflow_level in ['3', '4']:
            #     vals.update({
            #         'state': 'category_manager_approval',
            #         # 'category_manager_id': category_manager.id if category_manager else False,
            #         'submitted_date': fields.Datetime.now(),
            #     })

        # ✅ CREATE RECORDS FIRST
        records = super().create(vals_list)

        # ✅ NOW DO EMAILS + ACTIVITIES
        for rec in records:

            workflow_level = self._get_workflow_level(rec.ticket_type_id.id)

            # Workflow 0
            if workflow_level == '0':
                template = self.env.ref('ticketing_it.email_template_it_assigned', False)
                if template:
                    template.send_mail(rec.id, force_send=True, email_values={
                            'email_to': rec.employee_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })


            # Workflow 1 → IT Manager
            elif workflow_level == '1':
                template = self.env.ref('ticketing_it.email_template_it_approval', False)
                if template:
                    template.send_mail(rec.id, force_send=True, email_values={
                            'email_to': rec.it_manager_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })



            # Workflow 2 → Line Manager
            elif workflow_level == '2':
                template = self.env.ref('ticketing_it.email_template_manager_approval', False)
                if template:
                    template.send_mail(rec.id, force_send=True, email_values={
                            'email_to': rec.line_manager_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })



            # Workflow 3/4 → Category Manager
            # elif workflow_level in ['3', '4']:
            #     template = self.env.ref('ticketing_it.email_template_category_manager_approval', False)
            #     if template:
            #         template.send_mail(rec.id, force_send=True, email_values={
            #                 'email_to': rec.category_manager_id.email,
            #                 'recipient_ids': [(5, 0, 0)],
            #                 'partner_ids': [(5, 0, 0)],
            #             })


                # ---------------------------
                # Social Media Duration (FIXED)
                # ---------------------------
            if rec.ticket_type_id.code == 'social_media':
                duration = self.env['ir.config_parameter'].sudo().get_param(
                    'it_ticket.social_media_duration', '3m'
                )
                rec.duration = duration
        return records

    # Fetch workflow level configuration for a given ticket type
    def _get_workflow_level(self, ticket_type_id):

        config = self.env['it.ticket.workflow.config'].search(
            [('ticket_type_id', '=', ticket_type_id)],
            limit=1
        )

        if config:
            return config.workflow_level

        return '0'

    # def _get_category_manager(self, ticket_type_id):
    #
    #     config = self.env['it.ticket.workflow.config'].search(
    #         [('ticket_type_id', '=', ticket_type_id)],
    #         limit=1
    #     )
    #
    #     if config:
    #         return config.category_manager_id
    #
    #     return 'null'




    # =========================================================
    # WORKFLOW METHODS - APPROVE/REJECT
    # =========================================================
    # Submit ticket and route it based on configured workflow
    def action_submit(self):
        _logger.info("Submitting IT Ticket")

        for rec in self:

            config = self.env['it.ticket.workflow.config'].search(
                [('ticket_type_id', '=', rec.ticket_type_id.id)],
                limit=1
            )

            workflow = config.workflow_level if config else '2'

            # Workflow 0 → Direct to IT team
            if workflow == '0':

                it_team = self.env.ref('ticketing_it.group_it_team')

                first_user = False
                if it_team and it_team.user_ids:
                    first_user = it_team.user_ids[0]

                rec.write({
                    'state': 'assigned',
                    'assigned_to_id': first_user.id if first_user else False,
                    'submitted_date': fields.Datetime.now()
                })
                template = self.env.ref(
                    'ticketing_it.email_template_it_assigned',
                    raise_if_not_found=False
                )
                if template:
                    template.send_mail(rec.id, force_send=True, email_values={
                            'email_to': rec.employee_id.user_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })
                return

            # Workflow 1 → IT Manager
            elif workflow == '1':

                if not rec.it_manager_id:
                    raise ValidationError(_("No IT Manager configured"))

                rec.write({
                    'state': 'it_approval',
                    'submitted_date': fields.Datetime.now()
                })
                template = self.env.ref(
                    'ticketing_it.email_template_it_approval',
                    raise_if_not_found=False
                )
                if template:
                    template.send_mail(rec.id, force_send=True)
                    _logger.info(
                        "IT approval email sent to %s (%s) for ticket %s",
                        rec.it_manager_id.name,
                        rec.it_manager_id.email,
                        rec.name
                    )

            # Workflow 2 → Line Manager
            elif workflow == '2':

                if not rec.line_manager_id:
                    raise ValidationError(_("No line manager found"))

                rec.write({
                    'state': 'manager_approval',
                    'submitted_date': fields.Datetime.now()
                })
                template = self.env.ref(
                    'ticketing_it.email_template_manager_approval',
                    raise_if_not_found=False
                )
                if template:
                    template.send_mail(rec.id, force_send=True)

    # Open approval wizard for line manager
    def action_manager_approve(self):
        self.ensure_one()
        if self.env.user != self.line_manager_id:
            _logger.info("self.line_manager_id: %s | self.env.user: %s | self.line_manager_id.user_id: %s",
                         self.line_manager_id, self.env.user, self.line_manager_id.user_id)
            raise UserError(
                _("Only the line manager (%s) can approve this ticket") % self.line_manager_id.name
            )
        return {
            'name': _('Approve Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'it.ticket.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id}
        }

    # def action_category_manager_approve(self):
    #     self.ensure_one()
    #     if self.env.user != self.category_manager_id:
    #         _logger.info("self.category_manager_id: %s | self.env.user: %s | self.category_manager_id.user_id: %s",
    #                      self.category_manager_id, self.env.user, self.category_manager_id.user_id)
    #         raise UserError(
    #             _("Only the Category manager (%s) can approve this ticket") % self.category_manager_id.name
    #         )
    #     return {
    #         'name': _('Approve Ticket'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'it.ticket.approve.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {'default_ticket_id': self.id}
    #     }

    # Open approval wizard for IT manager
    def action_it_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('ticketing_it.group_it_manager'):
            raise UserError(_("Only IT managers can approve this ticket"))
        return {
            'name': _('Approve Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'it.ticket.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id}
        }

    # Open rejection wizard with reason input
    def action_reject(self):
        """Open wizard to reject ticket with reason."""
        self.ensure_one()
        self._check_reject_access()

        return {
            'name': _('Reject Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'it.ticket.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id}
        }

    # Validate if current user has permission to reject ticket
    def _check_reject_access(self):
        """Verify the current user is allowed to reject this ticket."""
        self.ensure_one()
        user = self.env.user

        if self.state == 'manager_approval':
            if user != self.line_manager_id:
                raise UserError(
                    _("Only the line manager (%s) can reject this ticket.")
                    % (self.line_manager_id.name or _('unassigned'))
                )
        elif self.state == 'it_approval':
            if not user.has_group('ticketing_it.group_it_manager'):
                raise UserError(_("Only IT managers can reject this ticket."))
        else:
            raise UserError(
                _("This ticket cannot be rejected in its current state (%s).")
                % dict(self._fields['state'].selection).get(self.state, self.state)
            )

    # Apply rejection state and notify user with reason
    def do_reject(self, reason):
        """Actually reject the ticket (called from wizard)."""
        for rec in self:
            rec._check_reject_access()

            rec.sudo().write({
                'state': 'rejected',
                'rejection_reason': reason,
                'rejected_by_id': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
            })

            rec.activity_unlink(['mail.mail_activity_data_todo'])

            template = self.env.ref(
                'ticketing_it.email_template_rejection',
                raise_if_not_found=False
            )
            if template:
                template.send_mail(rec.id, force_send=True, email_values={
                            'email_to': rec.employee_id.user_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })

            rec.message_post(
                body=_("Ticket rejected by %s<br/>Reason: %s") % (self.env.user.name, reason)
            )

    # =========================================================
    # IT TEAM WORKFLOW
    # =========================================================
    # Mark ticket as in progress by assigned user
    def action_start_work(self):
        for rec in self:
            if rec.assigned_to_id != self.env.user:
                raise UserError(_("This ticket is not assigned to you."))

            rec.state = 'in_progress'
            rec.sudo().message_post(
                body=_("Work started by %s") % self.env.user.name
            )

    # Mark ticket as completed and trigger completion logic and emails
    def action_done(self):
        """Mark ticket as done"""
        _logger.info("Entered into done action")
        for rec in self:
            rec.state = 'done'
            rec.done_date = fields.Datetime.now()
            _logger.info("rec.done_date: %s", rec.done_date)
            # ✅ Start access duration for social media tickets
            if rec.ticket_type_id.code == 'social_media' and rec.duration:

                start_date = rec.done_date
                rec.access_start_date = start_date

                _logger.info("start_date: %s", start_date)

                # FIXED: months instead of minutes
                if rec.duration == '3m':
                    rec.access_finish_date = start_date + relativedelta(months=3)

                elif rec.duration == '6m':
                    rec.access_finish_date = start_date + relativedelta(months=6)

                elif rec.duration == '12m':
                    rec.access_finish_date = start_date + relativedelta(years=1)

                elif rec.duration == 'custom':
                    # IMPORTANT: use actual field user filled
                    rec.access_finish_date = rec.custom_expiry_date

            _logger.info("rec.access_finish_date: %s", rec.access_finish_date)
            template = self.env.ref(
                'ticketing_it.email_template_done',
                raise_if_not_found=False
            )

            if template:
                template.send_mail(rec.id, force_send=True, email_values={
                            'email_to': rec.employee_id.user_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })

            rec.message_post(
                body=_("Ticket completed by %s and employee notified") % self.env.user.name
            )
        _logger.info("Ending into done action")

    # =========================================================
    # PORTAL ACCESS URL
    # =========================================================
    # Generate portal URL for ticket access
    def _compute_access_url(self):
        """Portal URL for employees to view their tickets"""
        super()._compute_access_url()
        for ticket in self:
            ticket.access_url = '/my/tickets/%s' % ticket.id


    # Compute month-year label when ticket is completed
    @api.depends('done_date')
    def _compute_month_solved(self):
        for rec in self:
            if rec.done_date:
                rec.month_solved = rec.done_date.strftime('%B %Y')
            else:
                rec.month_solved = 'N/A'

    # Override write to enforce assignment security and track state change dates
    # ===== HARD SECURITY =====
    def write(self, vals):

        # ----------------------------
        # ASSIGNMENT SECURITY
        # ----------------------------
        if 'assigned_to_id' in vals:
            # if not (
            #         self.env.user.has_group('ticketing_it.group_it_manager') or
            #         self.env.user.has_group('ticketing_it.group_category_manager')
            # ):
            if not (
                    self.env.user.has_group('ticketing_it.group_it_manager')
            ):

                raise AccessError("Only IT Manager can assign tickets.")

        # ----------------------------
        # STATE CHANGE DATE TRACKING
        # ----------------------------
        if 'state' in vals:
            new_state = vals.get('state')
            now = fields.Datetime.now()

            for record in self:
                # If moving to manager approval
                if new_state == 'manager_approval' and record.state != 'manager_approval':
                    vals['manager_approval_date'] = now
                    _logger.info(vals['manager_approval_date'])

                # If moving to IT approval
                if new_state == 'it_approval' and record.state != 'it_approval':
                    vals['it_approval_date'] = now
                    _logger.info(vals['it_approval_date'])

        return super().write(vals)

    # Open configuration wizard for reminder settings
    def open_reminder_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.reminder.config.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    # Cron job to send approval reminders based on ticket state and delay
    def action_send_dynamic_reminder(self):
        _logger.info("===== CRON STARTED: IT Ticket Reminder =====")

        ICP = self.env['ir.config_parameter'].sudo()
        reminder_days = int(ICP.get_param('ticketing_it.reminder_days', 1))
        _logger.info("Reminder days: %s", reminder_days)

        now = fields.Date.today()
        _logger.info("Current datetime: %s", now)

        # tickets = self.search([
        #     ('state', 'in', ['manager_approval', 'it_approval', 'category_manager_approval'])
        # ])
        tickets = self.search([
            ('state', 'in', ['manager_approval', 'it_approval'])
        ])
        _logger.info("Total tickets fetched: %s", len(tickets))

        user_ticket_map = defaultdict(list)

        # -----------------------------
        # GROUP TICKETS PER USER
        # -----------------------------
        for ticket in tickets:
            _logger.info("---- Checking Ticket: %s ----", ticket.name)
            _logger.info("State: %s", ticket.state)

            workflow_level = ticket.workflow_level
            _logger.info("Workflow level: %s", workflow_level)

            state_date = False
            user = False

            # -----------------------------
            # WORKFLOW LOGIC
            # -----------------------------
            if workflow_level == '1':
                if ticket.state == 'it_approval':
                    state_date = ticket.submitted_date
                    user = ticket.it_manager_id

            elif workflow_level == '2':
                if ticket.state == 'manager_approval':
                    state_date = ticket.submitted_date
                    user = ticket.line_manager_id

                elif ticket.state == 'it_approval':
                    state_date = ticket.manager_approval_date
                    user = ticket.it_manager_id

            # elif workflow_level == '3':
            #     if ticket.state == 'category_manager_approval':
            #         state_date = ticket.submitted_date
            #         user = ticket.category_manager_id
            #
            # elif workflow_level == '4':
            #     if ticket.state == 'category_manager_approval':
            #         state_date = ticket.submitted_date
            #         user = ticket.category_manager_id
            #
            #     elif ticket.state == 'it_approval':
            #         state_date = ticket.category_manager_approval_date
            #         user = ticket.it_manager_id

            else:
                _logger.warning("Skipping: Unknown workflow level")
                continue

            # -----------------------------
            # VALIDATION
            # -----------------------------
            if not state_date:
                _logger.warning("Skipping: No state_date")
                continue

            if not user:
                _logger.warning("Skipping: No user assigned")
                continue

            _logger.info("State date: %s | User: %s", state_date, user.name)

            # -----------------------------
            # CALCULATE DAYS
            # -----------------------------
            days_in_state = (now - state_date).days
            _logger.info("Days in current state: %s", days_in_state)

            if days_in_state < reminder_days:
                _logger.info("Skipping: Not enough days passed")
                continue

            # -----------------------------
            # CHECK LAST REMINDER
            # -----------------------------
            if ticket.last_reminder_sent:
                _logger.info("now: %s ticket.last_reminder_sent:%s", now, ticket.last_reminder_sent)
                days_since_last = (now - ticket.last_reminder_sent).days
                _logger.info("Days since last reminder: %s", days_since_last)

                if days_since_last < reminder_days:
                    _logger.info("Skipping: Reminder already sent recently")
                    continue
            if ticket.submitted_date:
                days_since_last = (now - ticket.submitted_date).days
                _logger.info("Days since submitted date: %s", days_since_last)

                if days_since_last < reminder_days:
                    _logger.info("Skipping: Reminder already sent recently")
                    continue
            _logger.info("Adding ticket to user: %s", user.name)

            user_ticket_map[user].append(ticket)

        _logger.info("Total users to notify: %s", len(user_ticket_map))

        # -----------------------------
        # SEND EMAIL USING TEMPLATE
        # -----------------------------
        template = self.env.ref('ticketing_it.email_template_approval_reminder', False)

        if not template:
            _logger.error("Reminder template not found!")
            return

        for user, user_tickets_list in user_ticket_map.items():
            user_tickets = self.browse([t.id for t in user_tickets_list])  # FIX

            _logger.info("Sending email to: %s (%s tickets)", user.name, len(user_tickets))

            try:
                template.with_context(
                    approver_name=user.name,
                    tickets=user_tickets,
                    ticket_ids=user_tickets.ids
                ).send_mail(
                    user_tickets[0].id,
                    force_send=True,
                    email_values={
                        'email_to': user.partner_id.email,
                        'recipient_ids': [(5, 0, 0)],
                        'partner_ids': [(5, 0, 0)],
                    }
                )

                _logger.info("Email sent successfully to %s", user.name)

            except Exception as e:
                _logger.error("Failed to send email to %s: %s", user.name, str(e))
                continue

            # -----------------------------
            # UPDATE TRACKING
            # -----------------------------
            for ticket in user_tickets:
                ticket.sudo().write({
                    'last_reminder_sent': now
                })

                ticket.message_post(
                    body=_("Consolidated reminder sent to %s") % user.name
                )

        _logger.info("===== CRON FINISHED =====")

    # Cron job to notify users when social media access expires
    def check_social_media_expiry(self):
        _logger.info("===== CRON STARTED: Social Media Expiry Reminder =====")
        now = fields.Date.today()

        # Find tickets whose access just expired
        tickets = self.search([
            ('access_finish_date', '=', now)
        ])
        _logger.info("Total tickets expiring in last day: %s", len(tickets))

        for ticket in tickets:
            try:
                _logger.info("Processing Ticket: %s", ticket.name)

                # Assignee email
                if ticket.assigned_to_id and ticket.assigned_to_id.email:
                    template = self.env.ref('ticketing_it.email_template_access_end_assignee', False)
                    if template:
                        template.send_mail(ticket.id, force_send=True, email_values={
                            'email_to': ticket.assigned_to_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })

                # Employee email
                if ticket.employee_id and ticket.employee_id.user_id and ticket.employee_id.email:
                    template = self.env.ref('ticketing_it.email_template_access_end_employee', False)
                    if template:
                        template.send_mail(ticket.id, force_send=True, email_values={
                            'email_to': ticket.employee_id.email,
                            'recipient_ids': [(5, 0, 0)],
                            'partner_ids': [(5, 0, 0)],
                        })

            except Exception as e:
                _logger.error("Error processing ticket %s: %s", ticket.id, str(e))

        _logger.info("===== CRON FINISHED =====")


class ITTicketWorkflowConfig(models.Model):
    # Model to configure workflow levels for each ticket type
    _name = 'it.ticket.workflow.config'
    _description = 'Ticket Workflow Configuration'
    _rec_name = 'ticket_type_id'

    ticket_type_id = fields.Many2one(
        'it.ticket.type',
        string='Ticket Type Id',
        required=True,
        domain="[('id', 'not in', existing_ticket_type_ids)]"
    )

    workflow_level = fields.Selection([
        ('0', '0 - Direct to IT Support'),
        ('1', '1 - IT Manager → IT Support'),
        ('2', '2 - Line Manager → IT Manager → IT Support'),
        # ('3', '3 - Category Manager → IT Support'),
        # ('4', '4 - Category Manager → IT Manager → IT Support')
    ], default='2', required=True)
    existing_ticket_type_ids = fields.Many2many(
        'it.ticket.type',
        compute='_compute_existing_ticket_types'
    )
    # category_manager_id = fields.Many2one(
    #     'res.users',
    #     string="Category Manager"
    # )
    # allowed_category_managers = fields.Many2many(
    #     "res.users", compute="_compute_allowed_category_managers"
    # )
    _sql_constraints = [
        ('unique_ticket_type_id', 'unique(ticket_type_id)', 'Workflow already defined for this ticket type!')
    ]

    # @api.depends()
    # def _compute_allowed_category_managers(self):
    #     it_category_manager_group = self.env.ref("ticketing_it.group_category_manager")
    #     for ticket in self:
    #         ticket.allowed_category_managers = it_category_manager_group.user_ids

    # Ensure only one workflow configuration exists per ticket type
    @api.constrains('ticket_type_id')
    def _check_unique_ticket_type(self):
        for rec in self:
            existing = self.search([
                ('ticket_type_id', '=', rec.ticket_type_id.id),
                ('id', '!=', rec.id)
            ])
            if existing:
                raise ValidationError(
                    "Workflow already exists for this ticket type!"
                )

    # Compute list of ticket types already configured to prevent duplicates
    @api.depends()
    def _compute_existing_ticket_types(self):
        all_configs = self.search([]).mapped('ticket_type_id')

        for rec in self:
            rec.existing_ticket_type_ids = all_configs
