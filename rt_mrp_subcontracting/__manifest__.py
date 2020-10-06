# @author: Ruben Tonetto <ruben.tonetto@gmail.com>
# Copyright Ruben tonetto
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mrp Subcontracting',
    'summary': """Mrp Subcontracting""",
    'author':  'Ruben Tonetto ',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
             'mrp',
             'purchase_order_type',
             'purchase_stock',
     ],
    'data': [
         'data/stock_picking_type.xml',
         'data/purchase_order_type.xml',
         'wizards/workorder.xml',
         'wizards/mrp_routing_update_view.xml',
         'wizards/mrp_workorder_update_view.xml',
         'views/partner.xml',
         'views/purchase.xml',
         'views/mrp.xml',
     ],
    'demo': [
        'data/mrp_demo.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
 }