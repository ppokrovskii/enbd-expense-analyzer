# Bank Transaction Analyzer - Requirements

## Implementation Status

### ✅ Completed Features (Phase 1)

All core functionality has been successfully implemented and tested. See [implementation-complete.md](./implementation-complete.md) for detailed completion report.

**Milestones Completed:**
- ✅ M1: Account Management
- ✅ M2: Enhanced Categorization  
- ✅ M3: Background Jobs & WebSocket
- ✅ M4: Multi-Bank Support
- ✅ M5: LLM Rule Generation
- ✅ M6: Frontend Implementation

**Test Coverage:** 40/40 passing ✅

---

## Overview
Multi-bank web app for analyzing transaction exports with AI categorization, visualizations, and financial chat assistant. Currently supports ENBD (Emirates NBD), extensible for FAB, WIO, etc.

## Implemented Features ✅

### ✅ Transaction Management
- ✅ Upload XLSX files (multi-bank support with auto-detection)
- ✅ Parse: Details + Description fields → combined search field
- ✅ Deduplicate by hash: `md5(date|account|amount|description)`
- ✅ Transform: Remove commas, extract merchants, create signed amounts
- ✅ Multi-bank parser architecture (ENBD, FAB, WIO)
- ✅ Unparsed file storage for manual review

### ✅ Categorization
**Rule-based**:
- ✅ Match on: Details + Description (concatenated)
- ✅ Support account variables: `{current_account}`, `{own_account}`, `{own_account_masked}`
- ✅ Exclude patterns for refined matching
- ✅ Pipe-separated alternatives (OR logic)
- ✅ Longest match priority
- ✅ Case-insensitive matching
- ✅ **Auto re-categorization**: Background job with real-time progress notifications

**AI-powered**:
- ✅ LLM rule generation for new merchants
- ✅ Category suggestions based on transaction details
- ✅ Confidence scoring
- ✅ Integration with AI chat

**Rule Manager** (unified rule editing UI):
- ✅ Filter by: category, merchant search, status (uncategorized/has rule)
- ✅ Entry points: navigation menu, transaction/merchant selection, category click
- ✅ URL params: `?merchants=`, `?category=`, `?search=`, `?status=`
- ✅ Inline rule editing (keywords, exclude, category)
- ✅ Bulk actions: AI Categorize, Assign Category, Delete Rules
- ✅ Rule tracing: shows which rule matches each merchant

**Category Properties**:
- ✅ Name, keywords, exclude_keywords, color (64-color palette)
- ✅ Colors: 8 families × 8 shades = 64 options
- ✅ Match both fields configuration

### ✅ AI Chat Assistant
- ✅ Multi-session with persistent history
- ✅ Context injection: transactions + category rules
- ✅ Real-time context preview
- ✅ Category management via chat: create, modify categories
- ✅ ChatGPT-style UI with markdown rendering
- ✅ Master-detail layout with chat history
- ✅ Auto-generated chat titles
- ✅ Quick action buttons with auto-context

### ✅ Account Configuration
- ✅ User defines owned accounts with friendly names
- ✅ Variables for rules: `{current_account}` → `101XXXXXXXX01`
- ✅ Generic variables: `{own_account}`, `{own_account_masked}`
- ✅ CRUD operations for accounts
- ✅ Primary account designation

### ✅ Notifications (Real-time via WebSocket)
- ✅ Re-categorization progress (started, %, completed/failed)
- ✅ Job status updates
- ✅ Success/failure alerts
- ✅ Auto-reconnection
- ✅ Dismissible notifications

### ✅ Settings UI
- ✅ Account management interface
- ✅ Category CRUD with color picker
- ✅ Trigger recategorization from UI
- ✅ 64-color palette with visual preview

---

## Planned Features (Phase 2)

### Authentication & User Tiers
- [ ] Google OAuth + email/password registration
- [ ] **Free**: 3 questions/day for AI chat
- [ ] **Premium** (AED 29/month): Unlimited AI questions, full features
- [ ] Auto-apply admin-managed category templates on signup

