import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class WeComMainController(http.Controller):

    @http.route('/wecom/callback', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def wecom_callback_main(self, **kwargs):
        """
        Main WeCom callback endpoint that routes to project-specific handlers
        """
        try:
            # Get message signature and timestamp for verification
            msg_signature = kwargs.get('msg_signature', '')
            timestamp = kwargs.get('timestamp', '')
            nonce = kwargs.get('nonce', '')
            echostr = kwargs.get('echostr', '')

            _logger.info(f"WeCom callback received: msg_signature={msg_signature}, timestamp={timestamp}")

            # URL verification (GET request)
            if request.httprequest.method == 'GET':
                return self._verify_url(msg_signature, timestamp, nonce, echostr)

            # Message handling (POST request)
            elif request.httprequest.method == 'POST':
                return self._handle_message(msg_signature, timestamp, nonce)

        except Exception as e:
            _logger.error(f"WeCom callback error: {str(e)}")
            return Response(json.dumps({'error': 'Internal server error'}), status=500)

    def _verify_url(self, msg_signature, timestamp, nonce, echostr):
        """
        Verify WeCom callback URL
        """
        try:
            # Get all projects with WeCom configuration
            projects = request.env['panexlogi.project'].sudo().search([
                ('wecom_token', '!=', False),
                ('wecom_encoding_aes_key', '!=', False)
            ])

            for project in projects:
                # In a real implementation, you would use WeCom SDK to verify signature
                # This is a simplified version
                if self._verify_signature(project, msg_signature, timestamp, nonce, echostr):
                    # Return echostr for URL verification
                    return Response(echostr, content_type='text/plain')

            _logger.warning("No matching project found for WeCom verification")
            return Response('Verification failed', status=400)

        except Exception as e:
            _logger.error(f"URL verification error: {str(e)}")
            return Response('Verification error', status=500)

    def _handle_message(self, msg_signature, timestamp, nonce):
        """
        Handle WeCom message callbacks
        """
        try:
            # Get raw POST data
            raw_data = request.httprequest.get_data().decode('utf-8')
            _logger.info(f"Received WeCom message: {raw_data}")

            # Parse and decrypt message
            decrypted_msg = self._decrypt_message(msg_signature, timestamp, nonce, raw_data)
            if not decrypted_msg:
                return Response('Message decryption failed', status=400)

            # Route to appropriate project handler
            return self._route_to_project_handler(decrypted_msg)

        except Exception as e:
            _logger.error(f"Message handling error: {str(e)}")
            return Response(json.dumps({'error': 'Message processing failed'}), status=500)

    def _route_to_project_handler(self, message_data):
        """
        Route message to the appropriate project-specific handler
        """
        # Extract project identifier from message (this depends on your WeCom setup)
        project_identifier = message_data.get('AgentID') or message_data.get('ToUserName')

        if project_identifier:
            # Find project by WeCom Agent ID
            project = request.env['panexlogi.project'].sudo().search([
                ('wecom_agent_id', '=', project_identifier)
            ], limit=1)

            if project:
                # Call project-specific handler
                return request.env['panexlogi.project.wecom.handler'].sudo().handle_project_message(project,
                                                                                                    message_data)

        # Default handler if no specific project found
        return self._handle_default_message(message_data)

    def _verify_signature(self, project, msg_signature, timestamp, nonce, echostr):
        """
        Verify WeCom signature (simplified - implement proper verification)
        """
        # TODO: Implement proper signature verification using WeCom SDK
        # This should verify that the message comes from WeCom and is for this project
        return True  # Placeholder

    def _decrypt_message(self, msg_signature, timestamp, nonce, encrypted_msg):
        """
        Decrypt WeCom message (simplified - implement proper decryption)
        """
        # TODO: Implement proper message decryption using WeCom SDK
        try:
            # Parse JSON message
            message_data = json.loads(encrypted_msg)
            return message_data
        except:
            return None

    def _handle_default_message(self, message_data):
        """
        Handle messages that don't match any specific project
        """
        msg_type = message_data.get('MsgType', '')

        if msg_type == 'text':
            # Echo text messages for testing
            content = message_data.get('Content', '')
            return Response(json.dumps({
                'status': 'success',
                'message': f'Received: {content}'
            }), content_type='application/json')

        return Response(json.dumps({'status': 'success'}), content_type='application/json')