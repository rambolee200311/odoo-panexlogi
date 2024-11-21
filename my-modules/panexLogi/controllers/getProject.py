from odoo import http
from odoo.http import request
class GetProjectList(http.Controller):
    @http.route('/getProjectList', type='json', auth="user", cors="*", csrf=False)
    def getProjectList(self, **kw):
        # dingdan_h = 4900145711
        projects = request.env['panexlogi.project'].sudo().search([])  # 随便找个模型查询一条数据

        if not projects:
            back_data = {'code': 300, 'msg': 'project 不存在'}
            return (back_data)

        projectlist = []
        for r in projects:
            project = {
                "id": r.id,
                "code": r.project_code,
                "name": r.project_name,
            }
            projectlist.append(project)
        data = {
            "result": projectlist
        }
        back_data = {'code': 100, 'msg': '查询project成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)