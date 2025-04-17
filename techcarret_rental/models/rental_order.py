# -*- coding: utf-8 -*-
import pytz
from pytz import timezone, UTC
from math import ceil
from dateutil.relativedelta import relativedelta
from setuptools.dist import sequence

from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.fields import Command
from odoo.tools import format_datetime, format_time, date_utils
from pytz import timezone, UTC
from odoo.exceptions import UserError

class TecprojectType(models.Model):
    _name = 'tecproject.type'

    name = fields.Char('Name', copy=False, required=True)

    _sql_constraints = [('unique_tecproject', 'unique (name)', 'Name must be unique.')]

class ProductTemplate(models.Model):
    _inherit = "product.template"

    employee_id = fields.Many2one('hr.employee', 'Employee')

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if self.employee_id:
            self.employee_id.name = self.name
        return res

class Rentals(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        company = self.env.company
        if company.r_analytic_plan_id:
            defaults['r_analytic_plan_id'] = company.r_analytic_plan_id.id
        if company.r_analytic_sub_plan_id:
            defaults['r_analytic_sub_plan_id'] = company.r_analytic_sub_plan_id.id
        if company.s_analytic_plan_id:
            defaults['s_analytic_plan_id'] = company.s_analytic_plan_id.id
        if company.s_analytic_sub_plan_id:
            defaults['s_analytic_sub_plan_id'] = company.s_analytic_sub_plan_id.id
        if company.ss_analytic_plan_id:
            defaults['ss_analytic_plan_id'] = company.ss_analytic_plan_id.id
        if company.ss_analytic_sub_plan_id:
            defaults['ss_analytic_sub_plan_id'] = company.ss_analytic_sub_plan_id.id

        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)
        now_dt = now_dt.replace(hour=00, minute=00, second=1)
        now_dt = now_dt - relativedelta(hours=5)
        now_dt = now_dt - relativedelta(minutes=30)
        defaults['rental_start_date'] = now_dt

        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)
        now_dt = now_dt.replace(hour=23, minute=59, second=59)
        now_dt = now_dt - relativedelta(hours=5)
        now_dt = now_dt - relativedelta(minutes=30)
        defaults['rental_return_date'] =now_dt
        return defaults

    def _default_freequency(self):
        return self.env['sale.temporal.recurrence'].search([('unit', '=', 'month')], limit=1).id

    invoice_freequency = fields.Many2one('sale.temporal.recurrence', string='Invoicing Frequency', default=_default_freequency)
    rental_inv_line_ids = fields.One2many(
        comodel_name='rental.invoice.history',
        inverse_name='rental_sale_id',
        string="Rental History",
        copy=True, auto_join=True)
    rentalfirst_invoice_date = fields.Date(string='First Invoice Date', default=fields.Date.context_today)
    rentalnext_invoice_date = fields.Date(string='Next Invoice Date', copy=False)
    recurring_period_interval = fields.Selection([
        ('hour', 'Hours'),
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='month')
    do_create_invoice_schedule = fields.Boolean(string="Dummy Compute", compute='_do_create_invoice_schedule')
    practice_id = fields.Many2one('employee.practice', 'Practice', copy=False)
    project_type_id = fields.Many2one('tecproject.type', 'Project type')
    project_code = fields.Char('Project Code', copy=False)
    is_tec_subscription = fields.Boolean("Is Subscription", default=False)
    r_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', readonly=False, domain="[('parent_id', '=', False)]")
    r_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', readonly=False, domain="[('parent_id', '=', r_analytic_plan_id)]")
    s_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', readonly=False, domain="[('parent_id', '=', False)]")
    s_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', readonly=False, domain="[('parent_id', '=', s_analytic_plan_id)]")
    ss_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', readonly=False, domain="[('parent_id', '=', False)]")
    ss_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', readonly=False, domain="[('parent_id', '=', ss_analytic_plan_id)]")
    has_recurring_line = fields.Boolean(compute='_compute_has_recurring_line')

    _sql_constraints = [
        ('date_order_conditional_required',
         "CHECK((state = 'sale' AND date_order IS NOT NULL) OR state != 'sale')",
         "A confirmed sales order requires a confirmation date."),
        ('so_project_code_unique', 'UNIQUE(project_code)', 'The project code must be unique')
    ]

    @api.depends('order_line.price_unit')
    def _do_create_invoice_schedule(self):
        for order in self:
            # for order_line in order.order_line:
            #     if order_line.product_uom.name == 'Hours':
            #         order_line.product_uom_qty = order.duration_days * 8
            #     else:
            #         order_line.product_uom_qty = order.duration_days
            #     if order_line.product_id.product_pricing_ids:
            #         for product_pricing_id in order_line.product_id.product_pricing_ids:
            #             if order_line.product_uom.name == 'Hours' and product_pricing_id.recurrence_id.unit == 'hour':
            #                 order_line.price_unit= product_pricing_id.price
            #             elif order_line.product_uom.name == 'Days'and product_pricing_id.recurrence_id.unit == 'day':
            #                 order_line.price_unit=product_pricing_id.price
            #             elif order_line.product_uom.name == 'Week'and product_pricing_id.recurrence_id.unit == 'week':
            #                 order_line.price_unit=product_pricing_id.price
            #             elif order_line.product_uom.name == 'Months'and product_pricing_id.recurrence_id.unit == 'month':
            #                 order_line.price_unit=product_pricing_id.price
            #             elif order_line.product_uom.name == 'Years' and product_pricing_id.recurrence_id.unit == 'year':
            #                 order_line.price_unit=product_pricing_id.price
            #     else:
            #         if order_line.price_unit==0.00:
            #             order_line.price_unit = order_line.product_id.with_company(order_line.company_id.id).lst_price or 0.00
            order.do_create_invoice_schedule=True

    @api.depends('order_line', 'order_line.recurring_invoice')
    def _compute_has_recurring_line(self):
        recurring_product_orders = self.order_line.filtered(lambda l: l.product_id.recurring_invoice).order_id
        recurring_product_orders.has_recurring_line = True
        (self - recurring_product_orders).has_recurring_line = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Rentals, self).create(vals_list)
        for so in res:
            tag_ids=[]
            for tag in so.tag_ids:
                tag_ids.append(tag.id)
            if so.is_subscription == True:
                tag_obj = self.env['crm.tag'].search([('name', '=', 'Subscription')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'Subscription'})
                tag_ids.append(tag_obj.id)
            elif so.is_rental_order == True:
                tag_obj = self.env['crm.tag'].search([('name', '=', 'HR')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'HR'})
                tag_ids.append(tag_obj.id)
            else:
                tag_obj = self.env['crm.tag'].search([('name', '=', 'Project')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'Project'})
                tag_ids.append(tag_obj.id)
            if tag_ids:
                so.tag_ids = [(6, 0, tag_ids)]
        return res

    def write(self, vals):
        for line in self:
            tag_ids=[]
            is_subscription=False
            if 'is_subscription' in vals:
                if vals.get('is_subscription') == True:
                    is_subscription=True
            elif line.is_subscription == True:
                is_subscription=True
            if is_subscription == True:
                for tag in line.tag_ids:
                    if tag.name not in['Project', 'HR']:
                        tag_ids.append(tag.id)
                tag_obj = self.env['crm.tag'].search([('name', '=', 'Subscription')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'Subscription'})
                tag_ids.append(tag_obj.id)
                if tag_ids:
                    vals.update({'tag_ids': [(6, 0, tag_ids)]})
        res = super(Rentals, self).write(vals)
        return res

    @api.depends('rental_start_date', 'rental_return_date')
    def _compute_duration(self):
        self.duration_days = 0
        self.remaining_hours = 0
        for order in self:
            planned_days=0
            if order.rental_start_date and order.rental_return_date:
                duration = order.rental_return_date - order.rental_start_date
                remaining_hours = ceil(duration.seconds / 3600)
                employee = ''
                count = 0
                for order_line in order.rental_inv_line_ids:
                    if count==0:
                            if order_line.employee_id:
                                if order_line.employee_id.resource_calendar_id:
                                    employee = order_line.employee_id.id
                                    count = count + 1
                for order_line in order.rental_inv_line_ids:
                    if employee == order_line.employee_id.id:
                        if order_line.uom == 'days':
                            planned_days = planned_days + order_line.planned_days
                        else:
                            days=order_line.planned_days/8
                            planned_days = planned_days + days
                if order.is_rental_order == True:
                    if planned_days>0:
                        order.duration_days = planned_days
                    else:
                        if remaining_hours>12:
                            order.duration_days = duration.days + 1
                        else:
                            order.duration_days = duration.days
                order.remaining_hours = 0

    @api.onchange('rental_start_date')
    def _onchange_finvoice(self):
        if self.invoice_freequency:
            rental_start_date = self.rental_start_date + relativedelta(hours=7)
            next_invoice_date = rental_start_date + relativedelta(months=1)
        else:
            next_invoice_date = self.rental_start_date
        self.rentalfirst_invoice_date=next_invoice_date

    @api.onchange('r_analytic_plan_id','s_analytic_plan_id','ss_analytic_plan_id')
    def _onchange_set_aa1(self):
        for sale in self:
            if sale.order_line:
                sale.r_analytic_sub_plan_id=''
                sale.s_analytic_sub_plan_id=''
                sale.ss_analytic_sub_plan_id=''
                for o_line in sale.order_line:
                    o_line.analytic_distribution=False

    @api.onchange('order_line','r_analytic_plan_id','r_analytic_sub_plan_id','s_analytic_plan_id','s_analytic_sub_plan_id','ss_analytic_plan_id','ss_analytic_sub_plan_id','project_code','project_type_id','practice_id')
    def _onchange_set_aa(self):
        for sale in self:
            for o_line in sale.order_line:
                if o_line.product_id:
                    aa_name=''
                    if sale.is_rental_order==True:
                        if o_line.product_id and sale.project_code:
                            aa_name=o_line.product_id.name+'/'+sale.project_code
                    elif sale.is_tec_subscription==True:
                        # PRJ/CLIENTCODE/LC/Practice/SO no.
                        if sale.partner_id and sale.partner_id.customer_code and sale.practice_id and sale.name:
                            aa_name="PRJ/"+str(sale.partner_id.customer_code)+"LC/"+sale.practice_id.name+"/"+sale.name
                    else:
                        # PRJ/CLIENTCODE/PROJECT TYPE/Practice/Project Code
                        if sale.partner_id and sale.partner_id.customer_code and sale.project_type_id and sale.practice_id and sale.name and sale.project_code:
                            aa_name = "PRJ/"+str(sale.partner_id.customer_code)+"/"+str(sale.project_type_id.name)+"/"+str(sale.practice_id.name)+"/"+sale.project_code
                    if aa_name !='':
                        analytic_plan_id=''
                        if sale.r_analytic_sub_plan_id and sale.is_rental_order==True:
                            analytic_plan_id=sale.r_analytic_sub_plan_id
                        elif sale.ss_analytic_sub_plan_id and sale.is_tec_subscription==True:
                            analytic_plan_id=sale.ss_analytic_sub_plan_id
                        elif sale.s_analytic_sub_plan_id:
                            analytic_plan_id=sale.s_analytic_sub_plan_id
                        if analytic_plan_id:
                            aa_objs = self.env['account.analytic.account'].search([('company_id', '=', sale.company_id.id),('plan_id', '=', analytic_plan_id.id),('name', '=', aa_name)], limit=1)
                            if not aa_objs:
                                aa_dict ={aa_objs.id: 100}
                                aa_objs = self.env['account.analytic.account'].create({
                                    'plan_id': analytic_plan_id.id,
                                    'name': aa_name,
                                    'company_id':sale.company_id.id,
                                    'partner_id': sale.partner_id.id,
                                })
                                if aa_objs:
                                    o_line.analytic_distribution=aa_dict
                            else:
                                aa_dict ={aa_objs.id: 100}
                                if o_line.analytic_distribution:
                                    for key, value in o_line.analytic_distribution.items():
                                        aa_dict.update({key:value})
                                o_line.analytic_distribution=aa_dict


    @api.onchange('rental_start_date','rental_return_date')
    def _onchange_rental_dates(self):
        if self.is_rental_order == True:
            for order in self:
                for order_line in order.order_line:
                    if order_line.product_uom.name == 'Hours':
                        order_line.product_uom_qty = order.duration_days * 8
                    else:
                        order_line.product_uom_qty = order.duration_days

    @api.onchange('invoice_freequency', 'rentalfirst_invoice_date','rental_start_date','rental_return_date','order_line')
    def _onchange_inv_freeqency(self):
        if self.is_rental_order == True:
            for order in self:
                for order_line in order.order_line:
                    # if order_line.product_uom.name == 'Hours':
                    #     order_line.product_uom_qty = order.duration_days * 8
                    # else:
                    #     order_line.product_uom_qty = order.duration_days
                    if order_line.product_id.product_pricing_ids:
                        for product_pricing_id in order_line.product_id.product_pricing_ids:
                            if order_line.product_uom.name == 'Hours' and product_pricing_id.recurrence_id.unit == 'hour':
                                order_line.price_unit= product_pricing_id.price
                            elif order_line.product_uom.name == 'Days'and product_pricing_id.recurrence_id.unit == 'day':
                                order_line.price_unit=product_pricing_id.price
                            elif order_line.product_uom.name == 'Week'and product_pricing_id.recurrence_id.unit == 'week':
                                order_line.price_unit=product_pricing_id.price
                            elif order_line.product_uom.name == 'Months'and product_pricing_id.recurrence_id.unit == 'month':
                                order_line.price_unit=product_pricing_id.price
                            elif order_line.product_uom.name == 'Years' and product_pricing_id.recurrence_id.unit == 'year':
                                order_line.price_unit=product_pricing_id.price
                    else:
                        if order_line.price_unit == 0.00:
                            order_line.price_unit = order_line.product_id.with_company(order_line.company_id.id).lst_price or 0.00
                total_working_days=0
                no_working_days=0
                self.rental_inv_line_ids=[(6, 0, [])]
                datetime_min_time = datetime.min.time()
                datetime_max_time = datetime.min.time()
                if order.invoice_freequency.unit == 'hour':
                    order.recurring_period_interval = 'hour'
                elif order.invoice_freequency.unit == 'day':
                    order.recurring_period_interval = 'day'
                elif order.invoice_freequency.unit == 'week':
                    order.recurring_period_interval = 'week'
                elif order.invoice_freequency.unit == 'month':
                    order.recurring_period_interval = 'month'
                elif order.invoice_freequency.unit == 'year':
                    order.recurring_period_interval = 'year'
                if order.rental_start_date and order.rental_return_date and order.rentalfirst_invoice_date:
                    inv_dates=[]
                    emp_id=''
                    for order_line in order.order_line:
                        if order_line.product_id:
                            if order_line.product_id.employee_id:
                                if order_line.product_id.employee_id.resource_calendar_id:
                                    emp_id=order_line.product_id.employee_id.id
                    for order_line in order.order_line:
                        invoice_start_date=order.rental_start_date.date()
                        last_invoiced_date=order.rentalfirst_invoice_date
                        if order_line.product_id and order_line.product_id.employee_id:
                            #FIND NON-WORKING DAYS
                            start_dt = datetime.combine(order.rental_start_date.date(), datetime_min_time)
                            end_dt = datetime.combine(order.rentalfirst_invoice_date, datetime_max_time)
                            if end_dt>order.rental_return_date:
                                end_dt=datetime.combine(order.rental_return_date, datetime_max_time)
                            if order_line.product_id.employee_id:
                                #CREATE FIRST MONTH INVOICE
                                #ALL INVOICE DONE ON MONTHLY
                                planned_worked = order_line.product_id.employee_id._get_work_days_data_batch(start_dt, end_dt, calendar=order_line.product_id.employee_id.resource_calendar_id) \
                                    [order_line.product_id.employee_id.id]['days']
                                total_working_days = total_working_days + planned_worked
                                if planned_worked>0:
                                    uom = 'days'
                                    if order_line.product_uom.name=='Hours':
                                        planned_worked = planned_worked*8
                                        uom = 'hours'
                                    dummy_start_dt = start_dt + relativedelta(days=5)
                                    inv_dates.append((0, 0, {'sale_state':order.state,
                                                             'planned_days':planned_worked,
                                                             'partner_id':order.partner_id.id,
                                                             'employee_id': order_line.product_id.employee_id.id,
                                                             'rentalnext_invoice_date': self.rentalfirst_invoice_date,
                                                             'rentalnext_invoice_date_time':self.rentalfirst_invoice_date,
                                                             'is_ready_to_invoice':True,
                                                             'uom': uom,
                                                             'rental_month':str(dummy_start_dt.month)
                                                             }))
                                    if emp_id == order_line.product_id.employee_id.id:
                                        if order_line.product_uom.name == 'Hours':
                                            planned_worked = planned_worked/8
                                        no_working_days = no_working_days + planned_worked
                                next_invoice_date = order.rentalfirst_invoice_date + relativedelta(months=1)
                                #CREATE BILL FOR UPCOMING MONTHS
                                month_count = 2
                                while next_invoice_date <= order.rental_return_date.date():
                                    upcoming_invoice_date = order.rentalfirst_invoice_date + relativedelta(months=month_count)
                                    start_dt = next_invoice_date - relativedelta(months=1)
                                    end_dt = upcoming_invoice_date - relativedelta(months=1)
                                    if next_invoice_date >= order.rental_return_date.date():
                                        end_dt = order.rental_return_date.date()
                                    start_dt = datetime.combine(start_dt, datetime_min_time)
                                    end_dt = datetime.combine(end_dt, datetime_max_time)
                                    planned_worked = order_line.product_id.employee_id._get_work_days_data_batch(start_dt, end_dt, calendar=order_line.product_id.employee_id.resource_calendar_id) \
                                        [order_line.product_id.employee_id.id]['days']
                                    if planned_worked>0:
                                        uom = 'days'
                                        if order_line.product_uom.name == 'Hours':
                                            planned_worked = planned_worked * 8
                                            uom = 'hours'
                                        dummy_start_dt = start_dt + relativedelta(days=5)
                                        inv_dates.append((0, 0, {'sale_state':order.state,
                                                             'planned_days':planned_worked,
                                                             'partner_id':order.partner_id.id,
                                                             'employee_id': order_line.product_id.employee_id.id,
                                                             'rentalnext_invoice_date':next_invoice_date,
                                                             'rentalnext_invoice_date_time':next_invoice_date,
                                                             'uom': uom,
                                                             'rental_month': str(dummy_start_dt.month)
                                                             }))
                                    month_count = month_count + 1
                                    next_invoice_date = upcoming_invoice_date
                                    total_working_days = total_working_days + planned_worked
                                    if emp_id == order_line.product_id.employee_id.id:
                                        if order_line.product_uom.name == 'Hours':
                                            planned_worked = planned_worked/8
                                        no_working_days = no_working_days + planned_worked
                                #CREATE LAST MONTH INVOICE IF WORKED IN PREVIOUS MONTH
                                upcoming_invoice_date = order.rentalfirst_invoice_date + relativedelta(months=month_count)
                                start_dt = next_invoice_date - relativedelta(months=1)
                                end_dt = upcoming_invoice_date - relativedelta(months=1)
                                #add one more day to get final day in accounting
                                # end_dt = upcoming_invoice_date - relativedelta(days=1)
                                if next_invoice_date >= order.rental_return_date.date():
                                    # end_dt = order.rental_return_date.date()+relativedelta(days=1)
                                    end_dt = order.rental_return_date.date()
                                start_dt = datetime.combine(start_dt, datetime_min_time)
                                end_dt = datetime.combine(end_dt, datetime_max_time)
                                planned_worked = \
                                order_line.product_id.employee_id._get_work_days_data_batch(start_dt, end_dt,
                                                                                            calendar=order_line.product_id.employee_id.resource_calendar_id) \
                                    [order_line.product_id.employee_id.id]['days']
                                if planned_worked > 0:
                                    uom='days'
                                    if order_line.product_uom.name=='Hours':
                                        planned_worked = planned_worked*8
                                        uom='hours'
                                    dummy_start_dt = start_dt + relativedelta(days=5)
                                    inv_dates.append((0, 0, {'sale_state': order.state,
                                                             'planned_days': planned_worked,
                                                             'partner_id': order.partner_id.id,
                                                             'employee_id': order_line.product_id.employee_id.id,
                                                             'rentalnext_invoice_date': next_invoice_date,
                                                             'rentalnext_invoice_date_time': next_invoice_date,
                                                             'uom':uom,
                                                             'rental_month': str(dummy_start_dt.month)
                                                             }))
                                    if emp_id == order_line.product_id.employee_id.id:
                                        if order_line.product_uom.name == 'Hours':
                                            planned_worked = planned_worked/8
                                        no_working_days = no_working_days + planned_worked
                                month_count = month_count + 1
                                next_invoice_date = upcoming_invoice_date
                                total_working_days = total_working_days + planned_worked
                    if inv_dates:
                        order.duration_days = no_working_days
                        order.rental_inv_line_ids=inv_dates
                        for order_line in order.order_line:
                            if order_line.product_uom.name == 'Hours':
                                order_line.product_uom_qty = order.duration_days * 8
                            else:
                                order_line.product_uom_qty = order.duration_days

    def _confirmation_error_message(self):
        """ Return whether order can be confirmed or not if not then returm error message. """
        self.ensure_one()
        if self.state not in {'draft', 'sent'}:
            if self.is_rental_order == False:
                return _("Some orders are not in a state requiring confirmation.")
        if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
        ):
            return _("A line on these orders missing a product, you cannot confirm it.")

        return False

    def create_rental_invoice(self, rental_obj):
        invoice_line_ids=[]
        invoice_date=''
        for line in rental_obj.rental_sale_id.order_line:
            for rental_line in rental_obj.rental_sale_id.rental_inv_line_ids:
                if not invoice_date and rental_line.is_ready_to_invoice==True and rental_line.worked_days>0:
                    invoice_date = rental_line.rentalnext_invoice_date
                if not rental_line.inv_ref_id and rental_line.worked_days>0:
                    if line.product_id.employee_id.id == rental_line.employee_id.id:
                        old_rental_objs = self.env['rental.invoice.history'].search(
                            [('rental_sale_id', '=', rental_obj.rental_sale_id.id),('employee_id', '=', rental_line.employee_id.id),
                             ('state', 'in', ['confirmed', 'done'])], limit=1, order='id desc')
                        if old_rental_objs:
                            old_inv_date = old_rental_objs.rentalnext_invoice_date
                        else:
                            old_inv_date = rental_obj.rental_sale_id.rental_start_date
                        upcoming_rental_objs = self.env['rental.invoice.history'].search(
                            [('rental_sale_id', '=', rental_obj.rental_sale_id.id),
                             ('employee_id', '=', rental_line.employee_id.id),
                             ('state', 'in', ['draft'])], limit=1)
                        if upcoming_rental_objs:
                            new_inv_date = upcoming_rental_objs.rentalnext_invoice_date
                        else:
                            new_inv_date = rental_obj.rental_sale_id.rental_return_date
                        distribution = line.env['account.analytic.distribution.model']._get_distribution({
                            "product_id": line.product_id.id,
                            "partner_id": line.order_id.partner_id.id,
                            "company_id": line.company_id.id,
                        })
                        analytic_distribution = distribution or line.analytic_distribution
                        if rental_obj.worked_days>0:
                            inv_line={
                                'product_id': line.product_id.id,
                                'product_uom_id':line.product_uom.id,
                                'name': line.product_id.name,
                                'quantity': rental_line.worked_days,
                                'price_unit': line.price_unit,
                                'tax_ids': line.tax_id,
                                'discount': line.discount,
                                'sale_line_ids': [Command.link(line.id)],
                                'rental_start_date': old_inv_date,
                                'rental_return_date': new_inv_date,
                            }
                            if analytic_distribution:
                                inv_line.update({'analytic_distribution':analytic_distribution})
                            invoice_line_ids.append((0, 0, inv_line))
                        # line.qty_delivered = line.qty_delivered + rental_line.worked_days
                        rental_line.is_ready_to_invoice=False
                        rental_line.state='done'
        if invoice_line_ids:
            inv_obj = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rental_obj.rental_sale_id.partner_id.id,
                'invoice_date': invoice_date or fields.date.today(),
                'ref': rental_obj.rental_sale_id.name or '',
                'narration': rental_obj.rental_sale_id.note,
                'source_id': rental_obj.rental_sale_id.source_id.id,
                'team_id': rental_obj.rental_sale_id.team_id.id,
                'fiscal_position_id': (rental_obj.rental_sale_id.fiscal_position_id or rental_obj.rental_sale_id.fiscal_position_id._get_fiscal_position(rental_obj.rental_sale_id.partner_invoice_id)).id,
                'invoice_origin': rental_obj.rental_sale_id.name,
                'invoice_payment_term_id': rental_obj.rental_sale_id.payment_term_id.id,
                'invoice_user_id': rental_obj.rental_sale_id.user_id.id,
                'payment_reference': rental_obj.rental_sale_id.reference,
                'user_id': rental_obj.rental_sale_id.user_id.id,
                'invoice_line_ids': invoice_line_ids
            })
            if inv_obj:
                for line in rental_obj.rental_sale_id.order_line:
                    for rental_line in rental_obj.rental_sale_id.rental_inv_line_ids:
                        if not rental_line.inv_ref_id and rental_line.worked_days > 0.00:
                            if line.product_id.employee_id.id == rental_line.employee_id.id:
                                rental_line.inv_ref_id = inv_obj.id
                for inv_line in inv_obj.invoice_line_ids:
                    inv_line._compute_name()
                    for so_line in rental_obj.rental_sale_id.order_line:
                        if inv_line.product_id.id == so_line.product_id.id:
                            inv_ids=[inv_line.id]+so_line.invoice_lines.ids
                            so_line.invoice_lines = [(6, 0, inv_ids)]
                return inv_obj

    def _cron_create_rental_month_invoices(self, rental_invoice=''):
        """ Generate invoice """
        if rental_invoice:
            rental_objs = rental_invoice
        else:
            to_be_invoiced=[]
            user_tz = timezone(self.env.user.tz or 'UTC')
            now_dt = datetime.now().astimezone(user_tz).replace(tzinfo=None)
            r_invoice_day = self.env['ir.config_parameter'].sudo().get_param('techcarret_rental.r_invoice_day')
            search_date = date.today() + timedelta(days=int(r_invoice_day))
            rental_objs = self.env['rental.invoice.history'].search([('state', '=', 'draft')])
            for rental_obj in rental_objs:
                if rental_obj.rentalnext_invoice_date <= search_date:
                    if rental_obj.rental_sale_id.invoice_freequency.unit in ['hour']:
                        rentalnext_invoice_date_time  = pytz.utc.localize(rental_obj.rentalnext_invoice_date_time).astimezone(user_tz)
                        if rentalnext_invoice_date_time.date() < now_dt.date():
                            to_be_invoiced.append(rental_obj.id)
                        elif rentalnext_invoice_date_time.hour <= now_dt.hour:
                            to_be_invoiced.append(rental_obj.id)
                    else:
                        to_be_invoiced.append(rental_obj.id)
            if to_be_invoiced:
                rental_objs = self.env['rental.invoice.history'].search([('id', 'in', to_be_invoiced)])
        for rental_obj in rental_objs:
            if rental_obj.rental_sale_id.state=='sale':
                pending_month=[]
                for rh in rental_obj.rental_sale_id.rental_inv_line_ids:
                    if rh.state == 'draft':
                        m = rh.rentalnext_invoice_date.month
                        y = rh.rentalnext_invoice_date.year
                        str_m_y = str(m)+'_'+str(y)
                        pending_month.append(str_m_y)
                timesheet_months=[]
                if rental_obj.worked_days<=0:
                    old_rental_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=',rental_obj.rental_sale_id.id),('id', '=', int(rental_obj.id-1)),('state','in',['confirmed','done'])], limit=1)
                    future_rental_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=',rental_obj.rental_sale_id.id),('id', '=', int(rental_obj.id+1)),('state','in',['draft'])], limit=1)
                    if old_rental_objs:
                        start_date=(old_rental_objs.rentalnext_invoice_date).strftime('%Y-%m-%d 00:00:00')
                        if future_rental_objs:
                            end_date=datetime.strftime(future_rental_objs.rentalnext_invoice_date - timedelta(days=1), "%Y-%m-%d 23:59:59")
                        else:
                            end_date=datetime.strftime(rental_obj.rental_sale_id.rental_return_date, "%Y-%m-%d 23:59:59")
                    else:
                        start_date=(rental_obj.rental_sale_id.rental_start_date).strftime('%Y-%m-%d 00:00:00')
                        if future_rental_objs:
                            end_date=datetime.strftime(future_rental_objs.rentalnext_invoice_date - timedelta(days=1), "%Y-%m-%d 23:59:59")
                        else:
                            end_date=datetime.strftime(rental_obj.rental_sale_id.rental_return_date, "%Y-%m-%d 23:59:59")
                    delta =timedelta(days=1)
                    start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                    while start_date <= end_date:
                        m = start_date.month
                        y = start_date.year
                        str_m_y = str(m)+'_'+str(y)
                        if str_m_y not in timesheet_months and str_m_y in pending_month:
                            timesheet_months.append(str_m_y)
                        start_date += delta
                    if rental_obj.employee_id:
                        #CREATE RENTAL INVOICE
                        if rental_obj.worked_days>0:
                            self.create_rental_invoice(rental_obj)
                            rental_obj.state = 'done'
                            rental_obj.is_ready_to_invoice=False
                            if future_rental_objs:
                                future_rental_objs.is_ready_to_invoice=True
                                rental_obj.rental_sale_id.rentalnext_invoice_date = future_rental_objs.rentalnext_invoice_date
                else:
                    #CREATE RENTAL INVOICE
                    self.create_rental_invoice(rental_obj)
                    rental_obj.state = 'done'
                    rental_obj.is_ready_to_invoice=False
                    future_rental_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=',rental_obj.rental_sale_id.id),('id', '=', int(rental_obj.id+1)),('state','in',['draft'])], limit=1)
                    if future_rental_objs:
                        future_rental_objs.is_ready_to_invoice=True
                        rental_obj.rental_sale_id.rentalnext_invoice_date = future_rental_objs.rentalnext_invoice_date

    def action_confirm(self):
        res = super(Rentals, self).action_confirm()
        for so_line in self:
            if so_line.is_rental_order == True:
                for rental_in in so_line.rental_inv_line_ids:
                    rental_in.state ='draft'
                # for o_line in so_line.order_line:
                    # if o_line.product_id and not o_line.product_id.employee_id:
                    #     raise UserError(_("Employee profile not mapped in product master"))
                for r_invoice in so_line.rental_inv_line_ids:
                    r_invoice.sale_state='sale'
            if not so_line.order_line:
                raise UserError(("Please add some Products in Order lines."))
            project = so_line.order_line[0]._timesheet_create_project()
        return res

    def action_cancel(self):
        res = super(Rentals, self).action_cancel()
        for so_line in self:
            if so_line.is_rental_order == True:
                for r_invoice in so_line.rental_inv_line_ids:
                    r_invoice.sale_state='cancel'
                    r_invoice.state='cancel'
        return res

    def action_draft(self):
        res = super(Rentals, self).action_draft()
        for so_line in self:
            if so_line.is_rental_order == True:
                for line in so_line.order_line:
                    line.qty_delivered =0
                for r_invoice in so_line.rental_inv_line_ids:
                    r_invoice.sale_state='draft'
                    r_invoice.state='draft'
        return res

    def _prepare_analytic_account_data(self, prefix=None):
        """ Prepare SO analytic account creation values.

        :return: `account.analytic.account` creation values
        :rtype: dict
        """
        self.ensure_one()
        name = self.name
        if prefix:
            name = prefix + ": " + self.name
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        return {
            'name': self.project_code,
            'code': self.client_order_ref,
            'company_id': self.company_id.id,
            'plan_id': project_plan.id,
            'partner_id': self.partner_id.id,
        }


