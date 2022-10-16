# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
import qrcode
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from uuid import uuid4


class EnquiryLine(models.Model):
    _inherit = 'enquiry.line'

    categ_id = fields.Many2one('product.category', string="Category")
    serial_number = fields.Char('Sl No.')
    part_number_mfr = fields.Char('Mfr.Part No.')
    c_mfr = fields.Char(string="C.MFR")
    c_pn = fields.Char(string="C.P/N")
    manual_desc = fields.Text(string="Description")

    @api.onchange('categ_id')
    def onchange_categ_id_names(self):
        if self.categ_id:
            products = self.env['product.product'].search([('categ_id', '=', self.categ_id.id)])
            return {'domain': {'product_id': [('id', 'in', products.ids)]}}

    @api.onchange('product_id')
    def load_vendor_names(self):
        if self.product_id:
            product = self.env['product.template'].search([('name', '=', self.product_id.name)])
            supplier_names = []
            seller_ids = []
            if product.seller_ids:
                for line in product.seller_ids:
                    supplier_names.append(line.name.name)
                    seller_ids.append(line.name.id)
                self.supplier_name = [(6, 0, seller_ids)]
                # return {'domain': {'supplier_name': [('name', 'in', supplier_names)]}}
            if self.product_id.item_description:
                self.description = self.product_id.item_description
            if self.product_id.default_code:
                self.part_number = self.product_id.default_code
            if self.product_id.part_number_mfr:
                self.part_number_mfr = self.product_id.part_number_mfr
            if self.product_id.categ_id:
                self.categ_id = self.product_id.categ_id

    @api.onchange('part_number_mfr')
    def load_part_number_mfr(self):
        if self.part_number_mfr:
            product = self.env['product.template'].search([('part_number_mfr', '=', self.part_number_mfr)])
            if product:
                supplier_names = []
                seller_ids = []
                if product.seller_ids:
                    for line in product.seller_ids:
                        supplier_names.append(line.name.name)
                        seller_ids.append(line.name.id)
                    self.supplier_name = [(6, 0, seller_ids)]
                    # return {'domain': {'supplier_name': [('name', 'in', supplier_names)]}}
                self.product_id = product.product_variant_id.id
                if self.product_id.item_description:
                    self.description = self.product_id.item_description
                if self.product_id.default_code:
                    self.part_number = self.product_id.default_code
                if self.product_id.part_number_mfr:
                    self.part_number_mfr = self.product_id.part_number_mfr
                if self.product_id.categ_id:
                    self.categ_id = self.product_id.categ_id

    @api.onchange('description')
    def load_part_item_description(self):
        if self.description:
            product = self.env['product.template'].search([('item_description', '=', self.description)])
            if product:
                supplier_names = []
                seller_ids = []
                if product.seller_ids:
                    for line in product.seller_ids:
                        supplier_names.append(line.name.name)
                        seller_ids.append(line.name.id)
                    self.supplier_name = [(6, 0, seller_ids)]
                    # return {'domain': {'supplier_name': [('name', 'in', supplier_names)]}}
                self.product_id = product.product_variant_id.id
                if self.product_id.item_description:
                    self.description = self.product_id.item_description
                if self.product_id.default_code:
                    self.part_number = self.product_id.default_code
                if self.product_id.part_number_mfr:
                    self.part_number_mfr = self.product_id.part_number_mfr
                if self.product_id.categ_id:
                    self.categ_id = self.product_id.categ_id


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    rig = fields.Char(string="RIG")

    def enquiry_purchase_single(self):
        my_check_wc_list = []
        vendors_len = len(
            self.enquiry_lines.filtered(lambda a: a.product_uom_qty > a.product_onhand_qty).mapped('supplier_name'))
        if vendors_len <= 1:

            for line in self.enquiry_lines:
                if line.product_uom_qty > line.product_onhand_qty:
                    qty = line.product_uom_qty - line.product_onhand_qty
                    product_line = (0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.description,
                        'product_qty': qty,
                        'part_number': line.part_number,
                        'price_unit': 0,
                        'c_mfr': line.c_mfr,
                        'c_pn': line.c_pn,
                        'categ_id': line.categ_id.id,
                        'part_number_mfr': line.part_number_mfr,
                        # 'reference_number':line.reference_number,
                        # 'remarks':line.remarks,
                        'availability': line.availability,
                        'state': 'draft',
                        'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'product_uom': line.product_uom.id,
                    })
                    my_check_wc_list.append(product_line)

            view_id = self.env.ref('purchase.purchase_order_form')
            return {
                'name': _('New Purchase Quotation'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'view_id': view_id.id,
                'views': [(view_id.id, 'form')],
                'context': {
                    'default_state': 'draft',
                    'default_inquiry_id': [(6, 0, self.ids)],
                    'default_customer_reference': self.customer_reference,
                    'default_order_line': my_check_wc_list,
                    'default_partner_id': self.enquiry_lines.supplier_name.id,
                }
            }
        else:
            for supl in self.enquiry_lines.mapped('supplier_name'):
                product_line = []
                my_check_wc_list = []
                for line in self.enquiry_lines.search([('crm_id', '=', self.id), ('supplier_name', '=', supl.id)]):
                    if line.product_uom_qty > line.product_onhand_qty:
                        qty = line.product_uom_qty - line.product_onhand_qty
                        product_line = (0, 0, {
                            'product_id': line.product_id.id,
                            # 'name': line.product_id.name,
                            'name': line.description,
                            'product_qty': qty,
                            'price_unit': 0,
                            'part_number': line.product_id.default_code,
                            'state': 'draft',
                            'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            'product_uom': line.product_uom.id,
                        })
                        my_check_wc_list.append(product_line)
                if my_check_wc_list:
                    self.env['purchase.order'].create({
                        'partner_id': supl.id,
                        'state': 'draft',
                        'customer_reference': self.customer_reference,
                        'inquiry_id': [(6, 0, self.ids)],
                        'order_line': my_check_wc_list
                    })

    def action_pq_compare(self):
        self.ensure_one()
        lines = []
        for purchase in self.purchase_ids:
            for line in purchase.order_line:
                product_line = (0, 0, {
                    'purchase_line_id': line.id,
                    'purchase_id': purchase.id,
                    'product_id': line.product_id.id,
                    'quantity': line.product_qty,
                    'price': line.price_unit,
                    'partner_id': purchase.partner_id.id,
                })
                lines.append(product_line)
        view_id = self.env.ref('lead_supplier_domains_15.comparision_pq_id').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'comparision.pq',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_ledger_lines': lines,
                        },
            'nodestroy': True,
        }

    def action_rfq_send(self):
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
        for each in self.purchase_ids:
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

    def action_new_quotation(self):
        res = super(CrmLead, self).action_new_quotation()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_crm.sale_action_quotations_new")
        enquiry_lines = []
        for products in self.enquiry_lines:
            approved_vendor = self.env['res.partner']
            supplier_currency = self.env['res.currency']
            supplier_po = ''
            approved_price = 0
            # if self.purchase_ids.filtered(lambda a:a.po_state == 'approve'):
            # if self.lead_crm_demo.filtered(lambda a: a.po_state == 'approve'):
            for each in products.supplier_name:
                pq_approved = self.purchase_ids.filtered(lambda a: a.po_state == 'approve' and a.partner_id == each)
                if pq_approved:
                    supplier_po = pq_approved.name
                    # approved_vendor = self.lead_crm_demo.filtered(lambda a: a.po_state == 'approve').partner_id.id
                    approved_vendor = self.purchase_ids.filtered(
                        lambda a: a.po_state == 'approve' and a.partner_id == each).partner_id.id
                    approved_price = sum(self.purchase_ids.filtered(
                        lambda a: a.po_state == 'approve' and a.partner_id == each).mapped(
                        'order_line').filtered(lambda a: a.product_id == products.product_id).mapped('price_unit'))
                    supplier_currency = self.purchase_ids.filtered(
                        lambda
                            a: a.po_state == 'approve' and a.partner_id == each).partner_id.property_purchase_currency_id.id

            if not approved_vendor:
                approved_vendor = products.supplier_name[0].id
                supplier_currency = products.supplier_name[0].property_purchase_currency_id.id
                approved_price = 0
            lines = (0, 0, {
                'categ_id': products.categ_id.id,
                'product_id': products.product_id.id,
                'name': products.description,
                'part_number_mfr': products.part_number_mfr,
                'part_number_one': products.part_number_one,
                'part_number_two': products.part_number_two,
                'c_mfr': products.c_mfr,
                'c_pn': products.c_pn,
                'on_hand': products.product_onhand_qty,
                'product_uom': products.product_uom.id,
                'supplier_currency': supplier_currency,
                'part_number': products.part_number,
                'price_unit': products.product_id.lst_price,
                'product_uom_qty': products.product_uom_qty,
                'supplier_po': supplier_po,
                # 'supplier': products.supplier_name.id,
                'supplier_new': approved_vendor,
                # 'supplier_price': products.supplier_price,
                'supplier_price': approved_price,
                'supplier_price_new': approved_price,
                'availability': products.availability,
            })
            enquiry_lines.append(lines)
        action['context'] = {
            'search_default_opportunity_id': self.id,
            'default_opportunity_id': self.id,
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_team_id': self.team_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_rig': self.rig,
            'default_customer_reference': self.customer_reference,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_tag_ids': [(6, 0, self.tag_ids.ids)],
            'default_order_line': enquiry_lines
        }
        # for products in self.enquiry_lines:
        #     for each in products.supplier_name:
        #         pq_approved = self.purchase_ids.filtered(lambda a: a.po_state == 'approve' and a.partner_id == each)
        # for line in pq_approved.order_line:
        #     line.
        return action


