# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        # if not res: validate has been done
        # if res, validate has not been done (an action is returned for immediate transfer)
        if not res:
            self.subcontracting_validate()
        return res

    def subcontracting_validate(self):

        if self.picking_type_id.id == self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_out').id:
            virtual = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)

            picking_in = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_in').id,
                'location_id': self.location_dest_id.id,
                'location_dest_id': virtual.id,
            })
            purchase_id = self.move_lines[0].purchase_line_id.order_id
            for move in self.move_lines.mapped('purchase_line_id').mapped('workorder_id').mapped('move_raw_ids'):
                move.location_id = self.location_dest_id
                move.picking_id = picking_in

            purchase_id.subcontract_picking_in_id = picking_in
        elif self.picking_type_id.id == self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_in').id:
            po = self.env['purchase.order'].search([('subcontract_picking_in_id', '=', self.id)])
            if not po:
                raise UserError('No Purchase order found for picking %s' % self.name)
            if po.state != "purchase":
                raise UserError('To validate this picking the related purchase %s must be confirmed' % po.name)

            # versamento di produzione
            for wo in self.move_lines.mapped('workorder_id'):
                wo.record_production()
                wo.production_id.post_inventory()
                if not wo.next_work_order_id:
                    wo.production_id.button_mark_done()




class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        for picking in self.pick_ids:
            picking.subcontracting_validate()
        return res