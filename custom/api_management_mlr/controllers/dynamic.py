# -*- coding: utf-8 -*-
import logging
from odoo import http, fields
from odoo.http import request
import json

_logger = logging.getLogger(__name__)


def serialize_field(record, field_name, field):
    value = record[field_name]

    if field.type in ('char', 'text', 'selection', 'integer', 'float', 'boolean', 'monetary'):
        return value

    elif field.type in ('date', 'datetime'):
        return value.isoformat() if value else value

    elif field.type == 'many2one':
        if value:
            rec = value
            name = rec.display_name if hasattr(rec, 'display_name') else str(rec.id)
            return {'id': rec.id, 'name': name}
        return None

    elif field.type in ('one2many', 'many2many'):
        return [{'id': r.id, 'name': r.display_name} for r in value]

    elif field.type == 'binary':
        return bool(value)

    return str(value)


class DynamicAPI(http.Controller):

    @http.route('/api/<string:endpoint_path>', auth='none', type='http', methods=['GET'], csrf=False)
    def dynamic_api_handler(self, endpoint_path, **kwargs):

        api_key_value = request.params.get('key')
        limit = int(kwargs.get('limit', 500))
        offset = int(kwargs.get('offset', 0))

        # 🔐 API KEY VALIDATION
        api_key = request.env['res.api.key'].sudo().search([
            ('key', '=', api_key_value),
            ('active', '=', True),
            '|', ('expiry_date', '=', False),
            ('expiry_date', '>=', fields.Date.today())
        ], limit=1)

        if not api_key:
            return request.make_response(
                json.dumps({'error': 'Unauthorized'}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        endpoint = request.env['res.api.endpoint'].sudo().search([
            ('url_path', '=', endpoint_path),
            ('active', '=', True),
            ('api_key_ids', 'in', api_key.id),
        ], limit=1)

        if not endpoint:
            return request.make_response(
                json.dumps({'error': 'Invalid endpoint'}),
                status=404,
                headers=[('Content-Type', 'application/json')]
            )

        model_obj = request.env[endpoint.model_id.model]

        # ✅ COMPANY FILTER (MULTI COMPANY SUPPORT)
        allowed_companies = api_key.company_ids.ids or request.env.user.company_ids.ids

        if not allowed_companies:
            allowed_companies = request.env['res.company'].sudo().search([]).ids

        # ✅ APPLY CONTEXT (NO force_company)
        model_obj = model_obj.sudo().with_context(
            allowed_company_ids=allowed_companies
        )

        # ✅ DOMAIN FILTER
        domain = []
        if 'company_id' in model_obj._fields:
            domain.append(('company_id', 'in', allowed_companies))

        # ✅ OPTIONAL: FILTER BY COMPANY FROM URL
        company_param = kwargs.get('company_id')
        if company_param:
            domain = [('company_id', '=', int(company_param))]

        # ✅ TOTAL COUNT
        total_count = model_obj.search_count(domain)

        # ✅ FETCH DATA WITH PAGINATION
        records = model_obj.search(
            domain,
            limit=limit,
            offset=offset,
            order='id'
        )

        # ✅ SERIALIZE DATA
        data = []
        for rec in records:
            rec_data = {}
            for fld in endpoint.field_ids.mapped('name'):
                field = model_obj._fields.get(fld)
                if field:
                    try:
                        rec_data[fld] = serialize_field(rec, fld, field)
                    except Exception:
                        continue
            data.append(rec_data)

        return request.make_response(
            json.dumps(data),
            headers=[
                ('Content-Type', 'application/json'),
                ('X-Total-Count', str(total_count))
            ]
        )