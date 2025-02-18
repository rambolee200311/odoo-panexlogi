from odoo import _, models, fields, api, exceptions, tools
from odoo.exceptions import UserError

'''
    Transport Order
'''


class TransportOrder(models.Model):
    _name = 'panexlogi.transport.order'
    _description = 'panexlogi.transport.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Order Date', default=fields.Date.today)
    project = fields.Many2one('panexlogi.project', string='Project', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code', readonly=True)
    waybill_billno = fields.Many2one('panexlogi.waybill', string='Waybill No inner')
    waybillno = fields.Char(string='Waybill No', related='waybill_billno.waybillno', readonly=True)

    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)

    cargodesc = fields.Text(string='Cargo Description')

    collterminal = fields.Many2one('panexlogi.terminal', string='Collection Terminal')
    collterminal_code = fields.Char(string='Collection Terminal Code', related='collterminal.terminal_code',
                                    readonly=True)
    coldate = fields.Date(string='Collection Date')
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    unlolocation = fields.Char(string='Unloaded Location')
    unlodate = fields.Date(string='Unloaded Date')

    dropterminal = fields.Many2one('panexlogi.terminal', string='Empty Container Drop-off Terminal')
    dropterminal_code = fields.Char(string='Drop-off Terminal Code', related='dropterminal.terminal_code',
                                    readonly=True)

    drop_off_planned_date = fields.Date(string='Drop-off Planned Date')

    special_instructions = fields.Text(string='Special Instructions')
    additional_comments = fields.Text(string='Additional Comments')

    remark = fields.Text(string='Remark')
    transportorderdetailids = fields.One2many('panexlogi.transport.order.detail', 'transportorderid',
                                              string='Container NO')
    transportorderotherdocs_ids = fields.One2many('panexlogi.transport.order.otherdocs', 'billno', string='Other Docs')

    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('received', 'Received'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="Status",
        tracking=True
    )
    arrived_date = fields.Date(string='Arrived Date')

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.transport.order', times)
        values['state'] = 'new'
        return super(TransportOrder, self).create(values)

    # 发邮件给卡车公司
    def action_send_email(self):
        template_id = self.env.ref('panexLogi.email_template_transport_order').id
        self.env['mail.template'].browse(template_id).send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Email sent successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    # 生成入库单
    def action_create_inbound_order(self):
        # 生成入库订单
        owarehouse = 0
        iwarehouse = 0
        transport_order_details = []
        for record in self:
            for detail in record.transportorderdetailids:
                if owarehouse != detail.warehouse.id and detail.warehouse.id:
                    owarehouse = detail.warehouse.id
                    transport_order_detail = self.env['panexlogi.transport.order.detail'].search(
                        [('warehouse', '=', owarehouse)])
                    transport_order_details.append(transport_order_detail)
            for order_detail in transport_order_details:
                # inbound_order_product_ids

                detail_list = []
                for rec in order_detail:
                    # way bill pack list
                    packlist = self.env['panexlogi.waybill.packlist'].search(
                        [('cntrno', '=', rec.cntrno)])
                    for pack in packlist:
                        detail_list.append((0, 0, {
                            'cntrno': pack.cntrno,
                            'product_id': pack.product_id.id,
                            'batch': pack.batch,
                            'pcs': pack.pcs,
                            'pallets': pack.pallets,
                        }))
                    iwarehouse = rec.warehouse.id
                    # inbound_order
                order = {
                    'date': fields.Date.today(),
                    'project': record.project.id,
                    'warehouse': iwarehouse,
                    'inbound_order_product_ids': detail_list,
                }
                self.env['panexlogi.inbound.order'].create(order)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Inbound Order create successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.constrains('waybill_billno')
    def _check_waybillno_id(self):
        for r in self:
            domain = [
                ('waybill_billno', '=', r.waybill_billno.id),
                ('state', '!=', 'cancel'),
                ('id', '!=', r.id),
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('waybill_billno must be unique per transport order!'))

    # 维护到港实际日期 跳转wizard视图
    def add_actual_date(self):
        return {
            'name': 'Actual Arrival Date',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.transport.order.arrived.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_billno': self.id},
        }


class TransportOrderDetail(models.Model):
    _name = 'panexlogi.transport.order.detail'
    _description = 'panexlogi.transport.order.detail'

    cntrno = fields.Char(string='Container NO')
    coldate = fields.Date(string='Collection Date')
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    unlolocation = fields.Char(string='Unloaded Location')
    unlodate = fields.Date(string='Unloaded Date')
    dropterminal = fields.Many2one('panexlogi.terminal', string='Empty Container Drop-off Terminal')
    dropterminal_code = fields.Char(string='Drop-off Terminal Code', related='dropterminal.terminal_code',
                                    readonly=True)
    drop_off_planned_date = fields.Date(string='Drop-off Planned Date')
    special_instructions = fields.Text(string='Special Instructions')
    additional_comments = fields.Text(string='Additional Comments')
    remark = fields.Text(string='Remark')

    transportorderid = fields.Many2one('panexlogi.transport.order', string='Transport Order')

    state = fields.Selection(selection=[
        ('new', 'New'),
        ('arrived', 'Arrived'),
    ],
        default='new',
        string="Status",
        tracking=True
    )
    arrived_date = fields.Date(string='Arrived Date')


# 其他附件
class TransportOrderOtherDocs(models.Model):
    _name = 'panexlogi.transport.order.otherdocs'
    _description = 'panexlogi.transport.order.otherdocs'

    description = fields.Text(string='Description')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File name')
    billno = fields.Many2one('panexlogi.transport.order', string='Transport Order BillNo')


class TransportOrderArrivedWizard(models.TransientModel):
    _name = 'panexlogi.transport.order.arrived.wizard'
    _description = 'panexlogi.transport.order.arrived.wizard'

    arrived_date = fields.Date(string='Arrived Date', default=fields.Date.today)
    billno = fields.Many2one('panexlogi.transport.order', string='Transport Order', required=True)
    cntrnos = fields.Many2many('panexlogi.transport.order.cntrnos'
                               , string='Container NOs'
                               , relation='transport_order_arrived_cntro_rel'
                               , domain="[('transport_order_id', '=', billno)]")
    """
    @api.onchange('billno')
    def _onchange_billno(self):
        if self.billno.billno:
            return {'domain': {'cntrnos': [('billno', '=', self.billno.billno)]}}
        else:
            return {'domain': {'cntrnos': []}}
    """

    def apply_changes(self):
        for cntrno in self.cntrnos:
            detail = self.billno.transportorderdetailids.filtered(lambda x: x.cntrno == cntrno.cntrno)
            detail.state = 'arrived'  # Example operation: update state to 'arrived'
            detail.arrived_date = self.arrived_date
        return {'type': 'ir.actions.act_window_close'}


class TransportOrderCntrnos(models.Model):
    _name = 'panexlogi.transport.order.cntrnos'
    _description = 'Transport Order Cntrno Report'
    _auto = False
    _rec_name = 'cntrno'

    cntrno = fields.Char(string='Container NO')
    transport_order_id = fields.Integer(string='Transport Order ID')
    billno = fields.Char(string='BillNo')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
                CREATE OR REPLACE VIEW panexlogi_transport_order_cntrnos AS (
                    SELECT
                        row_number() OVER () AS id,
                        d.cntrno AS cntrno,
                        o.id as transport_order_id,
                        o.billno as billno
                    FROM
                    panexlogi_transport_order o
                    join panexlogi_transport_order_detail d on o.id = d.transportorderid
                    where o.state = 'confirm'   )
        """)