class PendingEnquiry(models.Model):
    _inherit = 'pending.enquiry'

    partner_id = fields.Many2one('res.partner', string="Customer", related='crm_lead_id.partner_id')


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    item_description = fields.Char('Item Desc')
    item_description_ar = fields.Char('Item Desc Ar')


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    categ_id = fields.Many2one('product.category', string="Category")
    c_mfr = fields.Char(string="C.MFR")
    c_pn = fields.Char(string="C.P/N")
    on_hand = fields.Float(string="On Hand")


class AlshabInvoice(models.Model):
    _inherit = 'alshab.invoice'

    ewb_number = fields.Char(string="E-Way No")
    decoded_data = fields.Char('Decoded Data')
    qr_image = fields.Binary(string="QR Image")
    uuid = fields.Char('UUID', size=50, index=True, default=lambda self: str(uuid4()), copy=False)

    def amount_words(self):
        return self.company_id.currency_id.amount_to_text(self.net_amount)

    def compute_amount_total(self):
        for each in self:
            each.amount_total = sum(each.mapped('inter_companys_lines').mapped('price_subtotal'))+sum(each.mapped('inter_companys_lines').mapped('discount_amount'))

    def compute_other_amount_total(self):
        for each in self:
            each.other_amount_total = each.amount_total * each.customer_currency_rate

    def compute_tax_amount(self):
        for each in self:
            each.tax_amount = sum(each.mapped('inter_companys_lines').mapped('tax_amount'))

    def compute_other_tax_amount(self):

        for each in self:
            each.other_tax_amount = each.tax_amount * each.customer_currency_rate

    def compute_after_discount_amount(self):
        for each in self:
            each.after_discount_amount = each.amount_total - each.discount

    def compute_other_after_discount(self):
        for each in self:
            each.other_after_discount = each.after_discount_amount * each.customer_currency_rate

    def compute_net_amount(self):
        for each in self:
            each.net_amount = each.after_discount_amount + each.tax_amount

    def compute_other_net_amount(self):
        for each in self:
            each.other_net_amount = each.net_amount * each.customer_currency_rate

    def compute_discount_total(self):
        for each in self:
            each.discount = sum(each.mapped('inter_companys_lines').mapped('discount_amount'))

    amount_total = fields.Float(string="Untaxed", compute='compute_amount_total')
    other_amount_total = fields.Float(string="Inter Untaxed", compute='compute_other_amount_total')
    discount = fields.Float(string="Discount", compute='compute_discount_total')
    after_discount_amount = fields.Float(string="After Discount", compute='compute_after_discount_amount')
    other_after_discount = fields.Float(string="Inter After Discount", compute='compute_other_after_discount')
    tax_amount = fields.Float(string="Tax Amount", compute='compute_tax_amount')
    other_tax_amount = fields.Float(string="Inter Tax Amount", compute='compute_other_tax_amount')
    net_amount = fields.Float(string="Net Amount", compute='compute_net_amount')
    other_net_amount = fields.Float(string="Inter Net Amount", compute='compute_other_net_amount')
    datetime_field = fields.Datetime(string="Create Date", default=lambda self: fields.Datetime.now())

    def testing(self):
        leng = len(self.company_id.name)
        company_name = self.company_id.name
        if 42 > leng:
            for r in range(42 - leng):
                if len(company_name) != 42:
                    company_name += ' '
                else:
                    break
        else:
            if 42 < leng:
                company_name = company_name[:42]
        vat_leng = len(self.company_id.vat)
        vat_name = self.company_id.vat
        if 17 > vat_leng:
            for r in range(15 - vat_leng):
                if len(vat_name) != 15:
                    vat_name += ' '
                else:
                    break
        else:
            if 17 < leng:
                vat_name = vat_name[:17]

        amount_total = str(self.net_amount)
        amount_leng = len(str(self.net_amount))
        if len(amount_total) < 17:
            for r in range(17 - amount_leng):
                if len(amount_total) != 17:
                    amount_total += ' '
                else:
                    break

        tax_leng = len(str(self.tax_amount))
        amount_tax_total = str(self.tax_amount)
        if len(amount_tax_total) < 17:
            for r in range(17 - tax_leng):
                if len(amount_tax_total) != 17:
                    amount_tax_total += ' '
                else:
                    break
        TimeAndDate = str(self.create_date) + "T" + str(self.datetime_field.time()) + "Z"
        time_length = len(str(self.create_date) + "T" + str(self.datetime_field.time()) + "Z")

        Data = str(chr(1)) + str(chr(leng)) + self.company_id.name
        Data += (str(chr(2))) + (str(chr(vat_leng))) + vat_name
        Data += (str(chr(3))) + (str(chr(time_length))) + TimeAndDate
        Data += (str(chr(4))) + (str(chr(len(str(self.net_amount))))) + str(self.net_amount)
        Data += (str(chr(5))) + (str(chr(len(str(self.tax_amount))))) + str(self.tax_amount)
        data = Data
        import base64
        print(data)
        mou = base64.b64encode(bytes(data, 'utf-8'))
        self.decoded_data = str(mou.decode())
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=20,
            border=4,
        )
        data_im = str(mou.decode())
        qr.add_data(data_im)
        qr.make(fit=True)
        img = qr.make_image()

        import io
        import base64

        temp = io.BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        self.qr_image = qr_image
        print(mou.decode())
        return str(mou.decode())

    def action_create_invoice(self):
        journal_id = self.env['account.journal'].sudo().search(
            [('name', '=', 'Customer Invoices'), ('type', '=', 'sale'), ('company_id', '=', self.company_id.id)]).id,
        account_id = self.env['account.account'].search(
            [('name', '=', 'Product Sales'), ('company_id', '=', self.company_id.id)])
        # account_ids = self.env['account.account'].search(
        #     [('name', '=', 'Debtors'), ('company_id', '=', self.company_id.id)])
        list = []
        for line in self.inter_companys_lines:
            dict = (0, 0, {
                'name': line.product_id.name,
                # 'origin': self.name,
                'account_id': account_id.id,
                'price_unit': line.price_unit,
                'quantity': line.done_qty,
                'discount': line.discount,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'sale_line_ids': [(6, 0, line.sale_line_id.ids)],
                # 'purchase_order_id': line.sale_line_id.order_id.id,
                # 'sale_line_id': [(6, 0, line.sale_line_id.ids)],
                # 'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                'desc_a': line.desc_a,
                # 'sale_line_ids': [(6, 0, [line.id for line in sale_order.order_line])],
            })
            list.append(dict)

        invoice = self.env['account.move'].sudo().create({
            'partner_id': self.partner_id.id,
            # 'currency_id': self.currency_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'company_id': self.company_id.id,
            'invoice_date': datetime.today().date(),
            'journal_id': journal_id,
            'customer_currency': self.customer_currency.id,
            'customer_currency_rate': self.customer_currency_rate,
            # 'account_id': account_ids.id,
            'inv_no': self.inv_no,
            'po_number': self.po_number,
            'po_date': self.po_date,
            'ewb_number': self.ewb_number,
            'invoice_line_ids': list,
            'alshab_invoice_id': self.id,
            'branch_id': self.branch_id.id,

        })
        invoice.action_post()
        for line in self.inter_companys_lines:
            so_id = self.env["sale.order"].search([('id', '=', line.sale_line_id.order_id.id)])
            pick_ids = self.env["pending.sale.order"].search(
                [('so_no', '=', so_id.id), ('product_name', '=', line.product_id.id)])
            if pick_ids:
                pick_ids.write({
                    'inv_no': invoice.id,
                    'inv_date': str(invoice.invoice_date),
                })
            line.sale_line_id.qty_invoiced += line.done_qty
            line.sales_order_lines.qty_invoiced += line.done_qty
            # ref_pending_sales = self.env["pending.sale.order"].search([('so_no', '=', line.sale_line_id.order_id.id), ('product_name','=', line.product_id.id)])
            # for inv_order in order:
            # if ref_pending_sales:
            #     ref_pending_sales.inv_no = invoice
            #     ref_pending_sales.inv_date = invoice.invoice_date
        # self.invoice_id = invoice
        # for line in self.inter_companys_lines:
        #     if line.sale_line_id:
        #         line.sale_line_id.qty_invoiced +=line.done_qty
        self.write({'state': 'invoice'})
        for eac in self.alshad_picking_ids:
            eac.billed = True
        if not self.env['stock.picking'].search([('po_number', '=', self.po_number.id), ('billed', '=', False)]):
            self.po_number.inv_quote_used = True

    def action_create_bill(self):
        journal_id = self.env['account.journal'].sudo().search(
            [('name', '=', 'Vendor Bills'), ('type', '=', 'purchase'), ('company_id', '=', self.company_id.id)]).id,
        account_id = self.env['account.account'].search(
            [('name', '=', 'Purchases - Resale Items'), ('company_id', '=', self.company_id.id)])

        list = []
        for each in self.alshad_picking_ids:
            ref = self.env['alshab.inventorys'].search([('picking_ids', '=', each._origin.id)])
            if ref:
                self.po_number = ref.po_number
                self.po_date = ref.po_date
        for line in self.inter_companys_lines:
            if self.customer_currency.name != 'SAR':
                unit_price = line.price_unit / self.customer_currency_rate
            else:
                unit_price = line.price_unit
            dict = (0, 0, {
                'name': line.product_id.name,
                # 'origin': self.name,
                'account_id': account_id.id,
                # 'price_unit': line.price_unit,
                'price_unit': unit_price,
                'discount': line.discount,
                'quantity': line.done_qty,
                'purchase_line_id': line.demo_purchase_line_id.id,
                'purchase_order_id': line.demo_purchase_line_id.order_id.id,
                # 'purchase_line_ids':[(6, 0, line.sale_line_id.ids)],
                # 'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                # 'sale_line_ids': [(6, 0, [line.id for line in sale_order.order_line])],
            })
            list.append(dict)

        invoice = self.env['account.move'].sudo().create({
            'partner_id': self.partner_id.id,
            # 'currency_id': self.currency_id.id,
            'move_type': 'in_invoice',
            'state': 'draft',
            'ewb_number': self.ewb_number,
            'company_id': self.company_id.id,
            'invoice_date': datetime.today().date(),
            'journal_id': journal_id,
            # 'account_id': account_ids.id,
            'inv_no': self.inv_no,
            'po_number': self.po_number,
            'customer_currency': self.customer_currency.id,
            'customer_currency_rate': self.customer_currency_rate,
            'po_date': self.po_date,
            'invoice_line_ids': list,
            'alshab_invoice_id': self.id,
            # 'purchase_id': self.purchases_ids[0].id,
            'branch_id': self.branch_id.id,

        })
        invoice.action_post()
        self.write({'state': 'invoice'})
        for eac in self.alshad_picking_ids:
            eac.billed = True

    @api.onchange('alshad_picking_ids')
    def onchange_alshad_picking_ids(self):
        list = []
        for pick in self.alshad_picking_ids:
            ref = self.env['alshab.inventorys'].search([('picking_ids', '=', pick._origin.id)])
            if ref:
                self.po_number = ref.po_number
                self.po_date = ref.po_date
                self.customer_reference = pick.move_ids_without_package.mapped('demo_sale_line_id').mapped(
                    'order_id').customer_reference
            for line in pick.move_ids_without_package:
                # inv_ref_line = ref.inter_companys_lines.filtered(lambda a: a.product_id == line._origin.product_id)
                # dict = (0, 0, {
                #     'name': line.product_id.name,
                #     # 'origin': self.name,
                #     'account_id': account_id.id,
                #     'price_unit': inv_ref_line.price_unit,
                #     'quantity': line.quantity_done,
                #     'purchase_line_id': line._origin.demo_purchase_line_id.id,
                #     'purchase_order_id': line._origin.demo_purchase_line_id.order_id.id,
                #     'product_id': line.product_id.id,
                #     'price_subtotal': inv_ref_line.price_unit * line.quantity_done
                # })
                # list.append(dict)
                price_unit = 0
                if line._origin.demo_sale_line_id:
                    price_unit = line._origin.demo_sale_line_id.price_unit
                if line._origin.demo_purchase_line_id:
                    price_unit = line._origin.demo_purchase_line_id.price_unit
                data = (0, 0, {
                    'product_id': line.product_id.id,
                    # 'desc': line.description_picking,
                    'desc': line.product_id.item_description,
                    'desc_a': line.product_id.item_description_ar,
                    # 'serial_number': order_line.serial_number,
                    'uom_id': line.product_id.uom_id.id,
                    'sale_line_id': line.sale_line_id.id,
                    'part_number_mfr': line.part_number,
                    'part_number': line.part_number,
                    'part_number_two': line.part_number,
                    'part_number_tree': line.part_number,
                    'price_unit': price_unit,
                    'product_uom_qty': line.quantity_done,
                    'done_qty': line.quantity_done,
                    # 'tax_ids': [(6, 0, line.product_id.taxes_id.ids)],
                    'price_subtotal': line.quantity_done * price_unit
                })
                list.append(data)

        self.inter_companys_lines = False
        self.inter_companys_lines = list