### Visualizations
- [ ] Stacked column charts (income bottom, expenses stacked by category)
- [ ] Time grouping: Weekly (Monday-Monday) or Monthly
- [ ] Filters: Date range, categories, accounts, merchant search
- [ ] Transaction table: Details, Description, Merchant, Category, Amount
- [ ] **Show planned expenses**: Alongside actual transactions, visually distinct
- [ ] Real-time updates on data changes

### Budget Planning
- [ ] Create planned transactions (future income/expenses)
- [ ] **Salary auto-configured** in settings → generates monthly planned salary transactions
- [ ] Bulk planning: Split large expense into monthly planned transactions
- [ ] System suggests equal monthly splits based on salary day
- [ ] User can customize split distribution

**Budget Overview**:
- [ ] Monthly breakdown: Planned income vs planned expenses
- [ ] **Balance calculation**: Income - Expenses = Remaining
- [ ] **Red warning**: Negative balance months
- [ ] **Visual indicators**: Green (positive), Yellow (< 10%), Red (negative)
- [ ] Compare: Actual vs planned for past months

**Transaction Management** (Planned):
- [ ] View/edit/delete planned transactions
- [ ] Mark as "matched" when actual transaction arrives
- [ ] Show variance: planned vs actual amounts

### Admin Panel
- [ ] Manage global category templates (name, keywords, color, bank)
- [ ] Templates auto-applied to new users
- [ ] Monitor usage statistics
- [ ] Download unparsed files for parser development

### Payments (UAE-compatible)
- [ ] Stripe integration: Cards, Apple Pay, Google Pay
- [ ] Plans: Free (AED 0) vs Premium (AED 29/month)
- [ ] Webhook-based activation

---

## Data Model

### ✅ Implemented Tables

**Transaction**: hash, date, account, details, description, search_text, merchant, amount, amount_signed, category, debit_credit, balance, created_at

**Category**: name, color, keywords, exclude_keywords, match_both_fields, user_id

**UserAccount**: account_name, account_number, account_number_masked, bank, is_primary

**BackgroundJob**: job_id, status, progress, total_items, processed_items, result, error, timestamps

**UnparsedFile**: original_filename, stored_filename, detected_bank, detection_confidence, user_provided_bank, error_message

**ChatSession**: session_id, title, messages, context, token_count

**LLMCache**: cache_key, response, created_at

**TokenUsage**: session_id, tokens_used, cost, timestamp

### 📅 Planned Tables

**User**: email, tier (free/premium), transaction_count, token_usage, daily_question_count

**PlannedTransaction**: (extends Transaction with plan_name, is_matched)

**CategoryTemplate** (Admin): name, keywords, color, banks, active

**SalaryConfig**: amount, day_of_month, category

---

## API Contracts

### ✅ Implemented Endpoints

#### Transactions
- ✅ `GET /api/data/transactions` - Filtered list with pagination
- ✅ `GET /api/data/summary` - Summary statistics
- ✅ `GET /api/data/spending-trends` - Spending analysis
- ✅ `GET /api/data/top-merchants` - Merchant analysis
- ✅ `POST /api/upload` - Multi-bank file upload

#### Categories
- ✅ `GET /api/categories/` - List all categories
- ✅ `POST /api/categories/` - Create category
- ✅ `PUT /api/categories/{id}` - Update category
- ✅ `DELETE /api/categories/{id}` - Delete category
- ✅ `POST /api/categories/categorize` - Trigger categorization

#### Accounts
- ✅ `GET /api/accounts/` - List accounts
- ✅ `POST /api/accounts/` - Create account
- ✅ `DELETE /api/accounts/{id}` - Delete account

