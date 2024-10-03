from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Project(models.Model):
    _name = 'panexlogi.project'
    _description = 'Project'
    _rec_name = "project_name"

    project_name = fields.Char(string='Project Name', required=True)
    customer = fields.Many2one('res.partner', string='Partner Name', required=True)
    productids = fields.One2many('panexlogi.project.product', 'projectid', string='Product lines')
    group = fields.Many2one('res.groups', string='Group')

    # 生成明细
    @api.model
    def create(self, value):
        """
        生成跟踪单号
        """
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