class RentalOrdersLine(models.Model):
    _inherit = 'sale.order.line'

    qty_delivered = fields.Float(
        string="Delivery Quantity",
        compute='_compute_qty_delivered',
        default=0.0,
        digits='Product Unit of Measure',
        store=True, readonly=False, copy=False)
    start_date = fields.Datetime()
    return_date = fields.Datetime()

    # @api.depends(
    #     'qty_delivered_method',
    #     'analytic_line_ids.so_line',
    #     'analytic_line_ids.unit_amount',
    #     'analytic_line_ids.product_uom_id')
    # def _compute_qty_delivered(self):
    #     """ This method compute the delivered quantity of the SO lines: it covers the case provide by sale module, aka
    #         expense/vendor bills (sum of unit_amount of AAL), and manual case.
    #         This method should be overridden to provide other way to automatically compute delivered qty. Overrides should
    #         take their concerned so lines, compute and set the `qty_delivered` field, and call super with the remaining
    #         records.
    #     """
    #     # compute for analytic lines
    #     for line in self:
    #         if line.order_id.is_rental_order == False:
    #             lines_by_analytic = self.filtered(lambda sol: sol.qty_delivered_method == 'analytic')
    #             mapping = lines_by_analytic._get_delivered_quantity_by_analytic([('amount', '<=', 0.0)])
    #             for so_line in lines_by_analytic:
    #                 so_line.qty_delivered = mapping.get(so_line.id or so_line._origin.id, 0.0)

    def _get_rental_order_line_description(self):
        tz = self._get_tz()
        if self.order_id.is_rental_order == True:
            start_date = self.order_id.rental_start_date
            return_date = self.order_id.rental_return_date
            user_tz = self.env.user.tz or self.env.context.get('tz')
            user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
            now_dt = start_date.astimezone(user_pytz).replace(tzinfo=None)
            now_dt = now_dt + relativedelta(hours=10)
            self.start_date = now_dt
            start_date = now_dt
            if self.order_id.recurring_period_interval in ['month','week','year']:
                s_date = datetime.strptime(str(start_date), "%Y-%m-%d %H:%M:%S").date()
                r_date = datetime.strptime(str(return_date), "%Y-%m-%d %H:%M:%S").date()
                s_date = s_date.strftime("%d-%m-%Y")
                r_date = r_date.strftime("%d-%m-%Y")
                return _(
                    "\n%(from_date)s to %(to_date)s", from_date=s_date, to_date=r_date
                )
            else:
                start_date = self.order_id.rental_start_date
                return_date = self.order_id.rental_return_date
                env = self.with_context(use_babel=True).env
                if start_date and return_date \
                        and start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date() \
                        == return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date():
                    # If return day is the same as pickup day, don't display return_date Y/M/D in description.
                    return_date_part = format_time(env, return_date, tz=tz, time_format=False)
                else:
                    return_date_part = format_datetime(env, return_date, tz=tz, dt_format=False)
                start_date_part = format_datetime(env, start_date, tz=tz, dt_format=False)
                return _(
                    "\n%(from_date)s to %(to_date)s", from_date=start_date_part, to_date=return_date_part
                )
        else:
            start_date = self.order_id.rental_start_date
            return_date = self.order_id.rental_return_date
            env = self.with_context(use_babel=True).env
            if start_date and return_date \
                    and start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date() \
                    == return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date():
                # If return day is the same as pickup day, don't display return_date Y/M/D in description.
                return_date_part = format_time(env, return_date, tz=tz, time_format=False)
            else:
                return_date_part = format_datetime(env, return_date, tz=tz, dt_format=False)
            start_date_part = format_datetime(env, start_date, tz=tz, dt_format=False)
            return _(
                "\n%(from_date)s to %(to_date)s", from_date=start_date_part, to_date=return_date_part
            )

    def _timesheet_create_project_prepare_values(self):
        res = super(RentalOrdersLine, self)._timesheet_create_project_prepare_values()
        res['name'] = self.order_id.project_code
        today_date = fields.Datetime.now()
        pro_end_date = today_date.date() + timedelta(days=30)
        res['date_start'] = today_date.date()
        res['date'] = pro_end_date
        print('DESSSSSSSSSSSS',res)
        return res

    @api.onchange('product_id')
    def _onchange_rent_product(self):
        for order in self:
            order.start_date = order.order_id.rental_start_date
            order.return_date = order.order_id.rental_return_date
            if order.order_id.is_rental_order == True:
                # if order.product_id and not order.product_id.employee_id:
                #     raise UserError(_("Employee profile not mapped in product master"))
                # if order.product_id.employee_id.work_log_ids:
                #     for line in order.product_id.employee_id.work_log_ids:
                #         if line.state == 'active':
                #             raise UserError(_("Employee is not available for rental."))
                if order.order_id.duration_days>0 and order.product_uom_qty<=1:
                    if order.product_uom.name == 'Hours':
                        order.product_uom_qty = order.order_id.duration_days * 8
                    else:
                        order.product_uom_qty = order.order_id.duration_days

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_rentalproduct(self):
        for order in self:
            if order.order_id.is_rental_order == True:
                if order.product_id.product_pricing_ids:
                    for product_pricing_id in order.product_id.product_pricing_ids:
                        if order.product_uom.name == 'Hours' and product_pricing_id.recurrence_id.unit == 'hour':
                            order.price_unit= product_pricing_id.price
                        elif order.product_uom.name == 'Days'and product_pricing_id.recurrence_id.unit == 'day':
                            order.price_unit=product_pricing_id.price
                        elif order.product_uom.name == 'Week'and product_pricing_id.recurrence_id.unit == 'week':
                            order.price_unit=product_pricing_id.price
                        elif order.product_uom.name == 'Months'and product_pricing_id.recurrence_id.unit == 'month':
                            order.price_unit=product_pricing_id.price
                        elif order.product_uom.name == 'Years' and product_pricing_id.recurrence_id.unit == 'year':
                            order.price_unit=product_pricing_id.price
                else:
                    if order.price_unit == 0.00:
                        order.price_unit = order.product_id.with_company(order.company_id.id).lst_price