#### Chat
- ✅ `GET /api/chat/sessions` - List chat sessions
- ✅ `POST /api/chat/sessions` - Create session
- ✅ `GET /api/chat/sessions/{id}` - Get session details
- ✅ `DELETE /api/chat/sessions/{id}` - Delete session
- ✅ `POST /api/chat/sessions/{id}/messages` - Send message
- ✅ `POST /api/chat/sessions/{id}/context` - Attach context
- ✅ `GET /api/chat/sessions/{id}/context` - Get context info

#### Background Jobs
- ✅ `POST /api/jobs/recategorize` - Trigger recategorization
- ✅ `GET /api/jobs/{id}` - Get job status
- ✅ `GET /api/jobs/` - List user jobs

#### LLM
- ✅ `POST /api/llm/generate-rule` - Generate categorization rule
- ✅ `POST /api/llm/suggest-category` - Suggest category

#### Rule Manager
- ✅ `GET /api/rules/merchants` - Aggregated merchants with rule match info
- ✅ `GET /api/rules/find-match` - Find rule matching a merchant
- ✅ `POST /api/rules/bulk-assign` - Assign category to multiple merchants

#### Unparsed Files
- ✅ `GET /api/unparsed-files` - List unparsed files
- ✅ `DELETE /api/unparsed-files/{id}` - Delete unparsed file

#### Notifications
- ✅ WebSocket: `/ws/{user_id}` - Real-time notifications

### 📅 Planned Endpoints

#### Auth
- [ ] `POST /auth/register`, `/auth/login`, `/auth/google`, `/auth/logout`

#### Budget & Planning
- [ ] `POST /transactions/planned` - Create planned transaction(s) with auto-split
- [ ] `PUT /transactions/{id}` - Update transaction (planned only)
- [ ] `DELETE /transactions/{id}` - Delete transaction (planned only)
- [ ] `GET /budget/overview` - Monthly balance (planned income vs expenses)
- [ ] `GET /chart/weekly`, `/chart/monthly` - Aggregated data (actual + planned)

#### Settings
- [ ] `PUT /settings/salary-day` - Set salary day (1-31)
- [ ] `PUT /settings/salary` - Configure salary (amount, day, category)
- [ ] `GET /settings` - Get all user settings

#### Admin
- [ ] `GET /admin/templates`, `POST /admin/templates`
- [ ] `GET /admin/unparsed-files` - Download unparsed files

#### Payments
- [ ] `POST /payments/checkout`, `/payments/webhook`

#### Usage
- [ ] `GET /usage/tokens`, `/usage/history`
- [ ] `GET /usage/daily-questions` - Check daily question limit

---

## Success Criteria

### ✅ Current Performance
- ✅ Upload processing: < 5s for 500 transactions
- ✅ Chart rendering: N/A (not yet implemented)
- ✅ Filter updates: < 500ms
- ✅ Chat response: < 3s
- ✅ Re-categorization: < 10s for 1,000 transactions
- ✅ WebSocket latency: < 100ms
- ✅ Test coverage: 40/40 passing

### 📅 Planned Targets
- [ ] AI categorization: < 5% in "Others"
- [ ] Free tier: 3 questions/day
- [ ] Context limit: UI prevents > 1,000 selection
- [ ] Payment success rate: 99%+ (UAE cards)
- [ ] Budget balance calculation: instant
- [ ] Planned item creation: < 2s

---

## Next Steps

### Phase 2: Authentication & Multi-User (Postponed)
- Implement Auth0 or Cognito
- User registration and login
- Free tier (3 questions/day) vs Premium (unlimited)
- User-specific data isolation

### Phase 3: Visualizations & Budget
- Implement chart components
- Budget planning UI
- Planned transactions
- Salary configuration
- Monthly balance overview

### Phase 4: Admin & Payments
- Admin panel for category templates
- Stripe integration
- Subscription management
- Usage monitoring

---

**For detailed implementation status and technical documentation, see:**
- [Implementation Complete Report](./implementation-complete.md)
- Backend tests: `/backend/tests/test_milestone_*.py`
- Frontend components: `/frontend/app/components/`, `/frontend/app/settings/`
