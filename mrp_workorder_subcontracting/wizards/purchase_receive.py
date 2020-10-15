# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
from datetime import datetime

class PurchaseSubcontractReceiveWizard(models.TransientModel):
    _name = "purchase.subcontract.receive.wizard"
    _description = "Wizard - Assign Workorder To Subcontract"

    name = fields.Char('Name', related="order_id.name")
    order_id = fields.Many2one('purchase.order', 'Subcontract Order')
    line_ids = fields.One2many('purchase.subcontract.receive.line.wizard', 'wizard_id', 'Lines')
    date_received = fields.Datetime('Date Received Material', required=True, default=datetime.now())

    def fill_quantities(self):
        for line in self.line_ids:
            line.qty_received = line.qty_remaining

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'}

    @api.onchange('order_id')
    def onchange_order_id(self):
        if not self.order_id:
            return

        lines = []
        for po_line in self.order_id.order_line:
            qty_remaining = po_line.product_qty - po_line.qty_received
            if qty_remaining <= 0:
                continue
            lines.append((0, 0, {
                'purchase_line_id': po_line.id,
                'workorder_id': po_line.workorder_id.id,
                'qty_remaining': qty_remaining,
            }))

        self.write({
            'line_ids': lines
        })

    def process(self):
        lines_to_do = self.line_ids.filtered(lambda l: l.qty_received > 0)
        if lines_to_do:
            picking_in = self.env['stock.picking'].create({
                'partner_id': self.order_id.partner_id.id,
                'picking_type_id': self.env.ref('mrp_workorder_subcontracting.subcontracting_picking_type_in').id,
                'location_id': self.order_id.subcontract_location_id.id,
                'location_dest_id': self.order_id.picking_type_id.default_location_dest_id.id,
            })

            wos = []
            finished_move_ids = []
            for line in lines_to_do:
                finished_moves = line.workorder_id.production_id.move_finished_ids.filtered(
                    lambda m: m.state not in ['done', 'cancel'])
                finished_moves.write({
                        'purchase_line_id': line.purchase_line_id.id,
                    })
                line.workorder_id.qty_producing = line.qty_received
                wos.append(line.workorder_id.id)
                line.workorder_id.record_production()
                finished_move_ids += finished_moves.ids

            wos = self.env['mrp.workorder'].browse(wos)
            wos.mapped('production_id').post_inventory()  # to be done together for creating one backorder picking
            self.env["stock.move"].browse(finished_move_ids).write({
                        'picking_id': picking_in.id,
                    })

            for line in lines_to_do:
                if not line.workorder_id.next_work_order_id and line.workorder_id.qty_remaining <= 0:
                    line.workorder_id.production_id.button_mark_done()
                line.purchase_line_id.qty_received = sum(move.quantity_done for move in line.purchase_line_id.move_ids)

            #picking_in.write({'state': 'done', 'date': self.date_received})


class PurchaseSubcontractReceiveLineWizard(models.TransientModel):
    _name = 'purchase.subcontract.receive.line.wizard'

    wizard_id = fields.Many2one("purchase.receive.subcontract.wizard")

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    product_id = fields.Many2one('product.product', related='workorder_id.product_id', string='Product')
    qty_remaining = fields.Float(string="Remaining Qty", digits=dp.get_precision('Product Unit of Measure'))
    qty_received = fields.Float(string="Received Qty", digits=dp.get_precision('Product Unit of Measure'))