class AlshabInvoceLines(models.Model):
    _inherit = 'alshab.invoice.lines'

    discount = fields.Float(string="Discount(%)")
    discount_amount = fields.Float(string="Discount",compute='compute_discount_amount')
    ar_quantity = fields.Char(string="Ar QTY")
    ar_price = fields.Char(string="Ar Price")
    ar_total = fields.Char(string="Ar Total")
    ar_vat = fields.Char(string="Ar Vat")
    ar_vat_amt = fields.Char(string="Ar Vat/AMt")
    ar_netprice=fields.Char(string="Ar Net/price")


    @api.depends('discount')
    def compute_discount_amount(self):
        for line in self:
            if line.discount:
               price_subtotal = line.product_uom_qty * line.price_unit
               line.discount_amount = price_subtotal * line.discount/100
            else:
                line.discount_amount = 0

    @api.onchange('product_uom_qty', 'price_unit', 'discount','discount_amount')
    def onchange_product_uom_qty_id(self):
        if self.product_uom_qty:
            price_subtotal = self.product_uom_qty * self.price_unit
            self.price_subtotal = price_subtotal - self.discount_amount

    @api.depends('product_id')
    @api.onchange('product_id')
    def onchange_product_ids(self):
        if self.product_id:
            self.desc = self.product_id.item_description
            self.desc_a = self.product_id.item_description_ar

    def compute_tax_amount(self):
        for line in self:
            if line.tax_ids:
                line.tax_amount = line.price_subtotal * line.tax_ids.amount / 100
            else:
                line.tax_amount = 0

    tax_amount = fields.Float(string="Tax Amount", compute='compute_tax_amount')


