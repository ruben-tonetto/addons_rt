
from odoo import fields, models, api


class MrpWorkorderUpdate(models.TransientModel):
    _name = 'mrp.workorder.update'
    _description = 'Update Workorders'

    mrp_workorder_ids = fields.Many2many(
        comodel_name='mrp.workorder',
        relation='mrp_workorder_compute_rel',
        column1='wizard_id',
        column2='mrp_workorder_id',
        string='Workorder Lines')
    new_subcontract_product_id = fields.Many2one('product.product', string='Subcontracting Product')
    new_subcontract_ok = fields.Boolean(string='Subcontracting Production', default=False)
    new_subcontract_partner_id = fields.Many2one('res.partner', string='Subcontracting Partner',
                                                 domain="[('supplier', '=', True)]")

    @api.model
    def default_get(self, field_names):
        defaults = super(MrpWorkorderUpdate, self).default_get(field_names)
        defaults['mrp_workorder_ids'] = self.env.context['active_ids']
        return defaults

    @api.multi
    def _reopen_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'}

    @api.multi
    def workorder_update(self, vals):
        for wo in self.mrp_workorder_ids:
            wo.subcontract_ok = self.new_subcontract_ok
            if self.new_subcontract_partner_id:
                wo.subcontract_partner_id = self.new_subcontract_partner_id.id
            if self.new_subcontract_product_id:
                wo.subcontract_product_id = self.new_subcontract_product_id.id
        return True
