# Payment Domain

**Module**: `app/domains/payments/`  
**Routes**: `/subscriptions/*`, `/webhooks/stripe`

---

## Responsibility

Stripe integration, freemium enforcement (1000 transaction limit)

---

## Key APIs

```
POST /subscriptions/checkout    → Create Stripe checkout session
POST /subscriptions/portal      → Manage subscription
POST /webhooks/stripe           → Handle Stripe events
```

---

## Database

```sql
-- Stored in users table
users.subscription_tier ('free' | 'premium')
users.transaction_limit (1000 for free, NULL for premium)
users.stripe_customer_id
users.stripe_subscription_id

-- Audit log
payment_events (id, user_id, event_type, stripe_event_id, data)
```

---

## Pricing (UAE)

```
Free:    0 AED/month, 1000 transactions, basic features
Premium: 29 AED/month, unlimited, AI chat, PDF reports
```

---

## Webhook Handling

```python
@app.post("/webhooks/stripe")
async def handle_webhook(request):
    event = stripe.Webhook.construct_event(...)
    
    if event.type == "checkout.session.completed":
        user.subscription_tier = "premium"
        user.transaction_limit = None
    
    elif event.type == "customer.subscription.deleted":
        user.subscription_tier = "free"
        user.transaction_limit = 1000
```

---

## Freemium Enforcement

```python
# In Transaction domain
if user.subscription_tier == "free" and count >= 1000:
    raise HTTPException(402, "Upgrade to premium")
```

---

**Dependencies**: Stripe, Auth Domain  
**Status**: Ready
