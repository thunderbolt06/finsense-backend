# FinSense API Examples

## 1. `/api/query` - Chat Endpoint

### Request (Start New Chat)

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the current stock price of AAPL?",
    "chat_id": null
  }'
```

### Request (Continue Existing Chat)

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How about GOOG?",
    "chat_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

### Streaming Response Format

The response is a Server-Sent Events (SSE) stream. Each line follows this format:

```
data: <JSON>\n\n
```

**Token Events:**
```
data: {"text": "I'll", "event": "token"}

data: {"text": " search", "event": "token"}

data: {"text": " for", "event": "token"}

[... more tokens ...]

data: {"text": " According to the latest data, AAPL is trading at $175.23.", "event": "token"}
```

**Done Event (includes chat_id):**
```
data: {"event": "done", "chat_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
```

### JavaScript/Fetch Example

```javascript
async function queryAPI(question, chatId = null) {
  const response = await fetch('http://localhost:8000/api/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: question,
      chat_id: chatId
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let chatId = null;
  let fullText = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6); // Remove 'data: ' prefix
        if (jsonStr.trim()) {
          try {
            const data = JSON.parse(jsonStr);
            
            if (data.event === 'token') {
              fullText += data.text;
              // Update UI with streaming text
              console.log('Token:', data.text);
            } else if (data.event === 'done') {
              chatId = data.chat_id;
              console.log('Chat ID:', chatId);
              // Store chat_id for subsequent requests
              localStorage.setItem('chatId', chatId);
            }
          } catch (e) {
            console.error('Failed to parse:', jsonStr, e);
          }
        }
      }
    }
  }
  
  return { fullText, chatId };
}

// Usage
queryAPI("What is the stock price of AAPL?").then(({ fullText, chatId }) => {
  console.log('Complete response:', fullText);
  console.log('Chat ID to use for follow-ups:', chatId);
});
```

### Python/requests Example

```python
import requests
import json

def query_api(question, chat_id=None):
    url = "http://localhost:8000/api/query"
    payload = {
        "question": question,
        "chat_id": chat_id
    }
    
    response = requests.post(url, json=payload, stream=True)
    
    chat_id_received = None
    full_text = ""
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                json_str = line_str[6:]  # Remove 'data: ' prefix
                if json_str.strip():
                    try:
                        data = json.loads(json_str)
                        if data.get('event') == 'token':
                            full_text += data.get('text', '')
                            print(data.get('text', ''), end='', flush=True)
                        elif data.get('event') == 'done':
                            chat_id_received = data.get('chat_id')
                            print(f"\n\nChat ID: {chat_id_received}")
                    except json.JSONDecodeError:
                        pass
    
    return full_text, chat_id_received

# Usage
text, chat_id = query_api("What is the stock price of AAPL?")
print(f"\nComplete response: {text}")
print(f"Chat ID: {chat_id}")
```

---

## 2. `/api/traces` - Get All Chat Histories

### Request

```bash
curl "http://localhost:8000/api/traces"
```

### Response

```json
{
  "status": "ok",
  "count": 2,
  "traces": [
    {
      "chat_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "New Chat",
      "finished": true,
      "created_at": "2025-01-15T10:30:45.123456+00:00",
      "updated_at": "2025-01-15T10:31:12.456789+00:00",
      "chat_history": [
        [
          "user",
          "text:What is the current stock price of AAPL?"
        ],
        [
          "assistant",
          "text:I'll search for the current stock price of AAPL..."
        ],
        [
          "tool",
          "tool_result:{\"tool_id\": null, \"result\": \"...\", \"func_name\": \"chat_with_web_search\"}"
        ],
        [
          "assistant",
          "text:According to the latest data, AAPL is trading at $175.23..."
        ]
      ]
    },
    {
      "chat_id": "f9e8d7c6-b5a4-3210-9876-fedcba098765",
      "title": "New Chat",
      "finished": true,
      "created_at": "2025-01-15T09:15:30.654321+00:00",
      "updated_at": "2025-01-15T09:16:45.789012+00:00",
      "chat_history": [
        [
          "user",
          "text:Tell me about Tesla's latest earnings"
        ],
        [
          "assistant",
          "text:Let me search for Tesla's latest earnings information..."
        ]
      ]
    }
  ]
}
```

### JavaScript Example

```javascript
async function getTraces() {
  const response = await fetch('http://localhost:8000/api/traces');
  const data = await response.json();
  
  console.log(`Found ${data.count} chats`);
  
  data.traces.forEach(trace => {
    console.log(`\nChat ID: ${trace.chat_id}`);
    console.log(`Title: ${trace.title}`);
    console.log(`Created: ${trace.created_at}`);
    console.log(`History:`, trace.chat_history);
  });
  
  return data;
}

// Usage
getTraces().then(data => {
  console.log('All traces:', data);
});
```

### Python Example

```python
import requests

def get_traces():
    url = "http://localhost:8000/api/traces"
    response = requests.get(url)
    data = response.json()
    
    print(f"Found {data['count']} chats")
    
    for trace in data['traces']:
        print(f"\nChat ID: {trace['chat_id']}")
        print(f"Title: {trace['title']}")
        print(f"Created: {trace['created_at']}")
        print(f"History: {trace['chat_history']}")
    
    return data

# Usage
traces = get_traces()
```

---

## 3. Other Endpoints

### `/api/ping` - Health Check

```bash
curl "http://localhost:8000/api/ping"
```

**Response:**
```json
{
  "status": "ok",
  "message": "FinSense API is running"
}
```

### `/api/db-test` - Database Test

```bash
curl "http://localhost:8000/api/db-test"
```

**Response:**
```json
{
  "status": "ok",
  "created_id": "uuid-here",
  "retrieved_id": "uuid-here",
  "title": "Test Chat"
}
```

---

## Complete Frontend Integration Example

```javascript
class FinSenseClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.chatId = localStorage.getItem('chatId');
  }

  async query(question) {
    const response = await fetch(`${this.baseURL}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question,
        chat_id: this.chatId
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          if (jsonStr.trim()) {
            try {
              const data = JSON.parse(jsonStr);
              if (data.event === 'token') {
                fullText += data.text;
                // Emit token event for UI updates
                this.onToken?.(data.text);
              } else if (data.event === 'done') {
                this.chatId = data.chat_id;
                localStorage.setItem('chatId', data.chat_id);
                // Emit done event
                this.onDone?.(fullText, data.chat_id);
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    }
    
    return fullText;
  }

  async getTraces() {
    const response = await fetch(`${this.baseURL}/api/traces`);
    return await response.json();
  }

  // Event handlers
  onToken = null;  // (text: string) => void
  onDone = null;  // (fullText: string, chatId: string) => void
}

// Usage
const client = new FinSenseClient();

client.onToken = (text) => {
  document.getElementById('response').innerText += text;
};

client.onDone = (fullText, chatId) => {
  console.log('Complete:', fullText);
  console.log('Chat ID:', chatId);
};

client.query("What is AAPL stock price?");
```