class RentalInvoiceHistory(models.Model):
    _name = 'rental.invoice.history'

    rental_sale_id = fields.Many2one(
        comodel_name='sale.order',
        string="Rental Order",
        required=True, ondelete='cascade', index=True, copy=False)
    is_ready_to_invoice = fields.Boolean('Can be invoiced?', default=False, copy=False)
    partner_id = fields.Many2one('res.partner', string="Customer")
    rentalnext_invoice_date = fields.Date(string='Next Invoice Date')
    rentalnext_invoice_date_time = fields.Datetime(string='Next Invoice Date')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    inv_ref_id = fields.Many2one('account.move', 'Invoice Ref#')
    invoice_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        related='inv_ref_id.state',
        string='Status',
    )
    sale_state = fields.Selection([('draft', "Quotation"),
                              ('sent', "Quotation Sent"),
                              ('sale', "Sales Order"),
                              ('cancel', "Cancelled"),], default='draft')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Invoiced'),('confirmed','Confirmed'),('cancel','Cancel')], default='draft')
    uom = fields.Selection([("hours", "Hours"), ("days", "Days")], string="UOM", required=True, default="days")
    rental_month = fields.Selection([
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
    ], string="Rental Month", default="1")
    work_entry_ids = fields.Many2many('hr.work.entry', string='Work Entries')
    planned_days = fields.Integer("Planned QTY")
    worked_days = fields.Integer("Worked QTY")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    def create_invoice(self):
        for line in self:
            line.rental_sale_id._cron_create_rental_month_invoices(line)

    @api.onchange('worked_days')
    def _onchange_worked_days(self):
        self.is_ready_to_invoice=False
        if self.worked_days>0.0:
            self.is_ready_to_invoice=True

class ProjectProject(models.Model):
    _inherit = 'project.project'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Project must be unique.')
    ]

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for project in self.filtered(lambda project: project.sale_line_id):
            break
            # if not project.sale_line_id.is_service:
            #     raise ValidationError(
            #         _("You cannot link a billable project to a sales order item that is not a service."))
            # if project.sale_line_id.is_expense:
            #     raise ValidationError(
            #         _("You cannot link a billable project to a sales order item that comes from an expense or a vendor bill."))

