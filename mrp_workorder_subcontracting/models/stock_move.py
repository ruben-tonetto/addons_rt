# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    subcontract_line_id = fields.Many2one('purchase.order.line',
        'Subcontract Order Line', ondelete='set null', index=True, readonly=True)