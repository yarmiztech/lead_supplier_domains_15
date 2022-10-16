# -*- coding: utf-8 -*-
{
    'name': "Supplier domain",
    'author':
        'Enzapps Private Limited',
    'summary': """
This module will help to Supplier domain in Lead
""",

    'description': """
This module will help to Supplier domain in Lead
    """,
    'website': "",
    'category': 'base',
    'version': '14.0',
    'depends': ['base','account',"stock","sale","contacts","crm_enquirys_lead","alshab_custom","demoerp_sales_flow_s15",'crm'],
    "images": ['static/description/icon.png'],
    'data': [
        'security/ir.model.access.csv',
        'views/demo_sales.xml',
        'views/comparision.xml'
           ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
