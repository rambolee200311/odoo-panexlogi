from odoo import models, fields, api, tools


class ProjectItemAnalysisReport(models.Model):
    _name = 'project.item.analysis.report'
    _description = 'Project Item Analysis Report'
    _auto = False  # Use SQL view

    date = fields.Date(string='Date')
    project_id = fields.Many2one('panexlogi.project', string='Project')
    project_name = fields.Char(string='Project Name', related='project_id.project_name', store=True)
    fitem_id = fields.Many2one('panexlogi.fitems', string='Item')
    fitem_name = fields.Char(string='Item Name', related='fitem_id.name', store=True)
    pay_amount = fields.Float(string='Paid')
    invoice_amount = fields.Float(string='Invoiced')
    balance_amount = fields.Float(string='Balance', compute='_compute_balance', store=True)

    @api.depends('pay_amount', 'invoice_amount')
    def _compute_balance(self):
        for rec in self:
            rec.balance_amount = rec.invoice_amount - rec.pay_amount

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW project_item_analysis_report AS (
                -- Payments from Payment Application Lines
                SELECT
                    CONCAT('pay_', pal.id) AS id,
                    pa.date AS date,
                    pal.project AS project_id,
                    proj.project_name AS project_name,
                    pal.fitem AS fitem_id,
                    fitems.name AS fitem_name,
                    SUM(pal.amount) AS pay_amount,
                    0 AS invoice_amount,
                    -SUM(pal.amount) AS balance_amount
                FROM panexlogi_finance_paymentapplicationline pal
                JOIN panexlogi_finance_paymentapplication pa ON pal.payapp_billno = pa.id
                LEFT JOIN panexlogi_project proj ON pal.project = proj.id
                LEFT JOIN panexlogi_fitems fitems ON pal.fitem = fitems.id
                WHERE pa.state != 'cancel' AND pal.amount != 0
                GROUP BY pa.date, pal.project, proj.project_name, pal.fitem, fitems.name, pal.id
                UNION ALL
                -- Invoices from AR Invoice Lines
                SELECT
                    CONCAT('inv_', aril.id) AS id,
                    ar.invoice_date AS date,
                    ar.project AS project_id,
                    proj.project_name AS project_name,
                    aril.fitem AS fitem_id,
                    fitems.name AS fitem_name,
                    0 AS pay_amount,
                    SUM(aril.invoice_amount) AS invoice_amount,
                    SUM(aril.invoice_amount) AS balance_amount
                FROM panexlogi_ar_invoice_line aril
                JOIN panexlogi_ar_invoice ar ON aril.ar_invoice_id = ar.id
                LEFT JOIN panexlogi_project proj ON ar.project = proj.id
                LEFT JOIN panexlogi_fitems fitems ON aril.fitem = fitems.id
                WHERE ar.state != 'cancel' AND aril.invoice_amount != 0
                GROUP BY ar.invoice_date, ar.project, proj.project_name, aril.fitem, fitems.name, aril.id
            )
        ''')