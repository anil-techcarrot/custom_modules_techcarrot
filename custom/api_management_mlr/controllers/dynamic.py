# -*- coding: utf-8 -*-
import datetime
import logging
from odoo import http, fields
from odoo.http import request
import json

_logger = logging.getLogger(__name__)

def serialize_field(record, field_name, field):
    value = record[field_name]
    if field.type in (
        'char', 'text', 'selection', 'integer', 'float', 'boolean', 'monetary'
    ):
        return value
    elif field.type in ('date', 'datetime'):
        return value.isoformat() if value else value
    elif field.type == 'many2one':
        if value:
            try:
                rec = value[0] if len(value) > 1 else value
                rec.ensure_one()
                try:
                    ng = rec.name_get()
                except Exception:
                    ng = None
                if ng:
                    name = ng[0][1]
                elif hasattr(rec, 'name'):
                    name = rec.name
                else:
                    name = str(rec.id)
            except Exception:
                name = str(value.id) if value else ''
            return {'id': rec.id, 'name': name}
        return None
    elif field.type in ('one2many', 'many2many'):
        result = []
        for r in value:
            try:
                r.ensure_one()
                try:
                    ng = r.name_get()
                except Exception:
                    ng = None
                if ng:
                    name = ng[0][1]
                elif hasattr(r, 'name'):
                    name = r.name
                else:
                    name = str(r.id)
            except Exception:
                name = str(r.id)
            result.append({'id': r.id, 'name': name})
        return result
    elif field.type == 'binary':
        return bool(value)
    else:
        return str(value)


class DynamicAPI(http.Controller):
    @http.route('/api/<string:endpoint_path>', auth='none', type='http', methods=['GET'], csrf=False)
    def dynamic_api_handler(self, endpoint_path, **kwargs):
        api_key_value = (
            request.httprequest.headers.get('x-api-key') or
            request.params.get('key')
        )
        ip_address = request.httprequest.remote_addr
        query_string = request.httprequest.query_string.decode()

        # ✅ Get limit and offset from request
        limit = int(kwargs.get('limit', 100))
        offset = int(kwargs.get('offset', 0))

        api_key = request.env['res.api.key'].sudo().search([
            ('key', '=', api_key_value),
            ('active', '=', True),
            '|', ('expiry_date', '=', False),
                 ('expiry_date', '>=', fields.Date.today())
        ], limit=1)

        if not api_key:
            return self._unauthorized(endpoint_path, ip_address, query_string)

        endpoint = request.env['res.api.endpoint'].sudo().search([
            ('url_path', '=', endpoint_path),
            ('active', '=', True),
            ('api_key_ids', 'in', api_key.id),
        ], limit=1)

        if not endpoint:
            return self._unauthorized(endpoint_path, ip_address, query_string)

        model_name = endpoint.model_id.model
        allowed_fields = endpoint.field_ids.mapped('name')
        model_obj = request.env[model_name]

        allowed_companies = api_key.company_ids.ids
        if not allowed_companies:
            allowed_companies = request.env.user.company_ids.ids
        if not allowed_companies:
            allowed_companies = request.env['res.company'].sudo().search([]).ids
        if not allowed_companies:
            return request.make_response(
                json.dumps({'error': 'No companies found in the system.'}),
                status=403,
                headers=[('Content-Type', 'application/json')]
            )

        try:
            table_name = model_obj._table
            model_fields = model_obj._fields
            has_company_id = 'company_id' in model_fields
            has_company_ids = 'company_ids' in model_fields and model_fields['company_ids'].type == 'many2many'

            if has_company_id:
                placeholders = ','.join(['%s'] * len(allowed_companies))
                # ✅ FIXED: Use limit and offset from request
                sql = f"SELECT id FROM {table_name} WHERE company_id IN ({placeholders}) ORDER BY id LIMIT {limit} OFFSET {offset}"
                params = tuple(allowed_companies)
            elif has_company_ids:
                m2m = model_fields['company_ids']
                rel_table = m2m.relation
                col1 = m2m.column1
                col2 = m2m.column2
                placeholders = ','.join(['%s'] * len(allowed_companies))
                # ✅ FIXED: Use limit and offset from request
                sql = (f"SELECT t.id FROM {table_name} t "
                       f"JOIN {rel_table} rel ON rel.{col1} = t.id "
                       f"WHERE rel.{col2} IN ({placeholders}) ORDER BY t.id LIMIT {limit} OFFSET {offset}")
                params = tuple(allowed_companies)
            else:
                # ✅ FIXED: Use limit and offset from request
                sql = f"SELECT id FROM {table_name} ORDER BY id LIMIT {limit} OFFSET {offset}"
                params = ()

            request.env.cr.execute(sql, params)
            record_ids = [row[0] for row in request.env.cr.fetchall()]

            if record_ids:
                records = model_obj.sudo().browse(record_ids)
            else:
                records = model_obj.sudo().browse([])

        except Exception as e:
            return request.make_response(
                json.dumps({'error': str(e)}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )

        model_fields = model_obj._fields
        data = []
        for rec in records:
            rec_data = {}
            for fld in allowed_fields:
                field = model_fields.get(fld)
                if field:
                    try:
                        rec_data[fld] = serialize_field(rec, fld, field)
                    except Exception:
                        continue
            data.append(rec_data)

        try:
            if request.env.cr.status == "in_failed_transaction":
                request.env.cr.rollback()
        except Exception:
            request.env.cr.rollback()

        request.env['api.access.log'].sudo().create({
            'api_key_id': api_key.id,
            'endpoint': endpoint.url_path,
            'status': 'success',
            'ip_address': ip_address,
            'query_string': query_string,
        })

        # ✅ Add total count in response header
        return request.make_response(
            json.dumps(data),
            headers=[
                ('Content-Type', 'application/json'),
                ('X-Total-Count', str(len(data)))
            ]
        )

    def _unauthorized(self, endpoint_path, ip_address, query_string):
        request.env['api.access.log'].sudo().create({
            'api_key_id': False,
            'endpoint': endpoint_path,
            'status': 'unauthorized',
            'ip_address': ip_address,
            'query_string': query_string,
        })
        return request.make_response(
            json.dumps({'error': 'Unauthorized'}),
            status=401,
            headers=[('Content-Type', 'application/json')]
        )