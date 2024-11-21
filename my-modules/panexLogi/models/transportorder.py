from odoo import _, models, fields, api, exceptions
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

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.transport.order', times)
        values['state'] = 'new'
        return super(TransportOrder, self).create(values)

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
