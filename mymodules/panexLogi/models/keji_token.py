import hashlib
import logging
from datetime import datetime, timedelta

import requests

from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools import json

_logger = logging.getLogger(__name__)


class KejiToken(models.Model):
    _name = 'keji.token'
    _description = 'keji.token'
    _order = 'expire_date desc'

    token = fields.Char(string='TOKEN', required=True)
    expire_date = fields.Datetime(string='EXPIRE DATA', required=True)
    app_id = fields.Char(string='APP ID', default='AFA9FD3298C6416EBCA6F5DA60747AE5')


class KejiSignature(models.Model):
    _name = 'keji.signature'
    _description = 'keji.signature'

    data = fields.Text(string='DATA', required=True)
    signature = fields.Char(string='MD5 SIGNATRUE', required=True)
    response = fields.Text(string='API RESPONSE', help='RESPONSE')


class KejiApiClient:
    def __init__(self, env):
        self.env = env
        self._base_url = self._get_config_param('keji-base_url', 'https://wms.keji-info.com/api')
        self._salt = self._get_config_param('keji-salt')[:32]
        self._app_id = self._get_config_param('keji-app_id', 'AFA9FD3298C6416EBCA6F5DA60747AE5')

    def get_token(self):
        """获取或刷新认证令牌"""
        # token_record = self.env['keji.token'].search([], order='expire_date desc', limit=1)
        # if token_record and token_record.expire_date > datetime.now():
        #     return token_record.token

        # 构建认证请求数据
        auth_data = {'app_id': self._app_id}
        auth_headers = {'Content-Type': 'application/json'}

        # 发送认证请求
        response = requests.post(
            f"{self._base_url}/Token/GetToken",
            json=auth_data,
            headers=auth_headers
        )
        response.raise_for_status()
        token_info = response.json()['outJson']
        _logger.debug("TOKEN INFO: %s", token_info)

        expire_min = token_info['expires_in']

        # 保存新令牌
        self.env['keji.token'].create({
            'token': token_info['app_token'],
            'expire_date': datetime.now() + timedelta(seconds=expire_min),
            'app_id': self._app_id
        })
        return token_info['app_token']

    def call_realtime_job(self, order_id):
        """调用实时作业接口"""
        url = f"{self._base_url}/KJWmsWebApi/InRealTimeJob"
        token = self.get_token()

        # make signature data
        sign_data = {"ORDER_ID": order_id, "START_LASTINDATE": "2023-05-01", "END_LASTINDATE": "", "MID1": "",
                     "OWNER_ID": ""}
        # Step 1: Create the request body
        json_data = self.get_source_str(sign_data)  # Convert the dictionary to a formatted string
        _logger.debug("Request Body: %s", json_data)

        # Step 2: Create the headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': token,
            'AppID': self._app_id,
            'Authorizations': self.generate_md5_signature(json_data, self._salt, False)
        }
        _logger.debug("Request Headers: %s", headers)

        # Step 3: Make the POST request
        try:
            response = requests.post(
                url,
                data=json_data,  # Use the pre-created request body
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            _logger.debug("API URL: %s", url)
            _logger.debug("API HEAD: %s", headers)
            _logger.debug("API REQUEST Body: %s", response.request.body)
            _logger.debug("API RESPONSE: %s", response)
        except requests.exceptions.RequestException as e:
            _logger.error("API REQUEST FAILED: %s", e)
            raise UserError(f"API REQUEST FAILED: {str(e)}") from e

        # 处理响应
        try:
            response.encoding = 'utf-8'  # Ensure the response is decoded as UTF-8
            result = response.json()
            if result.get('status') != 0:
                raise ValueError(f"API STATUS ERROR: {result.get('msg', 'no message')}")
        except ValueError as ve:
            _logger.error("API VALUE ERROR: %s", ve)
            raise UserError(f"API VALUE ERROR: {str(ve)}") from ve

        return result

    def get_source_str(self, source: dict) -> str:
        """
        将字典转换为特定格式的字符串
        :param source: 字典数据
        :return: 格式化后的字符串
        """
        # Convert dictionary to sorted JSON string
        if isinstance(source, dict):
            source_str = json.dumps(source, sort_keys=True, separators=(',', ':'))
        elif isinstance(source, str):
            source_str = source
        else:
            _logger.error("Invalid source type: %s", type(source))
            raise TypeError("Source must be a dictionary or string.")
            # Replace single quotes with double quotes
        _logger.debug("MD5 Source String: %s", source_str)
        return source_str

    def generate_md5_signature(self, source: str, salt: str, to_upper: bool = False) -> str:
        """
        生成与Java兼容的MD5签名（含特殊位运算处理）
        :param source: 原始数据
        :param salt: 盐值
        :param to_upper: 是否转大写
        :return: 32位MD5签名
        """

        # Truncate the salt to the first 32 characters
        truncated_salt = salt[:32]

        # Concatenate source and salt
        combined_data = f"{source}{truncated_salt}".encode('utf-8')
        _logger.debug("MD5 Combined Data: %s", combined_data)
        # Compute MD5 hash
        # md5_hash = hashlib.md5(combined_data).digest()
        md5_hash = hashlib.md5(combined_data).hexdigest()

        # Format the hash to match Java's behavior
        # formatted = ''.join(f"{(b & 0xFF):02x}" for b in md5_hash)

        # Return the hash in uppercase if required
        # return formatted.upper() if to_upper else formatted
        return md5_hash.upper() if to_upper else md5_hash

    def _get_config_param(self, key, default=None):
        """安全获取配置参数"""
        param_value = self.env['ir.config_parameter'].sudo().get_param(key, default)
        _logger.debug("GET PARAMETER VALUE: %s = %s", key, param_value)
        return param_value
