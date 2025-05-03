from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Project(models.Model):
    _name = 'panexlogi.project'
    _description = 'panexlogi.project'
    _rec_name = "project_name"

    project_name = fields.Char(string='Project Name', required=True)
    project_code = fields.Char(string='Project code', required=True)
    project_type = fields.Many2one('panexlogi.project.type', string='Project Type')
    customer = fields.Many2one('res.partner', string='Partner Name', required=True)
    productids = fields.One2many('panexlogi.project.product', 'projectid', string='Product lines')
    group = fields.Many2one('res.groups', string='Group')
    warehouse = fields.Many2many('stock.warehouse', string='Warehouse')
    payee_company = fields.Many2one('res.partner', string='Company', tracking=True,
                                    domain="[('is_company', '=', True),('category_id.name', 'ilike', 'company')]")
    remark = fields.Text(string='Remark')

    clearance_price_rule = fields.Boolean(string='Depend on Container Count')
    clearance_entry_price = fields.Float(string='Entry Item', default=0)
    clearance_extra_price = fields.Float(string='Extra Item', default=0)
    clearance_vat_rate = fields.Float(string='Rate of VAT(%)', default=0)

    handling_service_charge = fields.Boolean(string='Handling Service Charge')
    handling_service_fee = fields.Float(string='Service Fee', default=0)
    handling_vat_rate = fields.Float(string='Rate of VAT(%)', default=0)

    inbound_operating_fix = fields.Boolean(string='Fix Inbound Operating Fee')
    inbound_operating_fixfee_per_pallet = fields.Float(string='Per Pallte')

    inbound_trucking_fix = fields.Boolean(string='Fix Inbound Operating Fee')
    inbound_trucking_fixfee_per_pallet = fields.Float(string='Per Container')

    outbound_operating_fix = fields.Boolean(string='Fix Outbound Operating Fee')
    outbound_operating_fixfee_per_pallet = fields.Float(string='Per Pallte')

    # 生成明细
    """
    @api.model
    def create(self, value):
        
        生成跟踪单号

        args_list = []
        # products = ['Customs Clearance', 'Import Handling']

        product_id = self.env['product.product'].sudo().search([('categ_id', '=', 11)])
        if product_id:
            for producta in product_id:
                args_list.append((0, 0, {
                    'product_id': producta.id,
                    'vatRate': 0,
                }))  # 建立odoo规定的关联关系！！
        value['productids'] = args_list  # 给关联字段赋值
        return super(Project, self).create(value)
    """


class ProjectPorducts(models.Model):
    _name = 'panexlogi.project.product'
    _description = 'Project.product'

    product_id = fields.Many2one('product.product', string='Product')
    vatRate = fields.Float(string='Rate of VAT(%)')
    remark = fields.Text(string='Remark')
    projectid = fields.Many2one('panexlogi.project')


class ProjectPorductName(models.Model):
    _name = 'panexlogi.project.productname'
    _description = 'Project.productname'

    name = fields.Char('Name')

class ProjectType(models.Model):
    _name = 'panexlogi.project.type'
    _description = 'Project Type'
    _rec_name = "name"

    name = fields.Char('Name')
    remark = fields.Text('Remark')
    projectid = fields.Many2one('panexlogi.project')
