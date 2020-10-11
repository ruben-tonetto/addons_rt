# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

class PurchaseSubcontractReceiveWizard(models.TransientModel):
    _name = "purchase.subcontract.receive.wizard"
    _description = "Wizard - Assign Workorder To Subcontract"

    name = fields.Char('Name', related="order_id.name")
    order_id = fields.Many2one('purchase.order', 'Purchase Order')
    line_ids = fields.One2many('purchase.subcontract.receive.line.wizard', 'wizard_id', 'Lines')

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
        for line in self.line_ids:
            if line.qty_received <= 0:
                continue
            line.workorder_id.qty_producing = line.qty_received
            line.workorder_id.record_production()
            line.purchase_line_id.qty_received += line.qty_received
            line.workorder_id.production_id.post_inventory()
            if not line.workorder_id.next_work_order_id and line.workorder_id.qty_remaining <= 0:
                line.workorder_id.production_id.button_mark_done()

class PurchaseSubcontractReceiveLineWizard(models.TransientModel):
    _name = 'purchase.subcontract.receive.line.wizard'

    wizard_id = fields.Many2one("purchase.receive.subcontract.wizard")

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line')
    workorder_id = fields.Many2one('mrp.workorder', 'Workorder')
    product_id = fields.Many2one('product.product', related='workorder_id.product_id', string='Product')
    qty_remaining = fields.Float(string="Remaining Qty", digits=dp.get_precision('Product Unit of Measure'))
    qty_received = fields.Float(string="Received Qty", digits=dp.get_precision('Product Unit of Measure'))
