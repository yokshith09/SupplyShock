"""Static message templates (no LLM needed, so the demo cannot fail on drafting)."""
import os

COMPANY = os.getenv("COMPANY_NAME", "Apex Components Pvt Ltd")


def rfq(supplier_name: str, material: str, material_id: str, qty: int, unit: str, need_by: str | None) -> tuple[str, str]:
    need = f" by {need_by}" if need_by else " at the earliest"
    subject = f"RFQ: {qty} {unit} of {material} ({material_id}){need} | {COMPANY}"
    body = (f"Dear {supplier_name} team,\n\n"
            f"A regional supply disruption is affecting our primary supply of {material} ({material_id}). "
            f"We would like a quotation for {qty} {unit}, delivered{need}.\n\n"
            "Please reply with:\n"
            "  1. Unit price (INR)\n  2. Lead time and earliest dispatch date\n  3. Minimum order quantity\n"
            "  4. Payment terms\n\n"
            "A reply within 24 hours would help us decide quickly.\n\n"
            f"Regards,\nProcurement, {COMPANY}")
    return subject, body


def expedite(supplier_name: str, material: str, material_id: str, qty: int, unit: str) -> tuple[str, str]:
    subject = f"URGENT: expedite {material_id} shipment ({qty} {unit}) | {COMPANY}"
    body = (f"Dear {supplier_name} team,\n\n"
            f"Because of the regional disruption, please expedite our open order of {qty} {unit} of "
            f"{material} ({material_id}). If possible, dispatch before the disruption reaches your area "
            "and use the fastest available mode (air or express road).\n\n"
            "Please confirm the new dispatch date and any extra freight cost within 24 hours.\n\n"
            f"Regards,\nProcurement, {COMPANY}")
    return subject, body


def customer_notice(customer: str, order_id: str, kind: str, new_date: str | None) -> tuple[str, str]:
    if kind == "delay":
        when = f" The revised delivery date is {new_date}." if new_date else " We will confirm a revised date shortly."
        subject = f"Update on order {order_id}: delivery delay"
        body = (f"Dear {customer},\n\nA regional supply disruption may delay order {order_id}.{when} "
                "We apologise for the inconvenience and will keep you updated.\n\n"
                f"Regards,\n{COMPANY}")
    else:
        subject = f"Update on order {order_id}: on track"
        body = (f"Dear {customer},\n\nA regional supply disruption is in the news. We have already taken "
                f"steps to protect order {order_id} and currently expect to deliver as planned. "
                f"We will tell you immediately if that changes.\n\nRegards,\n{COMPANY}")
    return subject, body
