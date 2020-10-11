# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    subcontract_picking_out_id = fields.Many2one('stock.picking', string=_('Subcontract Pick Out'))
    subcontract_location_id = fields.Many2one('stock.location',
                                  string=_('Subcontracting Location'), index=True,
                                  help=_('Location for Subcontracting'))

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
    def action_view_picking(self):
        if self.order_type.id == self.env.ref('rt_mrp_subcontracting.po_type_subcontracting').id:
            if self.subcontract_picking_out_id.state != "done":
                raise UserError("You have to confirm Picking Out before proceeding with material receipt")

            wizard = self.env['purchase.subcontract.receive.wizard'].create({
                'order_id': self.id,
            })

            wizard.onchange_order_id()
            return {
                "name": "Subcontract Receive Wizard",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': "purchase.subcontract.receive.wizard",
                'type': 'ir.actions.act_window',
                'res_id': wizard.id,
                'target': 'new',
            }
        return super(PurchaseOrder, self).action_view_picking()

    def button_confirm(self):
        for order in self:
            if order.order_type.id != self.env.ref('rt_mrp_subcontracting.po_type_subcontracting').id:
                continue
            if order.subcontract_picking_out_id:
                raise UserError("Picking Out already assigned to order %s " % order.name)

            out_moves = []
            location_id = False  # set while processing the first workorder
            for po_line in order.order_line:
                for move in po_line.workorder_id.move_raw_ids:
                    if move.picking_id:
                        # raise UserError('The workorder %s has been already assigned!' % move.workorder_id.name)
                        continue
                    if not location_id:
                        location_id = move.location_id
                    else:
                        if location_id != move.location_id:
                            raise ("All moves must come from the same location id")
                    # stock move to subcontracting location
                    out_values = {
                        'name': move.product_id.name_get()[0][1],
                        'product_id': move.product_id.id,
                        'product_uom': move.product_uom.id,
                        'product_uom_qty': move.product_qty,
                        'date': fields.Datetime.now(),
                        'state': 'confirmed',
                        'location_id': location_id.id,
                        'location_dest_id': order.subcontract_location_id.id,
                        'purchase_line_id': po_line.id,
                    }
                    out_moves.append((0, 0, out_values))

            picking_out = self.env['stock.picking'].create({
                'partner_id': order.partner_id.id,
                'picking_type_id': self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_out').id,
                'location_id': location_id.id,
                'location_dest_id': order.partner_id.subcontract_location_id.id,
                'move_lines': out_moves
            })
            order.subcontract_picking_out_id = picking_out

        return super(PurchaseOrder, self).button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    workorder_id = fields.Many2one('mrp.workorder', string="Work Order")
    production_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    production_product_id = fields.Many2one('product.product', related="production_id.product_id",
                                            store=True, string="Manufacturing Product")

    @api.multi
    def unlink(self):
        for line in self.filtered(lambda l: l.order_id.order_type == self.env.ref('rt_mrp_subcontracting.po_type_subcontracting')):
            if line.workorder_id:
                line.workorder_id.subcontract_line_id = False
                if line.order_id.subcontract_picking_out_id:
                    line.order_id.subcontract_picking_out_id.move_lines.filtered(lambda m: m.workorder_id == line.workorder_id).unlink()
        res = super().unlink()
        return res
