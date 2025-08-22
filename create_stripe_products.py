#!/usr/bin/env python3
"""
Script to create Stripe products and prices for the GRC platform.
Run this to set up your Stripe test products.
"""

import stripe

# Your Stripe secret key
stripe.api_key = "sk_test_51RypNIH7PFpuJb1wTUDNegHTaNzfM4fVIUAXNu3kQJ67sM2xwpw7hWOIf4T28M1IYGbW5YYZLuWGGIc9B0y9hUIZ006BN0GHAI"

plans = [
    {
        'name': 'GRC Basic',
        'description': 'Ideal for small to medium teams with growing compliance needs',
        'price': 49,  # $49/month
    },
    {
        'name': 'GRC Enterprise', 
        'description': 'Full-featured solution for large organizations',
        'price': 199,  # $199/month
    }
]

print("Creating Stripe products and prices...")
print("=" * 50)

created_prices = {}

for plan in plans:
    try:
        # Create product
        product = stripe.Product.create(
            name=plan['name'],
            description=plan['description'],
        )
        print(f"✅ Created product: {product.name}")
        
        # Create price
        price = stripe.Price.create(
            unit_amount=plan['price'] * 100,  # Convert to cents
            currency='usd',
            recurring={'interval': 'month'},
            product=product.id,
        )
        
        slug = plan['name'].lower().replace('grc ', '').replace(' ', '_')
        created_prices[slug] = price.id
        
        print(f"✅ Created price: {price.id} (${plan['price']}/month)")
        print()
        
    except stripe.error.StripeError as e:
        print(f"❌ Error creating {plan['name']}: {str(e)}")

print("Environment variables to add to your .env files:")
print("=" * 50)
for slug, price_id in created_prices.items():
    env_var = f"STRIPE_PRICE_{slug.upper()}"
    print(f"{env_var}={price_id}")

print()
print("Next steps:")
print("1. Copy the above environment variables to your .env.dev and .env.dev.example files")
print("2. Set up webhook endpoint in Stripe Dashboard:")
print("   - URL: http://localhost:8000/webhooks/stripe/")
print("   - Events: customer.subscription.*, invoice.*, checkout.session.completed")
print("3. Copy the webhook signing secret to your .env files as STRIPE_WEBHOOK_SECRET")