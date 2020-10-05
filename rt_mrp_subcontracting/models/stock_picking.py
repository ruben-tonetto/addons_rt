# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        for pick in self:
            if pick.picking_type_id.id == self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_in').id:
                po = self.env['purchase.order'].search([('subcontract_picking_in_id', '=', pick.id)])
                if not po:
                    raise UserError('No Purchase order found for picking %s' % pick.name)
                if po.state != "purchase":
                    raise UserError('To validate this picking the related purchase %s must be confirmed' % po.name)

                # versamento di produzione
                for production in pick.move_lines.mapped('workorder_id.production_id'):
                    produce = self.env['mrp.product.produce'].with_context({
                        'active_id': production.id,
                    }).create({
                        'product_id': production.product_id.id,
                        'product_uom_id': production.product_uom_id.id,
                        'product_qty': production.product_uom_qty,
                    })
                    produce.do_produce()
                    production.button_mark_done()
        return res
