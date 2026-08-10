# Stripe Tax Remittance Operations

This runbook defines the operating responsibilities for Axim's UK-first Stripe
Billing and Stripe Tax model. It is an operational control document, not tax or
legal advice. The finance owner must confirm the treatment with the business's
tax adviser and HMRC.

## Responsibilities

| Area | Owner | Responsibility |
| --- | --- | --- |
| VAT registration | Finance owner | Confirm when Axim must register, maintain registration details and notify the team of changes. |
| Stripe Tax configuration | Billing operator | Maintain UK registrations, product tax codes, tax behaviour and seller details in Stripe. |
| Invoice evidence | Billing operator | Review invoice and tax evidence reconciliation, including failures and amendments. |
| VAT return and payment | Finance owner | Prepare, approve, file and pay VAT returns by the applicable deadlines. |
| Application controls | Engineering | Preserve idempotent webhook processing, exports, audit events and access controls. |
| International expansion | Finance owner and product owner | Assess registrations and filing obligations before material sales outside the UK. |

Stripe calculates tax and supplies invoice evidence. It does not transfer the
business's responsibility for registration, filing or remittance.

## UK operating stages

### Before registration

- Keep the Stripe Tax UK registration disabled until the business is authorised
  to collect UK VAT.
- Confirm the invoice treatment and wording with the finance owner.
- Verify that a test Checkout session does not collect VAT unexpectedly.

### After registration

- Add and verify the UK registration in Stripe Tax before enabling production
  collection.
- Confirm tax codes and tax behaviour for every billable Price.
- Run a test Checkout session for a UK customer and a customer outside the UK.
- Reconcile invoice subtotal, tax amount, total, currency, tax status and
  invoice identifiers in the finance export.
- Record the return period, reviewer and reconciliation outcome outside the
  application finance evidence export.

## Evidence and reconciliation

The application retains redacted `InvoiceEvidence` records containing invoice
and tax totals, status, periods, Stripe invoice references and hosted evidence
URLs. It does not export raw `BillingEvent.data`, payment methods or secrets.

For each filing period, the billing operator must:

1. Export invoice tax evidence for the period.
2. Compare Stripe totals with the accounting ledger and payment records.
3. Investigate missing, failed or duplicate webhook events.
4. Confirm refunds and credit notes are included in the relevant amendment.
5. Have the finance owner approve the reconciliation before filing.

Reconciliation failures must not be silently dismissed. Record the affected
invoice IDs, event IDs, investigation, correction and reviewer decision in the
approved finance control record. Do not paste complete Stripe webhook payloads
into tickets or audit notes.

## Refunds and credit notes

Refunds and credit notes must be matched to the original invoice and included
in the period and amendment required by the applicable tax rules. The billing
operator must verify that the Stripe invoice state, application evidence and
accounting ledger agree before the finance owner approves the adjustment.

## Retention and access

- Retain invoice evidence for the period required by the business's UK tax and
  accounting obligations, subject to the approved retention schedule.
- Restrict finance exports and invoice URLs to authorised tenant users and
  platform operators with a legitimate support or finance need.
- Treat hosted invoice URLs as sensitive links; do not expose them in public
  logs, analytics or support screenshots.
- Apply the existing audit trail to export requests, downloads and billing
  reconciliation actions.

## Release checklist

Before enabling production automatic tax:

- [ ] Finance owner has confirmed VAT registration status and filing ownership.
- [ ] Stripe Tax registration and seller details are configured.
- [ ] Every active Price has a reviewed tax code and tax behaviour.
- [ ] UK and non-UK Checkout scenarios have been tested.
- [ ] Invoice webhook delivery, duplicate delivery and failure handling have
  been tested.
- [ ] Invoice tax evidence export has been reviewed by finance.
- [ ] Refund and credit-note reconciliation has an owner and procedure.
- [ ] Data-processing and privacy notices mention Stripe billing and tax data.
- [ ] Finance contacts and escalation paths are recorded.

## International expansion trigger

Before material sales in a new jurisdiction, pause the rollout for a tax
assessment. Confirm registration thresholds, customer-location evidence,
invoice wording, filing frequency, currency treatment and whether Stripe Tax,
a filing partner or a merchant-of-record model is appropriate. No new market
should be enabled solely because Stripe can calculate a tax rate there.
