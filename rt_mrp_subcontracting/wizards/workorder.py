# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class WorkorderAssignSubcontract(models.TransientModel):
    _name = "workorder.assign.subcontract.wizard"
    _description = "Wizard - Assign Workorder To Subcontract"

    partner_id = fields.Many2one('res.partner', 'Partner', domain="[('supplier', '=', True)]")
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order')
    new_purchase_order = fields.Boolean('New Purchase Order?', default=True)
    workorder_ids = fields.Many2many(comodel_name='mrp.workorder', string='Workorders')
    location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination', required=True)
    date_planned_finished = fields.Datetime('Scheduled Date Finished', required=True)

    @api.onchange('purchase_order_id', 'workorder_ids')
    def _onchange_purchase_order(self):
        if self.purchase_order_id:
            self.location_dest_id = self.purchase_order_id.subcontract_picking_out_id.location_dest_id
            self.partner_id = self.purchase_order_id.partner_id

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id.subcontract_location_id:
            self.location_dest_id = self.partner_id.subcontract_location_id

    @api.model
    def default_get(self, field_names):
        defaults = super(WorkorderAssignSubcontract, self).default_get(field_names)
        defaults['workorder_ids'] = self.env.context['active_ids']
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

    @api.onchange('workorder_ids')
    def onchange_workorder_ids(self):
        if self.workorder_ids:
            wo = self.workorder_ids[0]
            if not self.location_id and wo.move_raw_ids:
                self.location_id = wo.move_raw_ids[0].location_id
            if not self.date_planned_finished or self.date_planned_finished > wo.production_id.date_planned_finished:
                self.date_planned_finished = wo.production_id.date_planned_finished

    @api.multi
    def assign(self):
        if not self.workorder_ids:
            raise UserError('No Workorders found!')

        virtual = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)

        if self.new_purchase_order:
            picking_out = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_out').id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            })

            picking_in = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': self.env.ref('rt_mrp_subcontracting.subcontracting_picking_type_in').id,
                'location_id': self.location_dest_id.id,
                'location_dest_id': virtual.id,
            })

            po = self.env['purchase.order'].create({
                'partner_id': self.partner_id.id,
                'date_planned': self.date_planned_finished,
                'subcontract_picking_out_id': picking_out.id,
                'subcontract_picking_in_id': picking_in.id,
                'order_type': self.env.ref('rt_mrp_subcontracting.po_type_subcontracting').id
            })
        else:
            po = self.purchase_order_id
            picking_out = po.subcontract_picking_out_id
            picking_in = po.subcontract_picking_in_id

        existing_moves = picking_in.move_lines
        workorders = self.workorder_ids
        # subcontract
        for wo in workorders:
            if wo.subcontract_line_id:
                workorders -= wo
                continue
            # memo subcontracting product
            if not wo.subcontract_product_id:
                raise UserError('No subcontract product found for workorder: %s'
                                % (wo.product_id.name_get()[0][1]))
            # create purchase order line
            po_line_values = {
                'product_id': wo.subcontract_product_id.id,
                'name': wo.name,
                'product_qty': wo.qty_production,
                'product_uom': wo.product_uom_id.id,
                'production_id': wo.production_id.id,
                'price_unit': 0,
                'date_planned': self.date_planned_finished,
                'order_id': po.id,
            }
            po_line = self.env['purchase.order.line'].create(po_line_values)
            po_line.onchange_product_id()
            po_line.product_qty = wo.qty_production
            wo.subcontract_line_id = po_line.id

            #if not workorders:
            #    raise UserError('No workorders have been added to purchase order')

            # materials

            new_moves = workorders.mapped("move_raw_ids")
            move_ids = new_moves - existing_moves

            # move quants raw materials for each workorder from location_id to location_dest_id of subcontractor
            for move in move_ids:
                if move.location_id != self.location_id:
                    raise UserError('All products must be picked up from the same source location!')
                if move.picking_id:
                    raise UserError('The workorder %s has been already assigned!' % move.workorder_id.name)
                # memo subcontracting product
                if move.workorder_id.subcontract_product_id:
                    subcontract_product_id = move.workorder_id.subcontract_product_id
                else:
                    raise UserError('No subcontract product found for product: %s'
                                    % (move.workorder_id.product_id.name_get()[0][1]))

                # stock move to subcontracting location
                out_values = {
                    'name': move.product_id.name_get()[0][1],
                    'product_id': move.product_id.id,
                    'product_uom': move.product_uom.id,
                    'product_uom_qty': move.product_qty,
                    'date': fields.Datetime.now(),
                    'state': 'confirmed',
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'picking_id': picking_out.id,
                    'purchase_line_id': po_line.id,
                }
                self.env['stock.move'].create(out_values)

                # puntare la move nel magazzino esterno e inserirla nel picking ** NON QUI, MA NELLA VALIDAZIONE DEL PICKING **
                move.write({
                    'picking_id': picking_in.id,
                })


        return {
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'res_id': po.id,
            'views': [(self.env.ref('purchase.purchase_order_form').id, 'form')],
        }
