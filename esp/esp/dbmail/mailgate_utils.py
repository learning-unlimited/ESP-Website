from __future__ import absolute_import

from email.utils import formataddr, getaddresses


def _is_self_address(address, local_part, domain):
    if not address:
        return False
    address = address.strip().lower()
    local_part = (local_part or "").strip().lower()
    domain = (domain or "").strip().lower()

    if "@" not in address:
        return address == local_part

    addr_local, addr_domain = address.rsplit("@", 1)
    return addr_local == local_part and addr_domain == domain


def sanitize_recipient_headers(message, local_part, domain, drop_bcc=False):
    """
    Remove self-referential list aliases from To/Cc/Bcc headers.
    Optionally drop Bcc entirely for forwarded mail.
    """
    for header in ("To", "Cc", "Bcc"):
        if not message.get(header):
            continue

        if header == "Bcc" and drop_bcc:
            del message[header]
            continue

        addresses = getaddresses([message.get(header)])
        filtered = []
        for name, address in addresses:
            if _is_self_address(address, local_part, domain):
                continue
            filtered.append(formataddr((name, address)) if name else address)

        del message[header]
        if filtered:
            message[header] = ", ".join(filtered)
