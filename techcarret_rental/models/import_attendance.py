# -*- coding: utf-8 -*-
import xlrd
import logging
import tempfile
import binascii
from datetime import date, datetime, timedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
	import xlwt
except ImportError:
	_logger.debug('Cannot `import xlwt`.')
try:
	import cStringIO
except ImportError:
	_logger.debug('Cannot `import cStringIO`.')
try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')


class ImportAttendance(models.Model):
	_name = 'import.attendance'
	_description = 'Import Attendance'
	_order = 'id desc'

	file_type = fields.Selection([('XLS', 'XLS File')],string='File Type', default='XLS')
	file = fields.Binary(string="Upload File", required=True)
	date_start = fields.Date('Date Start')
	date_end =  fields.Date('Date End')
	no_employee = fields.Integer('NO. Employees', compute='get_num_employee')
	state = fields.Selection([("draft", "New"), ("imported", "Imported")], required=True, default="draft")
	attendance_data_ids = fields.One2many('import.attendance.line', 'import_attendance_id', string='Stock Data')

	def get_eployee(self, emp_code):
		emp_obj = self.env['hr.employee'].sudo().search([('emp_code', '=', str(emp_code))], limit=1)
		if emp_obj:
			return emp_obj
		else:
			raise UserError(_('Employee master not found. Employee ID: %s', emp_code))

	def get_project(self, code):
		so_obj = self.env['sale.order'].sudo().search([('is_rental_order','=',True),('project_code', '=', str(code))], limit=1)
		if so_obj:
			if so_obj.state != 'sale':
				raise UserError(_('Rental not confirmed. Project code: %s', code))
			return so_obj
		else:
			raise UserError(_('Rental project code not found. Project code: %s', code))

	def import_attendance(self):
		for line in self.attendance_data_ids:
			delta =timedelta(days=1)
			date_start = line.date_start
			date_end = line.date_end
			emp_import_attendance_objs = self.env['import.attendance.line'].sudo().search([('sale_id','=',line.sale_id.id),('state','=','imported'),('employee_id', '=', line.employee_id.id)])
			while date_start <= date_end:
				d = date_end.day
				m = date_end.month
				y = date_end.year
				str_m_y = str(d)+'_'+str(m)+'_'+str(y)
				for emp_import_attendance_obj in emp_import_attendance_objs:
					d_m_y_list = emp_import_attendance_obj.d_m_y.split(",")
					if str_m_y in d_m_y_list:
						raise UserError(_('Employee timesheet already imported. Employee %s, %s', line.employee_id.emp_code, date_start))
				date_start += delta
			history_objs = self.env['rental.invoice.history'].sudo().search([('sale_state','=','sale'),('state','=','draft'),('employee_id', '=', line.employee_id.id)])
			if history_objs:
				#Import only if rented
				self.env['employee.workentry'].create({
					'employee_id': line.employee_id.id,
					'date_start': line.date_start,
					'date_end': line.date_end,
					'worked_days': line.worked_days,
					'import_id':line.id
				})
				count=0
				for history_obj in history_objs:
					if history_obj.rental_sale_id.is_rental_order == True and history_obj.rental_sale_id.state=='sale':
						m = line.date_end.month
						y = line.date_end.year
						str_m_y = str(m)+'_'+str(y)
						hm =history_obj.rentalnext_invoice_date.month
						hy =history_obj.rentalnext_invoice_date.year
						hstr_m_y = str(hm)+'_'+str(hy)
						if str_m_y == hstr_m_y:
							# if count==0 and history_obj.worked_days==0:
							if count==0:
								history_obj.worked_days = history_obj.worked_days+line.worked_days
								# line.sale_id = history_obj.rental_sale_id.id
								line.history_line_id=history_obj.id
								count=count+1
			line.state='imported'
		self.state = 'imported'

	def rollback_data(self):
		for line in self.attendance_data_ids:
			workentry_obj = self.env['employee.workentry'].sudo().search([('import_id', '=', line.id)])
			if workentry_obj:
				workentry_obj.unlink()
			if not line.history_line_id.inv_ref_id:
				line.history_line_id.worked_days= abs(line.history_line_id.worked_days - line.worked_days)
				line.history_line_id=''
				# line.sale_id=''
				line.state='draft'
			else:
				raise ValidationError(_("Can not roll back the invoiced data!"))
		self.state = 'draft'

	def get_num_employee(self):
		for imp_record in self:
			no_employee=[]
			for line in imp_record.attendance_data_ids:
				if line.employee_id:
					if line.employee_id.id not in no_employee:
						no_employee.append(line.employee_id.id)
			imp_record.no_employee=len(no_employee)

	@api.onchange('file')
	def get_stock_data(self):
		values=[]
		self.attendance_data_ids = [(6, 0, [])]
		no_employee=[]
		d_m_y=''
		# holiday_list=[]
		# w_working_days=[]
		if self.file and not self.attendance_data_ids:
			try:
				file = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
				file.write(binascii.a2b_base64(self.file))
				file.seek(0)
				workbook = xlrd.open_workbook(file.name)
				sheet = workbook.sheet_by_index(0)
			except Exception:
				raise ValidationError(_("Please Select Valid File Format !"))
			for row_no in range(sheet.nrows):
				line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
				if line:
					if row_no==0:
						seconds = (float(line[2]) - 25569) * 86400.0
						date_start =datetime.utcfromtimestamp(seconds).date()
						seconds = (float(line[5]) - 25569) * 86400.0
						date_end =datetime.utcfromtimestamp(seconds).date()
						self.date_start = date_start
						self.date_end = date_end
						if self.date_end<=self.date_start:
							raise UserError('Date end can not be less than the start date')
						delta = timedelta(days=1)
						tmp_date_start = date_start
						tmp_date_end = date_end
						while tmp_date_start <= tmp_date_end:
							d = tmp_date_start.day
							m = tmp_date_start.month
							y = tmp_date_start.year
							str_m_y = str(d)+'_'+str(m)+'_'+str(y)
							tmp_date_start += delta
							if d_m_y=='':
								d_m_y = str_m_y
							else:
								d_m_y = d_m_y+","+str_m_y
					if row_no>=2:
						if '.' in line[1]:
							project_code = line[1].split('.')[0]
						else:
							project_code = str(line[1])
						if '.' in line[2]:
							emp_code = line[2].split('.')[0]
						else:
							emp_code = str(line[2])
						employee_obj = self.get_eployee(emp_code)
						if employee_obj.id:
							no_employee.append(employee_obj.id)
						so_obj = self.get_project(project_code)
						delta = timedelta(days=1)
						tmp_date_start = date_start
						tmp_date_end = date_end
						emp_import_attendance_objs = self.env['import.attendance.line'].sudo().search([('sale_id','=',so_obj.id),('state','=','imported'),('employee_id', '=', employee_obj.id)])
						for emp_import_attendance_obj in emp_import_attendance_objs:
							while tmp_date_start <= tmp_date_end:
								d = tmp_date_start.day
								m = tmp_date_start.month
								y = tmp_date_start.year
								str_m_y = str(d)+'_'+str(m)+'_'+str(y)
								d_m_y_list = emp_import_attendance_obj.d_m_y.split(",")
								if str_m_y in d_m_y_list:
									raise UserError(_('Employee timesheet already imported. Employee %s, %s', employee_obj.emp_code, tmp_date_start))
								tmp_date_start += delta
						values.append((0, 0, {
									'date_start': date_start,
									'date_end': date_end,
									'employee_id': employee_obj.id,
									'worked_days': int(float(line[3])),
									'd_m_y':d_m_y,
									'sale_id':so_obj.id
									}))
			if values:
				self.attendance_data_ids= values
				self.no_employee=len(no_employee)

	def unlink(self):
		for rec in self:
			if rec.state == 'imported':
				raise UserError(_('Imported data can not be deleted.'))
		return super(ImportAttendance, self).unlink()


class ImportStockLine(models.Model):
	_name = 'import.attendance.line'
	_description = 'Import Stock Line'

	import_attendance_id = fields.Many2one("import.attendance", 'Stock Data', required=True, ondelete='cascade', index=True, copy=False)
	date_start = fields.Date('Date Start')
	date_end =  fields.Date('Date End')
	employee_id = fields.Many2one('hr.employee', string="Employee")
	worked_days = fields.Integer("Days Worked")
	d_m_y = fields.Char("Date-Month-Year")
	state = fields.Selection([("draft", "New"), ("imported", "Imported")], required=True, default="draft")
	sale_id = fields.Many2one('sale.order', 'Rental Ref#', copy=False)
	history_line_id = fields.Many2one('rental.invoice.history', copy=False)

	@api.constrains('worked_days')
	def _check_worked_days(self):
		if self.worked_days <0 or self.worked_days >31:
			raise UserError(_('Worked days must be between 1-31 days.'))
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
