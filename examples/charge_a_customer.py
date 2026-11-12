"""Create a test-mode charge and read it back: VELIRAPAY_API_KEY=vp_test_... python examples/charge_a_customer.py"""

import os

from velirapay import VeliraPayClient


def main() -> None:
    velirapay = VeliraPayClient(os.environ.get("VELIRAPAY_API_KEY"))

    if not velirapay.is_test_mode():
        raise SystemExit("This example only runs with a test-mode key, starting with vp_test_.")

    charge = velirapay.charges.create(
        {
            "amount": "49.90",
            "currency": "EUR",
            "asset": "BTC",
            "customer": {"email": "ada@example.com", "name": "Ada Lovelace"},
            "description": "Example charge from velirapay-python",
            "metadata": {"order_id": "example-1"},
        }
    )

    retrieved = velirapay.charges.retrieve(charge.id)

    print(f"id:              {retrieved.id}")
    print(f"status:          {retrieved.status}")
    print(f"amount:          {retrieved.asset_amount} {retrieved.asset}")
    print(f"deposit address: {retrieved.deposit_address}")
    print(f"checkout:        {retrieved.checkout_url}")
    print(f"expires at:      {retrieved.expires_at}")


if __name__ == "__main__":
    main()
