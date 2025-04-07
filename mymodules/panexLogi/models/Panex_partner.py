from odoo import models, fields, api


class Partner(models.Model):
    # _name = 'panex.shippingline'
    # _description = 'Shipping Line'
    _inherit = 'res.partner'

    panex_code = fields.Char(string='Contact Code')
    shipline = fields.Boolean("Shipping(船公司)", default=False)
    project = fields.Boolean("project（项目）", default=False)
    receiver = fields.Boolean("Receiver（收货方）", default=False)
    truck = fields.Boolean("Truck（卡车公司）", default=False)
    agency = fields.Boolean("Agency（代理）", default=False)


# panex partner bankinfo
class PartnerBankinfo(models.Model):
    _name = 'panexlogi.partner.bankinfo'
    _description = 'panexlogi.partner.bankinfo'
    _rec_name = "bic"

    odoo_name = fields.Char(string='Odoo Name')
    fi_name = fields.Char(string='FI Name')
    panex_kvknr = fields.Char(string='KvKnr')
    panex_btwnummer = fields.Char(string='BTW-nummer')
    iban = fields.Char(string='IBAN')
    bic = fields.Char(string='BIC')
    error = fields.Char(string='Error')
    partner_id = fields.Many2one('res.partner', string='Partner')

    # get partner id
    def get_partner_id(self):
        selected_partner = self.browse(self.env.context.get('active_ids'))
        for record in selected_partner:
            if record.odoo_name:
                partner = self.env['res.partner'].search([('name', '=', record.odoo_name)])
                if partner:
                    record.partner_id = partner.id
                else:
                    record.partner_id = False
                    record.error = 'Partner not found'
            else:
                partner = self.env['res.partner'].create({
                    'name': record.fi_name,
                    'is_company': True, })
                if partner:
                    record.partner_id = partner.id

    # set partner name
    def set_partner_name(self):
        selected_partner = self.browse(self.env.context.get('active_ids'))
        for record in selected_partner:
            if record.partner_id:
                record.partner_id.name = record.fi_name
            else:
                record.error = 'Partner not found'

    # set bank account
    def set_bank_account(self):
        selected_partner = self.browse(self.env.context.get('active_ids'))
        for record in selected_partner:
            if record.partner_id:
                if record.bic:
                    bankid = 0
                    bank = self.env['res.bank'].search([('bic', '=', record.bic)])
                    if not bank:
                        bank_new = self.env['res.bank'].create({
                            'name': record.bic,
                            'bic': record.bic,
                        })
                        bankid = bank_new.id
                    else:
                        bankid = bank.id
                    if record.iban:
                        account = self.env['res.partner.bank'].search(
                            [('partner_id', '=', record.partner_id.id), ('acc_number', '=', record.iban)])
                        if not account:
                            self.env['res.partner.bank'].create({
                                'acc_holder_name': record.fi_name,
                                'partner_id': record.partner_id.id,
                                'acc_number': record.iban,
                                'bank_id': bankid, })


            else:
                record.error = 'Partner not found'

    def set_kvknr(self):
        selected_partner = self.browse(self.env.context.get('active_ids'))
        for record in selected_partner:
            if record.partner_id:
                if record.panex_kvknr:
                    record.partner_id.x_kvknr = record.panex_kvknr
        # return successful message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'KvKnr set successfully',
                'sticky': False,
            },
        }


class Product(models.Model):
    _inherit = 'product.template'

    code = fields.Char(string='Code')
    net_weight = fields.Float(string='Net Weight')
    net_weight_unit = fields.Many2one('uom.uom', string='Net Weight Unit')
    gross_weight = fields.Float(string='Gross Weight')
    gross_weight_unit = fields.Many2one('uom.uom', string='Gross Weight Unit')
    volume = fields.Float(string='Volume')
    volume_unit = fields.Many2one('uom.uom', string='Volume Unit')
    width = fields.Float(string='Width')
    width_unit = fields.Many2one('uom.uom', string='Width Unit')
    height = fields.Float(string='Height')
    height_unit = fields.Many2one('uom.uom', string='Height Unit')
    depth = fields.Float(string='Depth')
    depth_unit = fields.Many2one('uom.uom', string='Depth Unit')
    size = fields.Char(string='Size')
    package = fields.Char(string='Package')
    k_number = fields.Char(string='K-Number')
    hs_code = fields.Char(string='HS Code')
    sku = fields.Char(string='SKU')
    model = fields.Char(string='Model')
