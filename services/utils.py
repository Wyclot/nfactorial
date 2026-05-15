import secrets

def generate_invoice_id() -> str:
    return f'{secrets.randbelow(10 ** 12):012d}'