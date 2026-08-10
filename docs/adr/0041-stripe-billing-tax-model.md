# ADR-0041: UK-First Stripe Billing and Tax Model

- Status: Accepted
- Date: 2026-08-10
- Decision scope: subscription billing, tax calculation, invoices and tax evidence

## Context

The platform needs recurring subscription billing, a customer billing portal and a defensible record of the tax treatment applied to each invoice. The initial commercial market is the UK, while the product is designed to expand later. The application must keep subscription entitlements separate from payment-provider objects and must not store unnecessary payment payloads.

The alternatives considered were:

1. Stripe Billing with Stripe Tax, Stripe Invoicing and the Stripe Customer Portal.
2. A merchant-of-record provider such as Paddle or Lemon Squeezy.
3. Direct tax calculation and internally generated invoices.

## Decision

The application will initially remain the seller of record and use Stripe as the billing provider:

- Stripe Billing manages subscriptions and recurring payment state.
- Stripe Tax calculates applicable VAT and retains the tax evidence supplied by Stripe.
- Stripe Invoicing is the source of truth for invoice numbering, tax breakdowns, credit notes and invoice PDFs.
- The Stripe Customer Portal provides customer self-service for payment methods, invoices and subscription management.
- The application owns entitlements. Domain code checks application entitlements, not Stripe objects or plan IDs directly.

Stripe-specific calls will remain behind the billing service boundary. Provider identifiers may be stored for reconciliation, but raw payment methods, card data and complete webhook payloads must not be persisted. Webhook events remain idempotent and auditable through their event identifiers and redacted metadata.

## UK-first tax stages

### Before VAT registration

The application will not charge UK VAT when the business is not VAT registered. Invoices will state the applicable non-VAT treatment configured for the seller.

### After VAT registration

Stripe Tax will be enabled for UK VAT calculation. Checkout and billing-profile work must capture the customer billing country, customer type and tax identifier where applicable. Invoices must expose the tax rate, taxable amount, tax amount and any reverse-charge treatment.

### International expansion

Before selling materially outside the UK, the business will reassess Stripe Tax registrations and evidence requirements against a merchant-of-record model. This is a commercial and tax decision, not an automatic software fallback.

## Implementation boundaries

The implementation will proceed in separate, testable slices:

1. Add a tenant billing/tax profile with country, business type and tax identifier fields, permission-gated and audited.
2. Pass the profile to Stripe Customer and Checkout/Tax configuration without exposing provider details to unrelated apps.
3. Reconcile invoice and tax metadata from signed, idempotent webhooks.
4. Provide finance/admin exports containing invoice and tax evidence references, without sensitive payment payloads.

VAT identifier validation must be treated as an external verification result with a timestamp and provider status; it must not be treated as proof of registration indefinitely. Reverse-charge treatment must be decided from the validated customer and transaction context, not from a client-supplied flag alone.

## Consequences

- The initial implementation remains simple for a UK launch and avoids premature merchant-of-record fees.
- A later provider change is possible because entitlements and billing state are separated from Stripe calls.
- The business remains responsible for VAT registration, returns and remittance while Stripe supplies calculation and evidence capabilities.
- Tax configuration, VAT registration status and invoice evidence become part of the audited billing domain.
- The product must not promise global tax compliance until registrations, evidence retention and reporting obligations for each market are explicitly assessed.

