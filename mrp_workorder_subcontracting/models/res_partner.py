# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    subcontract_location_id = fields.Many2one('stock.location',
                                  string=_('Subcontracting Location'), index=True,
                                  help=_('Location for Subcontracting'))
