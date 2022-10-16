# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime

class ComparisionPQ(models.Model):
    _name = 'comparision.pq'
    _order = "id desc"

    date = fields.Date(string='Create Date', default=fields.Date.context_today)
    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    ledger_lines = fields.One2many('comparision.pq.lines', 'compare_id')

    def send_email(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        for each in self.ledger_lines.filtered(lambda a:a.compared == True).mapped('purchase_id'):
            ctx.update({
                'default_model': 'purchase.order',
                'active_model': 'purchase.order',
                'active_id': each.ids[0],
                'default_res_id': each.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'custom_layout': "mail.mail_notification_paynow",
                'force_email': True,
                'mark_rfq_as_sent': True,
            })

            # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
            # object. Therefore, we pass the model description in the context, in the language in which
            # the template is rendered.
            lang = self.env.context.get('lang')
            if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
                template = self.env['mail.template'].browse(ctx['default_template_id'])
                if template and template.lang:
                    lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

            self = self.with_context(lang=lang)
            # if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
            # else:
            #     ctx['model_description'] = _('Purchase Order')

            return {
                'name': _('Compose Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }



class ComparisionPqLines(models.Model):
    _name = 'comparision.pq.lines'

    compare_id = fields.Many2one('comparision.pq')
    purchase_id = fields.Many2one('purchase.order')
    purchase_line_id = fields.Many2one('purchase.order.line')
    product_id = fields.Many2one('product.product')
    quantity = fields.Float(string="Quantity")
    price = fields.Float(string="Price")
    compared = fields.Boolean(default=False,string="Selected")
    partner_id = fields.Many2one('res.partner')

    @api.onchange('price')
    def _onchange_prices(self):
        self.purchase_line_id.price_unit = self.price

    def send_email(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        for each in self.compare_id.ledger_lines.filtered(lambda a: a.compared == True).mapped('purchase_id'):
        # for each in self.purchase_id:
            each.write({'po_state':'approve'})
            for remove_line in self.compare_id.ledger_lines.filtered(lambda a:a.purchase_id == each and a.compared == False):
                remove_line.unlink()
            for line in each.order_line:
                line.price_unit = self.price
            ctx.update({
                'default_model': 'purchase.order',
                'active_model': 'purchase.order',
                'active_id': each.ids[0],
                'default_res_id': each.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'custom_layout': "mail.mail_notification_paynow",
                'force_email': True,
                'mark_rfq_as_sent': True,
            })

            # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
            # object. Therefore, we pass the model description in the context, in the language in which
            # the template is rendered.
            lang = self.env.context.get('lang')
            if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
                template = self.env['mail.template'].browse(ctx['default_template_id'])
                if template and template.lang:
                    lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

            self = self.with_context(lang=lang)
            # if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
            # else:
            #     ctx['model_description'] = _('Purchase Order')

            return {
                'name': _('Compose Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }



class SalesOrders(models.Model):
    _inherit = "sales.orders"

    rig = fields.Char("Rig#")

    def amount_words(self):
        # amount_total_words = self.company_id.currency_id.amount_to_text(self.amount_total)
        return self.company_id.currency_id.amount_to_text(self.amount_total)

    def action_confirm(self):
        res = super(SalesOrders, self).action_confirm()
        for each in self.demo_quotes_ids:
            for i in each.order_line:
                ref_po = self.env['purchase.order'].search([('name', '=', i.supplier_po)])
                for po_line in ref_po.order_line:
                    po_line.reference_number = i.reference_number
                    po_line.remarks = i.remarks
        return res

    @api.onchange('demo_quotes_ids')
    def _onchange_demo_quotes_ids(self):
        product_list = []

        for sale in self.demo_quotes_ids:
            if self.rig:
                self.rig = self.rig+','+sale.rig
            else:
                self.rig = sale.rig

            # for line in sale.order_line.filtered(lambda a: a.qty_delivered < a.product_uom_qty):
            for line in sale.order_line.filtered(lambda a: a.sale_demo < a.product_uom_qty):
                supplier_id = self.env['res.partner']
                tax_amount = 0
                supplier_id_price = 0
                if line.tax_id:
                    tax_amount = line.price_subtotal * line.tax_id.amount / 100
                supplier = self.env["product.supplierinfo"].search(
                    [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)],
                    limit=1)
                if supplier:
                    supplier_id = supplier.name.id
                    supplier_id_price = supplier.price
                if line.sale_demo:
                    product_qty = line.product_uom_qty - line.sale_demo
                    price_subtotal = line.price_unit * product_qty
                else:
                    product_qty = line.product_uom_qty
                    price_subtotal = line.price_unit * product_qty
                line_dict = (0, 0, {
                    'price_unit': line.price_unit,
                    'sale_line_id': line._origin.id,
                    'product_uom_qty': product_qty,
                    'product_id': line.product_id.id,
                    'categ_id': line.categ_id.id,
                    'c_pn': line.c_pn,
                    'on_hand': line.on_hand,
                    'c_mfr': line.c_mfr,
                    'part_number_mfr': line.c_mfr,
                    'reference_number': line.reference_number,
                    'remarks': line.remarks,
                    'availability': line.availability,
                    'description': line.name,
                    'uom_id': line.product_id.uom_id.id,
                    'part_number': line.part_number,
                    'price_subtotal': price_subtotal,
                    'tax_amount': tax_amount,
                    'supplier_id': line.supplier_new.id,
                    # 'supplier_id': supplier_id,
                    'supplier_price': line.supplier_price_new,
                    'tax_id': [(6, 0, line.sudo().tax_id.ids)]})

                product_list.append(line_dict)
            if sale.customer_reference:
                self.customer_reference = sale.customer_reference
        self.sale_order_lines = False
        self.sale_order_lines = product_list
        self.amount_untaxed = sum(self.sale_order_lines.mapped('price_subtotal'))
        self.amount_tax = sum(self.sale_order_lines.mapped('tax_amount'))
        self.amount_total = sum(self.sale_order_lines.mapped('price_subtotal')) + sum(
            self.sale_order_lines.mapped('tax_amount'))

class SalesOrdersLines(models.Model):
    _inherit = "sales.orders.lines"


    categ_id = fields.Many2one('product.category', string="Category")
    c_mfr = fields.Char(string="C.MFR")
    c_pn = fields.Char(string="C.P/N")
    on_hand = fields.Float(string="On Hand")
    part_number_mfr =  fields.Char(string="Mfr.Part")
    reference_number = fields.Char('Ref. No.')
    remarks = fields.Char('Remarks')
    availability = fields.Char('Availability')
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    c_mfr = fields.Char(string="C.MFR")
    c_pn = fields.Char(string="C.P/N")
    categ_id = fields.Many2one('product.category', string="Category")
    part_number_mfr =  fields.Char(string="Mfr.Part")
    reference_number = fields.Char('Ref. No.')
    remarks = fields.Char('Remarks')
    availability = fields.Char('Availability')

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('po_number')
    def _onchange_po_number(self):
        if self.po_number:
            for pos in self.po_number:
                product_list = []
                customer_pos_data = self.env['sales.orders'].search([('po_number.name', '=', pos.name)])
                if customer_pos_data:
                    suppliers = customer_pos_data.sale_order_lines.mapped('supplier_id')
                    if suppliers:
                        self.partner_id = suppliers[0]
                        if self.customer_reference == False:
                           self.customer_reference=''
                        if customer_pos_data.customer_reference:
                            self.customer_reference +=customer_pos_data.customer_reference+' '
                    for line in customer_pos_data.sale_order_lines:
                        if line.supplier_id == self.partner_id:
                            tax_ids = self.env['account.tax']
                            if self.local_vendor_type == 'local':
                                tax_ids = self.env['account.tax'].search(
                                    [('name', '=', 'Vat 15%'), ('type_tax_use', '=', 'purchase')])

                            line_dict = (0, 0, {
                                'price_unit': line.sale_line_id.supplier_price_new,
                                'product_qty': line.product_uom_qty,
                                'product_id': line.product_id.id,
                                'part_number': line.part_number,
                                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'product_uom': line.product_id.uom_id.id,
                                'name': line.description,
                                'sales_orders_id':customer_pos_data.id,
                                'taxes_id': [(6, 0, tax_ids.ids)]})
                            product_list.append(line_dict)
                self.order_line = product_list

class AccountInvoice(models.Model):
    _inherit = "account.move"

    ewb_number = fields.Char(string="E-Way No")
    discount = fields.Float(string="Discount")


