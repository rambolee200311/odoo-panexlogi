from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 结算账单
class SettleBill(models.Model):
    _name = 'panexlogi.finance.settlebill'
    _description = 'panexlogi.finance.settlebill'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Code', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True)
    date = fields.Date(string="Date", required=True)
    remark = fields.Text(string='Remark', tracking=True)
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')

    customs_clearance_amount = fields.Float(string='Customs Clearance（欧元）',
                                            default=0, compute='_compute_customs_clearance_amount',
                                            store=True,
                                            tracking=True)
    import_handling_amount = fields.Float(string='Import Handling（欧元）',
                                          default=0, compute='_compute_customs_handling_amount',
                                          store=True,
                                          tracking=True)

    inbound_amount = fields.Float(string='Inbound Operating（欧元）',
                                  default=0, compute='_compute_inbound_amount', store=True, tracking=True)
    outbound_amount = fields.Float(string='Outbound Operating（欧元）',
                                   default=0, compute='_compute_outbound_amount', store=True, tracking=True)
    operating_amount = fields.Float(string='Operating（欧元）',
                                    default=0)

    trucking_amount = fields.Float(string='Trucking（欧元）',
                                   default=0, tracking=True)
    warehousing_amount = fields.Float(string='Warehousing（欧元）',
                                      default=0, tracking=True)
    delivery_amount = fields.Float(string='Delivery（欧元）',
                                   default=0, compute='_compute_delivery_amount', store=True, tracking=True)
    total_amount = fields.Float(string='Amount of Total（欧元）',
                                default=0, compute='_compute_amount', store=True, tracking=True)
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
    color = fields.Integer()

    clearanceids = fields.One2many('panexlogi.finance.settlebill.clearance',
                                   'settlebill_billno',
                                   string='clearance lines')
    handlingids = fields.One2many('panexlogi.finance.settlebill.handling',
                                  'settlebill_billno',
                                  string='handling lines')
    inboundids = fields.One2many('panexlogi.finance.settlebill.inbound',
                                 'settlebill_billno',
                                 string='inbound lines')
    outboundids = fields.One2many('panexlogi.finance.settlebill.outbound',
                                  'settlebill_billno',
                                  string='outbound lines')
    deliveryids = fields.One2many('panexlogi.finance.settlebill.delivery',
                                  'settlebill_billno',
                                  string='delivery lines')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.finance.settlebill', times)
        values['state'] = 'new'
        return super(SettleBill, self).create(values)

    """
        confirm paid 状态下不可删除
        ↓↓↓    
        """

    def unlink(self):
        if self.state in ['confirm', 'received']:
            raise UserError('You cannot delete a record with state: %s' % self.state)
        return super(SettleBill, self).unlink()

    @api.depends('clearanceids.amount')
    def _compute_customs_clearance_amount(self):
        for rec in self:
            rec.customs_clearance_amount = 0
            if rec.clearanceids:
                rec.customs_clearance_amount = sum(rec.clearanceids.mapped('amount'))

    @api.depends('handlingids.amount')
    def _compute_customs_handling_amount(self):
        for rec in self:
            rec.import_handling_amount = 0
            if rec.handlingids:
                rec.import_handling_amount = sum(rec.handlingids.mapped('amount'))

    @api.depends('inboundids.amount')
    def _compute_inbound_amount(self):
        for rec in self:
            rec.inbound_amount = 0
            if rec.inboundids:
                rec.inbound_amount = sum(rec.inboundids.mapped('amount'))

    @api.depends('outboundids.amount')
    def _compute_outbound_amount(self):
        for rec in self:
            rec.outbound_amount = 0
            if rec.outboundids:
                rec.outbound_amount = sum(rec.outboundids.mapped('amount'))

    @api.depends('deliveryids.amount')
    def _compute_delivery_amount(self):
        for rec in self:
            rec.delivery_amount = 0
            if rec.deliveryids:
                rec.delivery_amount = sum(rec.deliveryids.mapped('amount'))

    @api.depends('customs_clearance_amount',
                 'import_handling_amount',
                 'inbound_amount',
                 'outbound_amount',
                 'trucking_amount',
                 'warehousing_amount',
                 'delivery_amount')
    def _compute_amount(self):
        for rec in self:
            rec.total_amount = 0
            rec.total_amount = (rec.customs_clearance_amount
                                + rec.import_handling_amount
                                + rec.inbound_amount
                                + rec.outbound_amount
                                + rec.trucking_amount
                                + rec.warehousing_amount
                                + rec.delivery_amount)

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

    def action_received_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can received Confirm Order"))
            else:
                rec.state = 'received'
                return True

    def action_unreceived_order(self):
        for rec in self:
            if rec.state != 'received':
                raise UserError(_("You only can unreceived Received Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_renew_order(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You only can renew Concel Order"))
            else:
                rec.state = 'new'
                return True