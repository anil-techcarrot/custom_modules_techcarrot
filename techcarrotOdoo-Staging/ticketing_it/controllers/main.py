from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from werkzeug.utils import redirect as werkzeug_redirect
import logging

_logger = logging.getLogger(__name__)


class MicrosoftSSOHome(Home):

    @http.route('/web/session/logout', type='http', auth='none', website=True)
    def logout(self, redirect='/web/login', **kwargs):
        """
        Custom logout controller to handle Microsoft (Azure) SSO logout.

        Flow:
        1. Detect if user logged in via Microsoft OAuth.
        2. Build Microsoft logout URL dynamically.
        3. Logout from Odoo session.
        4. Redirect to Microsoft logout endpoint.
        5. Fallback to default Odoo login redirect if not SSO user.
        """

        microsoft_logout_url = None

        try:
            # Get current logged-in user ID from session
            uid = request.session.uid

            if uid:
                # Fetch user record securely using sudo()
                user = request.env['res.users'].sudo().browse(uid)

                # Check if user exists AND is logged in via OAuth (Microsoft SSO)
                if user.exists() and user.oauth_uid:

                    # Get base URL of Odoo (used for redirect after logout)
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

                    # Fetch OAuth provider configuration (Microsoft)
                    provider = request.env['auth.oauth.provider'].sudo().search(
                        [('id', '=', user.oauth_provider_id.id)], limit=1
                    )

                    # Default tenant (used if parsing fails)
                    tenant_id = 'common'

                    # Extract tenant ID from Microsoft auth endpoint
                    # Example endpoint:
                    # https://login.microsoftonline.com/<tenant_id>/oauth2/v2.0/authorize
                    if provider and provider.auth_endpoint:
                        parts = provider.auth_endpoint.split('/')
                        for i, part in enumerate(parts):
                            if 'login.microsoftonline.com' in part and i + 1 < len(parts):
                                tenant_id = parts[i + 1]
                                break

                    # Construct Microsoft logout URL
                    # This ensures user is logged out from Azure as well
                    microsoft_logout_url = (
                        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
                        f"?post_logout_redirect_uri={base_url}/web/login"
                    )

                    _logger.info(
                        "Azure SSO: Logging out user %s and redirecting to Microsoft logout",
                        user.login
                    )

        except Exception as e:
            # Catch any unexpected errors to avoid breaking logout flow
            _logger.error("Azure SSO: Logout hook error: %s", e)

        # ----------------------------------------
        # STEP 1: Always logout from Odoo session
        # ----------------------------------------
        request.session.logout(keep_db=True)

        # ----------------------------------------
        # STEP 2: Redirect to Microsoft logout (if SSO user)
        # ----------------------------------------
        if microsoft_logout_url:
            return werkzeug_redirect(microsoft_logout_url, code=302)

        # ----------------------------------------
        # STEP 3: Fallback (non-SSO users)
        # Redirect to standard Odoo login page
        # ----------------------------------------
        return werkzeug_redirect(
            f"{request.httprequest.host_url.rstrip('/')}{redirect}",
            code=302
        )