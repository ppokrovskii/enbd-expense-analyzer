# Payment Service - Solution Design

**Service**: Subscription & Billing Management  
**Port**: 8008  
**Repository**: `services/payment-service/`

---

## Responsibility

- Stripe integration for subscriptions
- Freemium tier enforcement (1000 transactions)
- Upgrade/downgrade flows
- Webhook handling

---

## API Endpoints

```
POST /subscriptions/checkout
  Body: { user_id, plan: "premium" }
  Returns: { checkout_url: string }

POST /subscriptions/portal
  Body: { user_id }
  Returns: { portal_url: string }

GET /subscriptions/status
  Query: user_id
  Returns: {
    tier: "free" | "premium",
    stripe_subscription_id: string?,
    status: "active" | "canceled" | "past_due",
    current_period_end: string?
  }

POST /webhooks/stripe
  Body: Stripe event
  Returns: { received: true }
```

---

## Data Model

**Note**: Subscription data stored in Auth Service's `users` table:
- `subscription_tier`: "free" | "premium"
- `transaction_limit`: 1000 (free) | NULL (premium)
- `stripe_customer_id`
- `stripe_subscription_id`

### payment_events (audit log)
```sql
CREATE TABLE payment_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  event_type VARCHAR(50) NOT NULL,  -- 'subscription.created', 'payment.succeeded'
  stripe_event_id VARCHAR(100) UNIQUE,
  data JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_user (user_id),
  INDEX idx_type (event_type)
);
```

---

## Stripe Integration

### Checkout Flow
```python
import stripe

stripe.api_key = STRIPE_SECRET_KEY

async def create_checkout_session(user_id: str, plan: str) -> str:
    """Create Stripe Checkout session for premium upgrade"""
    
    user = await get_user(user_id)
    
    # Create or retrieve customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": user_id}
        )
        await update_user(user_id, stripe_customer_id=customer.id)
    else:
        customer = stripe.Customer.retrieve(user.stripe_customer_id)
    
    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID_PREMIUM,  # Monthly price
            "quantity": 1
        }],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/dashboard?upgrade=success",
        cancel_url=f"{FRONTEND_URL}/pricing?upgrade=canceled",
        metadata={"user_id": user_id}
    )
    
    return session.url
```

### Customer Portal (for cancellation/updates)
```python
async def create_portal_session(user_id: str) -> str:
    """Create Stripe Customer Portal session"""
    
    user = await get_user(user_id)
    
    if not user.stripe_customer_id:
        raise HTTPException(400, "No active subscription")
    
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard"
    )
    
    return session.url
```

---

## Webhook Handling

```python
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks for subscription events"""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {str(e)}")
    
    # Route event to handler
    if event.type == "checkout.session.completed":
        await handle_checkout_completed(event.data.object)
    
    elif event.type == "customer.subscription.updated":
        await handle_subscription_updated(event.data.object)
    
    elif event.type == "customer.subscription.deleted":
        await handle_subscription_canceled(event.data.object)
    
    elif event.type == "invoice.payment_succeeded":
        await handle_payment_succeeded(event.data.object)
    
    elif event.type == "invoice.payment_failed":
        await handle_payment_failed(event.data.object)
    
    # Log event
    await log_payment_event(event)
    
    return {"received": True}

async def handle_checkout_completed(session: dict):
    """Upgrade user to premium after successful checkout"""
    
    user_id = session["metadata"]["user_id"]
    subscription_id = session["subscription"]
    
    await update_user(user_id, 
        subscription_tier="premium",
        transaction_limit=None,  # Unlimited
        stripe_subscription_id=subscription_id
    )
    
    await publish_event({
        "event": "subscription.upgraded",
        "user_id": user_id,
        "tier": "premium"
    })

async def handle_subscription_canceled(subscription: dict):
    """Downgrade user to free tier"""
    
    customer_id = subscription["customer"]
    user = await get_user_by_stripe_customer(customer_id)
    
    await update_user(user.id,
        subscription_tier="free",
        transaction_limit=1000,
        stripe_subscription_id=None
    )
    
    await publish_event({
        "event": "subscription.downgraded",
        "user_id": user.id,
        "tier": "free"
    })
```

---

## Freemium Enforcement

**Implementation in Transaction Service**:
```python
async def check_transaction_limit(person_id: str):
    """Called before importing transactions"""
    
    user = await get_user_by_person(person_id)
    
    if user.subscription_tier == "free":
        count = await count_transactions(person_id)
        
        if count >= user.transaction_limit:  # 1000
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Transaction limit reached",
                    "current_count": count,
                    "limit": user.transaction_limit,
                    "upgrade_url": f"{FRONTEND_URL}/pricing"
                }
            )
```

---

## Pricing (UAE)

### Stripe Products
```
Free Tier:
- Price: $0/month
- Transactions: 1000
- Features: Basic categorization, CSV export

Premium Tier:
- Price: 29 AED/month (~$8 USD)
- Transactions: Unlimited
- Features: AI Chat, PDF Reports, Priority support
```

### Frontend Display
```typescript
const plans = [
  {
    name: "Free",
    price: "0 AED",
    features: [
      "1,000 transactions",
      "Basic categorization",
      "CSV export"
    ]
  },
  {
    name: "Premium",
    price: "29 AED/month",
    features: [
      "Unlimited transactions",
      "AI Chat assistant",
      "PDF/Excel reports",
      "Priority support"
    ],
    cta: "Upgrade Now"
  }
];
```

---

## Events Published

```python
{
  "event": "subscription.upgraded",
  "user_id": "uuid",
  "tier": "premium",
  "stripe_subscription_id": "sub_xxx"
}

{
  "event": "subscription.downgraded",
  "user_id": "uuid",
  "tier": "free"
}

{
  "event": "payment.failed",
  "user_id": "uuid",
  "invoice_id": "in_xxx"
}
```

---

## Technology

- **Framework**: FastAPI
- **Payment**: Stripe SDK
- **Database**: PostgreSQL (via Auth Service)
- **Event Bus**: aio-pika

---

## Testing

```python
def test_create_checkout_session():
    with patch('stripe.checkout.Session.create') as mock:
        mock.return_value.url = "https://checkout.stripe.com/..."
        
        url = await create_checkout_session(user_id, "premium")
        
        assert "checkout.stripe.com" in url

@pytest.mark.integration
async def test_webhook_flow():
    # Simulate Stripe webhook
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": "test-user"},
                "subscription": "sub_test123"
            }
        }
    }
    
    await stripe_webhook(event)
    
    # Verify user upgraded
    user = await get_user("test-user")
    assert user.subscription_tier == "premium"
```

---

## Monitoring

- Checkout conversion rate
- Subscription churn rate
- Payment failure rate
- Webhook processing time

---

**Status**: Ready for implementation  
**Owner**: Backend Team  
**Dependencies**: Auth Service, Stripe



