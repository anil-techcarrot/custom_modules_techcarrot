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

        # API KEY VALIDATION
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

        # FIND CORRECT FIELD NAME FOR ALLOWED COMPANIES
        # Tries all possible field names used in different Odoo custom modules
        allowed_companies = []

        for field_name in ['company_ids', 'allowed_company_ids', 'company_id']:
            if field_name in api_key._fields:
                field = api_key._fields[field_name]
                if field.type in ('many2many', 'one2many'):
                    allowed_companies = api_key[field_name].ids
                elif field.type == 'many2one':
                    val = api_key[field_name]
                    allowed_companies = [val.id] if val else []
                if allowed_companies:
                    _logger.info("API KEY: using field '%s' => companies: %s", field_name, allowed_companies)
                    break

        # SAFETY: if still empty, block the request
        if not allowed_companies:
            return request.make_response(
                json.dumps({'error': 'No companies configured for this API key'}),
                status=403,
                headers=[('Content-Type', 'application/json')]
            )

        # APPLY COMPANY CONTEXT
        model_obj = model_obj.sudo().with_context(
            allowed_company_ids=allowed_companies
        )

        # DOMAIN FILTER — only allowed companies, no URL override
        domain = []
        if 'company_id' in model_obj._fields:
            domain.append(('company_id', 'in', allowed_companies))

        # TOTAL COUNT
        total_count = model_obj.search_count(domain)

        # Remove duplicates at DB level
        record_ids = model_obj.search(
            domain,
            limit=limit,
            offset=offset,
            order='id'
        ).ids

        # Remove any duplicate IDs
        unique_ids = list(dict.fromkeys(record_ids))
        records = model_obj.sudo().browse(unique_ids)


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