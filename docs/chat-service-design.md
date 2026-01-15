# Chat Service - Solution Design

**Service**: AI Chat with Tool Calling  
**Port**: 8004  
**Repository**: `services/chat-service/`

---

## Responsibility

- Manage chat sessions & messages
- AI agent with tool calling (transactions, categories)
- Context injection (1000 recent transactions)
- Token usage tracking & display

---

## API Endpoints

### Chat Sessions
```
GET /chat/sessions?person_id=...
  Returns: [ChatSession]

POST /chat/sessions
  Body: { person_id, title? }
  Returns: ChatSession

DELETE /chat/sessions/{id}
  Returns: { success: true }
```

### Messages
```
GET /chat/sessions/{id}/messages
  Returns: [Message]

POST /chat/sessions/{id}/messages
  Body: { content: string }
  Returns: {
    message: Message,
    token_usage: {
      prompt_tokens: number,
      completion_tokens: number,
      total_tokens: number,
      cost_usd: number
    }
  }

PUT /chat/messages/{id}/regenerate
  Returns: { message: Message, token_usage }
```

---

## Data Model

### chat_sessions
```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL,
  title VARCHAR(255) DEFAULT 'New Chat',
  total_tokens INTEGER DEFAULT 0,
  total_cost_usd DECIMAL(10,6) DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_person (person_id)
);
```

### chat_messages
```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'tool'
  content TEXT NOT NULL,
  tool_calls JSONB,  -- Array of tool calls
  tool_call_id VARCHAR(100),  -- For tool responses
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  total_tokens INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_session (session_id)
);
```

---

## AI Agent with Tools

### Tool Definitions
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_transactions",
            "description": "Get transactions for analysis. Use filters to narrow down results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "category": {"type": "string"},
                    "merchant": {"type": "string"},
                    "min_amount": {"type": "number"},
                    "max_amount": {"type": "number"},
                    "limit": {"type": "integer", "default": 100}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_categories",
            "description": "Get all categories for this person",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_summary",
            "description": "Get spending summary by category for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_transactions",
            "description": "Search transactions by text in merchant/details/description",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]
```

### Tool Implementations
```python
async def execute_tool(tool_name: str, arguments: dict, person_id: str) -> str:
    """Execute tool and return result as JSON string"""
    
    if tool_name == "get_transactions":
        response = await httpx.get(
            f"{TRANSACTION_SERVICE_URL}/transactions",
            params={**arguments, "person_id": person_id}
        )
        return response.text
    
    elif tool_name == "get_categories":
        response = await httpx.get(
            f"{CATEGORY_SERVICE_URL}/categories",
            params={"person_id": person_id}
        )
        return response.text
    
    elif tool_name == "get_spending_summary":
        response = await httpx.get(
            f"{TRANSACTION_SERVICE_URL}/transactions/summary",
            params={**arguments, "person_id": person_id}
        )
        return response.text
    
    elif tool_name == "search_transactions":
        response = await httpx.get(
            f"{TRANSACTION_SERVICE_URL}/transactions",
            params={"person_id": person_id, "search": arguments["query"]}
        )
        return response.text
    
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
```

---

## Chat Flow with Context Injection

```python
async def send_message(session_id: str, person_id: str, user_content: str) -> dict:
    """
    1. Get recent messages from session
    2. Inject context (1000 recent transactions + categories)
    3. Call LLM with tools
    4. Execute tool calls if any
    5. Continue conversation until done
    6. Track token usage
    """
    
    # Get conversation history
    messages = await get_session_messages(session_id)
    
    # Prepare context (injected once at start of conversation)
    if len(messages) == 0:
        context = await prepare_context(person_id)
        system_message = {
            "role": "system",
            "content": f"""
You are a financial assistant. Help the user analyze their transactions.

CONTEXT (Last 1000 transactions + categories):
{context}

Use tools to get more specific data when needed.
"""
        }
        conversation = [system_message]
    else:
        conversation = [{"role": m.role, "content": m.content} for m in messages]
    
    # Add user message
    conversation.append({"role": "user", "content": user_content})
    
    # Call LLM with tools
    total_tokens = 0
    while True:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation,
            tools=TOOLS,
            tool_choice="auto"
        )
        
        total_tokens += response.usage.total_tokens
        assistant_message = response.choices[0].message
        
        # No tool calls → conversation done
        if not assistant_message.tool_calls:
            await save_message(session_id, "assistant", assistant_message.content, 
                             response.usage.prompt_tokens, response.usage.completion_tokens)
            break
        
        # Execute tool calls
        conversation.append(assistant_message)
        
        for tool_call in assistant_message.tool_calls:
            tool_result = await execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                person_id
            )
            
            conversation.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })
    
    # Update session totals
    cost_usd = calculate_cost(total_tokens)
    await update_session_usage(session_id, total_tokens, cost_usd)
    
    return {
        "message": assistant_message.content,
        "token_usage": {
            "total_tokens": total_tokens,
            "cost_usd": cost_usd
        }
    }

