# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        # if not res: validate has been done
        # if res, validate has not been done (an action is returned for immediate transfer or backorder)
        if not res:
            self.subcontracting_validate()
        return res

    def subcontracting_validate(self):
        if self.picking_type_id.id == self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_out').id:
            for move in self.move_lines.mapped('purchase_line_id').mapped('workorder_id').mapped('move_raw_ids'):
                move.location_id = self.location_dest_id

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        for picking in self.pick_ids:
            picking.subcontracting_validate()
        return res

