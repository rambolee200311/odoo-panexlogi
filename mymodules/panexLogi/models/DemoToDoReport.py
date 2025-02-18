from odoo import api, fields, models


class DemoToDoReport(models.Model):
    _name = "panexlogi.demotodo.report"
    _description = "Demo ToDo Report"
    _auto = False

    id = fields.Integer(string='ID', readonly=True)
    billno = fields.Char(string='Bill No', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', readonly=True)
    receiver = fields.Many2one('res.users', string='receiver', readonly=True)
    date = fields.Date(string='Bill Date', readonly=True)
    ddate = fields.Date(string='Due Date', readonly=True)
    state = fields.Char(string="State", readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    totalpieces = fields.Integer(string='Total pieces', readonly=True)
    eurtotal = fields.Float(string='Total_of_EUR', readonly=True)

    # with
    def _with_demotod(self):
        return ""

    # select
    def _select_demotod(self):
        select_ = f"""
        a.id,a.receiver, a.billno, a.date, a.ddate, a.state, a.project,
	    b.product_id,b.totalpieces,b.eurtotal
        """
        return select_

    # from
    def _from_demotod(self):
        from_ = f"""
            panexlogi_demotodo a
            inner join panexlogi_demotodo_packlist b on a.id=b.demotodono
            inner join product_product p on b.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            """
        return from_

    # where
    def _where_demotod(self):
        return "a.id>0"

    # group
    def _group_by_demotod(self):
        group_ = f"""
                a.id,a.receiver, a.billno, a.date, a.ddate, a.state, a.project,
        	    b.product_id,b.totalpieces,b.eurtotal
                """
        return group_

    def _query(self):
        with_ = self._with_demotod()
        where_ = self._where_demotod()
        return f"""
               {"WITH" + with_ + "(" if with_ else ""}
               SELECT {self._select_demotod()}
               FROM {self._from_demotod()}
               WHERE {self._where_demotod()}
               GROUP BY {self._group_by_demotod()}
               {")" if with_ else ""}
           """

    @property
    def _table_query(self):
        return self._query()

"""
class DemoToDoPrintModel(models.AbstractModel):
    _name = 'report.panexLogi.demotodo_printmodel'  # report.模块名+(Qweb模板)看板视图id
    _description = 'DemoToDo打印'

    def _get_report_values(self, docids, data=None):
        docs = self.env['panexlogi.demotodo'].sudo().browse(docids)
        return {
            'docs': docs,
        }
"""
