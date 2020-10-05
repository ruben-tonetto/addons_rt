from odoo import models, fields, api


class MrpRoutingUpdate(models.TransientModel):
    _name = 'mrp.routing.update'
    _description = 'Update Routing Lines'

    routing_ids = fields.Many2many(
        comodel_name='mrp.routing.workcenter',
        string='Routings')
    new_subcontract_product_id = fields.Many2one('product.product', string='Subcontracting Product')
    new_subcontract_ok = fields.Boolean(string='Subcontracting Production', default=False)
    new_subcontract_partner_id = fields.Many2one('res.partner', string='Subcontracting Partner',
                                                 domain="[('supplier', '=', True)]")

    @api.model
    def default_get(self, field_names):
        defaults = super(MrpRoutingUpdate, self).default_get(field_names)
        defaults['routing_ids'] = self.env.context['active_ids']
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
    def routing_update(self, vals):
        for ro in self.routing_ids:
            ro.subcontract_ok = self.new_subcontract_ok
            if self.new_subcontract_partner_id:
                ro.subcontract_partner_id = self.new_subcontract_partner_id.id
            if self.new_subcontract_product_id:
                ro.subcontract_product_id = self.new_subcontract_product_id.id
        return True