async def prepare_context(person_id: str) -> str:
    """Get last 1000 transactions + categories"""
    
    # Get transactions
    response = await httpx.get(
        f"{TRANSACTION_SERVICE_URL}/transactions",
        params={"person_id": person_id, "limit": 1000}
    )
    transactions = response.json()
    
    # Get categories
    response = await httpx.get(
        f"{CATEGORY_SERVICE_URL}/categories",
        params={"person_id": person_id}
    )
    categories = response.json()
    
    # Format as concise text
    txn_text = "\n".join([
        f"{t['date']}: {t['merchant']} - {t['category']} - {t['amount_signed']} AED"
        for t in transactions[:1000]
    ])
    
    cat_text = ", ".join([c['name'] for c in categories])
    
    return f"""
CATEGORIES:
{cat_text}

TRANSACTIONS (last 1000):
{txn_text}
"""

def calculate_cost(tokens: int, model: str = "gpt-4o-mini") -> float:
    """Calculate cost in USD based on token usage"""
    # gpt-4o-mini pricing (as of 2025)
    COST_PER_1M_TOKENS = 0.15
    return (tokens / 1_000_000) * COST_PER_1M_TOKENS
```

---

## Token Usage Display

### Frontend Display
```typescript
interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

// Display in chat header
<div className="text-xs text-muted-foreground">
  Session: {session.total_tokens.toLocaleString()} tokens 
  (${session.total_cost_usd.toFixed(4)})
</div>

// Display per message (hover tooltip)
<Tooltip>
  <TooltipTrigger>ⓘ</TooltipTrigger>
  <TooltipContent>
    {message.total_tokens} tokens (${cost.toFixed(4)})
  </TooltipContent>
</Tooltip>
```

---

## Dependencies

### Internal
- Transaction Service
- Category Service

### External
- OpenAI API
- PostgreSQL (chat schema)
- Redis (caching)

---

## Technology

- **Framework**: FastAPI
- **LLM**: OpenAI SDK (gpt-4o-mini)
- **HTTP Client**: httpx (async)
- **Database**: PostgreSQL

---

## Testing

```python
@pytest.mark.asyncio
async def test_chat_with_tools():
    session = await create_session(person_id)
    
    # User asks about spending
    response = await send_message(
        session.id,
        person_id,
        "How much did I spend on coffee last month?"
    )
    
    assert "tool_calls" in response or "assistant" in response
    assert response["token_usage"]["total_tokens"] > 0

def test_token_cost_calculation():
    cost = calculate_cost(10000)  # 10k tokens
    assert 0.001 < cost < 0.002  # ~$0.0015
```

---

## Monitoring

- Average tokens per message
- Tool call frequency
- Response latency
- Cost per session

---

**Status**: Ready for implementation  
**Owner**: AI/Chat Team  
**Dependencies**: Transaction Service, Category Service, OpenAI



