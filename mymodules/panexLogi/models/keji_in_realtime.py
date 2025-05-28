import logging

from .keji_token import KejiApiClient
from odoo import models, fields
from odoo.tools import json

_logger = logging.getLogger(__name__)


class KejiInRealtime(models.Model):
    _name = 'keji.in.realtime'
    _description = 'keji.in.realtime'

    order_id = fields.Char(string='订单编号', required=True)  # 对应ORDER_ID字段
    owner_id = fields.Char(string='货主ID', required=True)  # 对应OWNER_ID字段
    order_seqno = fields.Integer(string='商品序号')  # 对应ORDER_SEQNO字段
    cop_g_no = fields.Char(string='商品料号', required=True)  # 对应COP_G_NO字段
    g_name = fields.Char(string='商品名称')  # 对应G_NAME字段
    qty = fields.Float(string='数量', digits=(19, 5))  # 对应DECIMAL(19,5)类型
    qty1 = fields.Float(string='入库数', digits=(19, 5))  # 新增QTY1字段
    qty2 = fields.Float(string='上架数', digits=(19, 5))  # 新增QTY2字段
    g_unit = fields.Char(string='数量单位')  # 对应G_UNIT字段
    wh_no = fields.Char(string='仓库名')  # 对应WH_NO字段
    production_date = fields.Datetime(string='生产日期')  # 对应PRODUCTION_DATE字段
    effective_date = fields.Datetime(string='有效期至')  # 对应EFFECTIVE_DATE字段
    batch_no = fields.Char(string='批次编号')  # 对应BATCH_NO字段
    mid3 = fields.Char(string='客户订单号')  # 对应MID3字段
    mid4 = fields.Char(string='发票编号')  # 对应MID4字段
    mid5 = fields.Char(string='自定义编号')  # 对应MID5字段
    work_no = fields.Char(string='采购单编号/工作号')  # 对应WORK_NO字段
    last_indate = fields.Char(string='实际入库日期')  # 修改类型为Char，对应VARCHAR(20)

    response_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='响应状态')


class KejiInRealtimeWizard(models.TransientModel):
    _name = 'keji.in.realtime.wizard'
    _description = 'keji.in.realtime.wizard'

    order_id = fields.Char(string='订单编号', required=True, defalut='A20250522002')  # 对应ORDER_ID字段
    result = fields.Text(string='执行结果')
    error_message = fields.Text(string='错误信息')
    response_data = fields.Text(string='响应数据')

    def execute_job(self):
        self.ensure_one()
        try:
            # Initialize API client
            client = KejiApiClient(self.env)

            # Call the API
            response = client.call_realtime_job(order_id=self.order_id)
            _logger.info("In Realtime API call successful: %s", response)

            # Parse and handle the response
            if response.get('status') == 0:
                self.response_data = json.dumps(response, ensure_ascii=False, indent=4)
                self._save_response(json.loads(response['outJson']).get('t', []), self.order_id)
                self.result = "Operation successful"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'The job executed successfully.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.error_message = response.get('msg', 'Unknown error')
                _logger.error("API returned an error: %s", self.error_message)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': f"API Error: {self.error_message}",
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except json.JSONDecodeError as e:
            self.error_message = "Failed to decode API response: %s" % str(e)
            _logger.error("JSON Decode Error: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f"JSON Decode Error: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            self.error_message = str(e)
            _logger.error("API call failed: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f"Unexpected Error: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _save_response(self, data_list, order_id=None):
        if data_list:
            self.env['keji.in.realtime'].search([('order_id', '=', order_id)]).unlink()
            for item in data_list:
                # Validate and handle invalid date values
                production_date = item.get('PRODUCTION_DATE')
                effective_date = item.get('EFFECTIVE_DATE')
                production_date = production_date if production_date and production_date != '-' else None
                effective_date = effective_date if effective_date and effective_date != '-' else None

                self.env['keji.in.realtime'].create({
                    'order_id': order_id,
                    'owner_id': item.get('OWNER_ID'),
                    'order_seqno': item.get('ORDER_SEQNO'),
                    'cop_g_no': item.get('COP_G_NO'),
                    'g_name': item.get('G_NAME'),
                    'qty': item.get('QTY'),
                    'qty1': item.get('QTY1'),
                    'qty2': item.get('QTY2'),
                    'g_unit': item.get('G_UNIT'),
                    'wh_no': item.get('WH_NO'),
                    'production_date': production_date,  # Use validated value
                    'effective_date': effective_date,  # Use validated value
                    'batch_no': item.get('BATCH_NO'),
                    'mid3': item.get('MID3'),
                    'mid4': item.get('MID4'),
                    'mid5': item.get('MID5'),
                    'work_no': item.get('WORK_NO'),
                    'last_indate': item.get('LASTINDATE'),
                    'response_status': 'success'
                })
