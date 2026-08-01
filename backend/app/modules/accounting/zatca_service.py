import base64
import hashlib
from typing import Optional


def _tlv_encode(tag: int, value: str) -> bytes:
    encoded_value = value.encode("utf-8")
    return bytes([tag, len(encoded_value)]) + encoded_value


def generate_qr_code_value(seller_name, vat_number, invoice_date, total_with_vat, vat_amount):
    tlv = b""
    tlv += _tlv_encode(1, seller_name)
    tlv += _tlv_encode(2, vat_number)
    tlv += _tlv_encode(3, invoice_date)
    tlv += _tlv_encode(4, f"{total_with_vat:.2f}")
    tlv += _tlv_encode(5, f"{vat_amount:.2f}")
    return base64.b64encode(tlv).decode("utf-8")


def generate_invoice_xml(invoice_number, issue_date, seller_name, seller_vat, seller_address,
                          buyer_name, buyer_vat, buyer_address, line_items, subtotal, tax_amount, total, invoice_type="simplified"):
    subtype = "0100000" if invoice_type == "simplified" else "0200000"
    items_xml = ""
    for i, item in enumerate(line_items, 1):
        item_tax = item.get("unit_price", 0) * item.get("quantity", 1) * 0.15
        item_total = item.get("unit_price", 0) * item.get("quantity", 1)
        items_xml += f"""
    <cac:InvoiceLine>
        <cbc:ID>{i}</cbc:ID>
        <cbc:InvoicedQuantity unitCode="PCE">{item.get("quantity", 1)}</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="SAR">{item_total:.2f}</cbc:LineExtensionAmount>
        <cac:TaxTotal><cbc:TaxAmount currencyID="SAR">{item_tax:.2f}</cbc:TaxAmount></cac:TaxTotal>
        <cac:Item><cbc:Name>{item.get("description", "Item")}</cbc:Name></cac:Item>
        <cac:Price><cbc:PriceAmount currencyID="SAR">{item.get("unit_price", 0):.2f}</cbc:PriceAmount></cac:Price>
    </cac:InvoiceLine>"""
    buyer_vat_xml = f"<cbc:CompanyID>{buyer_vat}</cbc:CompanyID>" if buyer_vat else ""
    buyer_addr_xml = f"<cbc:StreetName>{buyer_address}</cbc:StreetName>" if buyer_address else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
    <cbc:ID>{invoice_number}</cbc:ID>
    <cbc:IssueDate>{issue_date}</cbc:IssueDate>
    <cbc:InvoiceTypeCode name="{subtype}">388</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
    <cac:AccountingSupplierParty><cac:Party>
        <cac:PartyName><cbc:Name>{seller_name}</cbc:Name></cac:PartyName>
        <cac:PostalAddress><cbc:StreetName>{seller_address}</cbc:StreetName></cac:PostalAddress>
        <cac:PartyTaxScheme><cbc:CompanyID>{seller_vat}</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    </cac:Party></cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty><cac:Party>
        <cac:PartyName><cbc:Name>{buyer_name}</cbc:Name></cac:PartyName>
        <cac:PostalAddress>{buyer_addr_xml}</cac:PostalAddress>
        <cac:PartyTaxScheme>{buyer_vat_xml}
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    </cac:Party></cac:AccountingCustomerParty>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">{tax_amount:.2f}</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="SAR">{subtotal:.2f}</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="SAR">{tax_amount:.2f}</cbc:TaxAmount>
            <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>15</cbc:Percent>
            <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="SAR">{subtotal:.2f}</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="SAR">{subtotal:.2f}</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">{total:.2f}</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="SAR">{total:.2f}</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    {items_xml}
</Invoice>"""


def compute_invoice_hash(xml_content: str) -> str:
    return base64.b64encode(hashlib.sha256(xml_content.encode("utf-8")).digest()).decode("utf-8")
