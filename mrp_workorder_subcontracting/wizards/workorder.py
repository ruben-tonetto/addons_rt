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
            self.partner_id = self.purchase_order_id.partner_id

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id.subcontract_location_id:
            self.location_dest_id = self.partner_id.subcontract_location_id
        else:
            self.location_dest_id = False

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
            if not self.partner_id:
                self.partner_id = wo.subcontract_partner_id
                self.onchange_partner()

    @api.multi
    def assign(self):
        if not self.workorder_ids:
            raise UserError('No Workorders found!')

        if self.new_purchase_order:
            po = self.env['purchase.order'].create({
                'partner_id': self.partner_id.id,
                'date_planned': self.date_planned_finished,
                'order_type': self.env.ref('mrp_workorder_subcontracting.po_type_subcontracting').id,
                'subcontract_location_id': self.location_dest_id.id,
            })
        else:
            po = self.purchase_order_id

        workorders = self.workorder_ids
        # subcontract
        for wo in workorders:
            if wo.subcontract_line_id:
                workorders -= wo
                continue
            # subcontracting ok
            if not wo.subcontract_ok:
                raise UserError('Not Subcontract workorder : %s'
                                % (wo.product_id.name_get()[0][1]))
            # subcontracting partner
            if wo.subcontract_partner_id != self.partner_id:
                raise UserError('Subcontract partner not match for workorder: %s'
                                % (wo.product_id.name_get()[0][1]))
            # subcontracting product
            if not wo.subcontract_product_id:
                raise UserError('No subcontract product found for workorder: %s'
                                % (wo.product_id.name_get()[0][1]))
            # create purchase order line
            po_line_values = {
                'product_id': wo.subcontract_product_id.id,
                'product_qty': wo.qty_production,
                'product_uom': wo.product_uom_id.id,
                'price_unit': 0,
                'date_planned': self.date_planned_finished,
                'order_id': po.id,
                'name': wo.name,
                'production_id': wo.production_id.id,
                'production_product_id': wo.production_id.product_id.id,
                'workorder_id': wo.id,
            }
            po_line = self.env['purchase.order.line'].create(po_line_values)
            po_line._onchange_quantity()
            # assign to workorder purchase line for subcontract
            wo.subcontract_line_id = po_line.id

        return {
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'res_id': po.id,
            'views': [(self.env.ref('purchase.purchase_order_form').id, 'form')],
        }
