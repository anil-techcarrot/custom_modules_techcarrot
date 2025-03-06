# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    work_log_ids = fields.One2many(
        comodel_name='employee.worklog',
        inverse_name='employee_id',
        string="Work Logs",
        copy=True, auto_join=True)
    work_entry_ids = fields.One2many(
        comodel_name='employee.workentry',
        inverse_name='employee_id',
        string="Work Entry",
        copy=True, auto_join=True)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super(HrEmployeePrivate, self).create(vals_list)
        if employees:
            for employee in employees:
                # Create a product template
                uom_obj = self.env['uom.uom'].search([('name', '=', 'Days')], limit=1)
                product_template_id = self.env['product.template'].create({
                    'name': employee.name,
                    'sale_ok': False,
                    'purchase_ok': False,
                    'rent_ok': True,
                    'type': 'service',
                    'is_storable': False,
                    'employee_id':employee.id,
                })
                if product_template_id:
                    product_template_id.name = employee.name
                    product_template_id.uom_id = uom_obj.id
                    # attribute_obj = self.env['product.attribute'].search([('name', '=', 'Shift')], limit=1)
                    # if attribute_obj:
                    #     self.env['product.template.attribute.line'].create({
                    #         'attribute_id': attribute_obj.id,
                    #         'product_tmpl_id': product_template_id.id,
                    #         'value_ids': [(6, 0, [attribute_obj.value_ids.ids[0]])],
                    #     })
        return employees

class WorkLog(models.Model):
    _name = "employee.worklog"
    _description = 'Work Log'

    date_start = fields.Datetime('Date Start')
    date_end =  fields.Datetime('Date End')
    partner_id = fields.Many2one('res.partner', 'Customer')
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee Reference",
        required=True, ondelete='cascade', index=True, copy=False)
    rental_id = fields.Many2one('sale.order', 'Rental Order')
    state = fields.Selection([('active', 'In-Progress'), ('cancel', 'Cancel'), ('closed', 'Completed')], default='active', string="Rental State")


class WorkEntry(models.Model):
    _name = "employee.workentry"
    _description = 'Work Entry'

    date_start = fields.Date('Date Start')
    date_end =  fields.Date('Date End')
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee Reference",
        required=True, ondelete='cascade', index=True, copy=False)
    worked_days = fields.Integer("Worked Days")
    import_id = fields.Many2one('import.attendance.line', 'Attendance line')
    state = fields.Selection([('imported', 'Imported'), ('Invoiced', 'Invoiced')], default='imported', string="State")
