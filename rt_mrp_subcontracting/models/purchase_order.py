# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    subcontract_picking_out_id = fields.Many2one('stock.picking', string=_('Subcontract Pick Out'))
    subcontract_picking_in_id = fields.Many2one('stock.picking', string=_('Subcontract Pick In'))

    @api.multi
    def action_view_subcontract_picking_out(self):
        return {
            'name': 'Purchase Order',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.subcontract_picking_out_id.id
        }

    @api.multi
    def action_view_subcontract_picking_in(self):
        return {
            'name': 'Purchase Order',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.subcontract_picking_in_id.id
        }

    def button_confirm(self):
        for order in self:
            if order.order_type.id != self.env.ref('rt_mrp_subcontracting.po_type_subcontracting').id:
                continue
            if order.subcontract_picking_out_id:
                if order.subcontract_picking_out_id.state not in ['done', 'cancel']:
                    order.subcontract_picking_out_id.action_assign()
                    order.subcontract_picking_out_id.button_validate()
                order.subcontract_picking_in_id.move_lines.write({
                    'location_id': order.subcontract_picking_in_id.location_id.id,
                })
        return super(PurchaseOrder, self).button_confirm()

    @api.multi
    def button_cancel(self):
        for order in self:
            if order.subcontract_picking_in_id:
                order.subcontract_picking_in_id.move_lines.write({"picking_id":  False})
                order.subcontract_picking_in_id.action_cancel()
            if order.subcontract_picking_out_id:
                order.subcontract_picking_out_id.action_cancel()
        super(PurchaseOrder, self).button_cancel()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    workorder_id = fields.Many2one('mrp.workorder', string="Work Order")
    production_id = fields.Many2one('mrp.production', string="Manufactoring Order")
    production_product_id = fields.Many2one('product.product', related="production_id.product_id",
                                            store=True, string="Manufactoring Product")