class AlshabInventoryLines(models.Model):
    _inherit = 'alshab.inventory.lines'

    c_mfr = fields.Char(string="C.MFR")
    c_pn = fields.Char(string="C.P/N")
    categ_id = fields.Many2one('product.category', string="Category")
    part_number_mfr = fields.Char(string="Mfr.Part")
    reference_number = fields.Char('Ref. No.')
    remarks = fields.Char('Remarks')
    availability = fields.Char('Availability')
    part_number = fields.Char('Part No')


class AlshabInventorys(models.Model):
    _inherit = 'alshab.inventorys'

    @api.onchange('sales_ids_orders')
    def onchange_sales_ids_orders(self):
        if self.sales_ids_orders:
            self.inter_companys_lines = False
            all_list = []
            for each in self.sales_ids_orders:
                self.po_number = each.po_number
                self.po_date = each.po_date
                self.branch_id = each.branch_id.id
                self.partner_id = each.partner_id.id
                self.customer_ref = each.customer_reference
                # self.rig = each.rig
                self.entry_date = each.date
                self.picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing')]).id
                stock_location = self.env['stock.location'].search(
                    [('name', '=', 'Stock')]).id
                out_location = self.env['stock.location'].search(
                    [('name', '=', 'Customers')]).id
                self.location_id = stock_location
                self.dest_location_id = out_location
                for order_line in each.sale_order_lines.filtered(lambda a: a.qty_delivered < a.product_uom_qty):
                    data = (0, 0, {
                        'product_id': order_line.product_id.id,
                        'desc': order_line.description,
                        # 'serial_number': order_line.serial_number,
                        'location_id': stock_location,
                        'dest_location_id': out_location,
                        'uom_id': order_line.product_id.uom_id.id,
                        'sale_line_id': order_line.sale_line_id.id,
                        'c_mfr': order_line.c_mfr,
                        'c_pn': order_line.c_pn,
                        'categ_id': order_line.categ_id.id,
                        'part_number_mfr': order_line.part_number_mfr,
                        'reference_number': order_line.reference_number,
                        'remarks': order_line.remarks,
                        'availability': order_line.availability,
                        'part_number': order_line.part_number,
                        'part_number_two': order_line.part_number,
                        'part_number_tree': order_line.part_number,
                        'price_unit': order_line.price_unit,
                        'product_uom_qty': order_line.product_uom_qty - order_line.qty_delivered,
                        'done_qty': order_line.product_uom_qty - order_line.qty_delivered,
                        # 'partner_id': self.partner_id.id,
                        # 'procure_method': 'make_to_order',
                        'demo_sale_line_id': order_line.sale_line_id.id,
                        'sales_order_lines': order_line._origin.id,
                        # 'picking_id': self.picking_type_id.id,
                    })
                    all_list.append(data)

            self.inter_companys_lines = all_list

    @api.onchange('purchases_ids')
    def onchange_purchases_ids(self):
        if self.purchases_ids:
            self.inter_companys_lines = False
            all_list = []
            for each in self.purchases_ids:
                # self.env['sales.orders'].search([('po_number','=',po_number)])
                self.po_number = each._origin.po_number.id
                # self.po_date =each.po_number.po_date
                self.po_date = self.env['sales.orders'].search([('po_number', '=', each._origin.po_number.id)]).po_date
                self.branch_id = each.branch_id.id
                self.partner_id = each.partner_id.id
                self.picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming')]).id
                out_location = self.env['stock.location'].search(
                    [('name', '=', 'Stock')]).id

                stock_location = self.env['stock.location'].search(
                    [('name', '=', 'Vendors')]).id
                # origin_location_id = self.env['stock.location'].search([('name', '=', 'Vendors')])[0]
                # dest_location_id = self.env['stock.location'].search(
                #     [('company_id', '=', self.company_id.id), ('name', '=', 'Stock')]).id
                # picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'Receipts')]).filtered(
                #     lambda a: a.default_location_dest_id.company_id == self.company_id)

                self.location_id = stock_location
                self.dest_location_id = out_location
                for order_line in each.order_line.filtered(lambda a: a.qty_received < a.product_uom_qty):
                    data = (0, 0, {
                        'product_id': order_line.product_id.id,
                        'desc': order_line.name,
                        # 'serial_number': order_line.serial_number,
                        'location_id': stock_location,
                        'dest_location_id': out_location,
                        'sales_orders_id': order_line._origin.sales_orders_id.id,
                        'uom_id': order_line.product_id.uom_id.id,
                        # 'sale_line_id': order_line._origin.id,
                        'part_number_mfr': order_line.product_id.part_number_mfr,
                        'part_number': order_line.part_number,
                        'part_number_two': order_line.part_number,
                        'part_number_tree': order_line.part_number,
                        'price_unit': order_line.price_unit,
                        'product_uom_qty': order_line.product_qty - order_line.qty_received,
                        'done_qty': order_line.product_qty - order_line.qty_received,
                        # 'partner_id': self.partner_id.id,
                        # 'procure_method': 'make_to_order',
                        'demo_purchase_line_id': order_line._origin.id,
                        # 'picking_id': self.picking_type_id.id,
                    })
                    all_list.append(data)

            self.inter_companys_lines = all_list
