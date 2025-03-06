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

	def get_eployee(self, barcode):
		emp_obj = self.env['hr.employee'].sudo().search([('barcode', '=', str(barcode))], limit=1)
		if emp_obj:
			return emp_obj
		else:
			return False

	def import_attendance(self):
		for line in self.attendance_data_ids:
			delta =timedelta(days=1)
			date_start = line.date_start
			date_end = line.date_end
			emp_import_attendance_objs = self.env['import.attendance.line'].sudo().search([('state','=','imported'),('employee_id', '=', line.employee_id.id)])
			while date_start <= date_end:
				d = date_start.day
				m = date_start.month
				y = date_start.year
				str_m_y = str(d)+'_'+str(m)+'_'+str(y)
				for emp_import_attendance_obj in emp_import_attendance_objs:
					d_m_y_list = emp_import_attendance_obj.d_m_y.split(",")
					if str_m_y in d_m_y_list:
						raise UserError(_('Employee timesheet already imported. Employee %s, %s', line.employee_id.barcode, date_start))
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
						m = line.date_start.month
						y = line.date_start.year
						str_m_y = str(m)+'_'+str(y)
						hm =history_obj.rentalnext_invoice_date.month
						hy =history_obj.rentalnext_invoice_date.year
						hstr_m_y = str(hm)+'_'+str(hy)
						if str_m_y == hstr_m_y:
							if count==0 and history_obj.worked_days==0:
								history_obj.worked_days = line.worked_days
								line.sale_id = history_obj.rental_sale_id.id
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
				line.history_line_id.worked_days=0
				line.history_line_id=''
				line.sale_id=''
				line.state='draft'
			# else:
			# 	raise ValidationError(_("Can not roll back the invoiced data!"))
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
						seconds = (float(line[1]) - 25569) * 86400.0
						date_start =datetime.utcfromtimestamp(seconds).date()
						seconds = (float(line[4]) - 25569) * 86400.0
						date_end =datetime.utcfromtimestamp(seconds).date()
						self.date_start = date_start
						self.date_end = date_end
						delta =timedelta(days=1)
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
							barcode = line[1].split('.')[0]
						else:
							barcode = str(line[1])
						employee_obj = self.get_eployee(barcode)
						if not employee_obj:
							raise UserError(_('Employee not found %s.', barcode))
						if employee_obj.id not in no_employee:
							no_employee.append(employee_obj.id)

						delta =timedelta(days=1)
						tmp_date_start = date_start
						tmp_date_end = date_end
						emp_import_attendance_objs = self.env['import.attendance.line'].sudo().search([('state','=','imported'),('employee_id', '=', employee_obj.id)])
						for emp_import_attendance_obj in emp_import_attendance_objs:
							while tmp_date_start <= tmp_date_end:
								d = tmp_date_start.day
								m = tmp_date_start.month
								y = tmp_date_start.year
								str_m_y = str(d)+'_'+str(m)+'_'+str(y)
								d_m_y_list = emp_import_attendance_obj.d_m_y.split(",")
								if str_m_y in d_m_y_list:
									raise UserError(_('Employee timesheet already imported. Employee %s, %s', employee_obj.barcode, tmp_date_start))
								tmp_date_start += delta
						values.append((0, 0, {
									'date_start': date_start,
									'date_end': date_end,
									'employee_id': employee_obj.id,
									'worked_days': int(float(line[2])),
									'd_m_y':d_m_y
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
