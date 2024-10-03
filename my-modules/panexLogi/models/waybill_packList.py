from odoo import models, fields, api


# 装船清单


class WaybillPackList(models.Model):
    _name = 'panexlogi.waybill.packlist'
    _description = 'panexlogi.waybill.packlist'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Packing List No', readonly=True)
    batch = fields.Char(string='Batch')
    interpono = fields.Char(string='Inter-Company PO Number')
    product_id = fields.Many2one('product.product', string='Product Type')
    powerperpc = fields.Integer(string='Power Per Piece')
    pcs = fields.Float(string='Pcs', required=True)
    pallets = fields.Float(string='Pallets', required=True)
    totalvo = fields.Float(string='Total Volume')
    shipping = fields.Char(string='Shipping Line')
    waybillno = fields.Char(string='B/L Number')
    waybill_billno = fields.Many2one('panexlogi.waybill')
    cntrno = fields.Char(string='Container No')
    sealno = fields.Char(string='Seal Number')
    etdport = fields.Char(string='ETD Port')
    eta = fields.Date(string='Updated ETA')
    meap = fields.Float(string='MEA / PLT')
    gwp = fields.Float(string='GW / PLT')
    gw = fields.Float(string='GW')
    mea = fields.Float(string='MEA')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.packlinglist', times)
        return super(WaybillPackList, self).create(values)

    @api.depends('waybill_billno')
    def _get_blno(self):
        for r in self:
            if r.waybill_billno:
                r.waybillno = r.waybill_billno.waybillno

    @api.model
    def name_search(self, name, args=None, operator='=', limit=None):
        """
        名称模糊搜索。
        """
        args = args or []
        domain = []
        if 'model' in self.env.context:
            if self.env.context['model'] == 'panexlogi.waybill.packlist':
                if self.env.context['waybillbillno']:
                    # domain.append(('id', 'in', self.env['panexlogi.waybill'].search(
                    #     [('project', '=', self.project)]).ids))
                    domain.append(('waybill_billno', '=', self.env.context['waybillbillno']))
        return super(WaybillPackList, self).name_search(name, domain + args, operator=operator, limit=limit)
