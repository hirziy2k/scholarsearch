# Client-Side Hydration Loop

## SSE Stream Consumer Specification

This document defines the exact state machine required to consume Swarm Cascade SSE streams safely. The frontend MUST implement this protocol to handle network instability, cursor-based reconnection, and heartbeat monitoring.

---

## 1. Connection Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    HYDRATION STATE MACHINE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  IDLE    │───►│CONNECTING│───►│STREAMING │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │              │              │                        │
│       │              │              ▼                        │
│       │              │         ┌──────────┐                 │
│       │              │         │RECONNECTING                │
│       │              │         └──────────┘                 │
│       │              │              │                        │
│       ▼              ▼              ▼                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │DISCONNECT│◄───│  ERROR   │◄───│HEARTBEAT │              │
│  └──────────┘    └──────────┘    │ TIMEOUT  │              │
│                                  └──────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 2. State Definitions

| State | Description | Transitions |
|-------|-------------|-------------|
| `IDLE` | No active connection | → `CONNECTING` (on query submit) |
| `CONNECTING` | Establishing SSE connection | → `STREAMING` (on open), → `ERROR` (on failure) |
| `STREAMING` | Receiving events | → `RECONNECTING` (on close), → `COMPLETE` (on final event) |
| `RECONNECTING` | Attempting cursor-based reconnect | → `STREAMING` (on success), → `ERROR` (on failure) |
| `HEARTBEAT_TIMEOUT` | Missed 2+ heartbeats | → `RECONNECTING` |
| `ERROR` | Unrecoverable failure | → `IDLE` (after backoff) |
| `COMPLETE` | Stream finished | → `IDLE` |

## 3. Event Schema

```typescript
interface SwarmEvent {
  event_type: 'phase' | 'triage' | 'progress' | 'matrix' | 'boundary' | 'heartbeat' | 'complete' | 'error';
  data: Record<string, any>;
  timestamp: number;
  sequence: number;
}

interface SSEMessage {
  event: string;        // Maps to SwarmEvent.event_type
  data: string;         // JSON-encoded SwarmEvent
  id: string;           // Sequence number for cursor tracking
}
```

## 4. Hydration Protocol

### 4.1 Initial Connection

```typescript
function connectToSwarm(queryHash: string): EventSource {
  const source = new EventSource(`/api/stream/${queryHash}`);
  
  source.onmessage = (event) => {
    const swarmEvent: SwarmEvent = JSON.parse(event.data);
    handleSwarmEvent(swarmEvent);
    updateCursorPosition(event.lastEventId);
  };
  
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) {
      transitionTo('RECONNECTING');
    }
  };
  
  return source;
}
```

### 4.2 Cursor-Based Reconnection

```typescript
function reconnectWithCursor(queryHash: string, lastCursor: string): void {
  const source = new EventSource(
    `/api/stream/${queryHash}?cursor=${lastCursor}`
  );
  
  // Server replays missed frames automatically
  source.onmessage = (event) => {
    const swarmEvent: SwarmEvent = JSON.parse(event.data);
    handleSwarmEvent(swarmEvent);
    updateCursorPosition(event.lastEventId);
  };
}
```

### 4.3 Heartbeat Monitor

```typescript
const HEARTBEAT_INTERVAL = 5000;  // Server sends every 5s
const HEARTBEAT_TIMEOUT = 15000;  // Miss 3 = reconnect

let lastHeartbeat = Date.now();
let heartbeatTimer: NodeJS.Timeout;

function startHeartbeatMonitor() {
  heartbeatTimer = setInterval(() => {
    if (Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT) {
      transitionTo('HEARTBEAT_TIMEOUT');
      reconnectWithCursor(currentQueryHash, lastCursorPosition);
    }
  }, HEARTBEAT_INTERVAL);
}

function onHeartbeat() {
  lastHeartbeat = Date.now();
  updatePulseIndicator();  // Banana-yellow pulse
}
```

## 5. UI Rendering Rules

### 5.1 Visual Design Tokens

```css
:root {
  /* Background */
  --bg-primary: #FAFAF8;        /* Clean off-white */
  --bg-secondary: #F5F5F0;      /* Slightly warmer */
  
  /* Typography */
  --text-primary: #2D2D2D;      /* Crisp charcoal */
  --text-secondary: #5A5A5A;    /* Muted charcoal */
  --text-accent: #1A1A1A;       /* Near-black for headers */
  
  /* Status Indicator */
  --pulse-color: #FFD93D;       /* Banana-yellow */
  --pulse-glow: rgba(255, 217, 61, 0.4);
  
  /* Layout */
  --content-max-width: 720px;
  --line-height: 1.7;
  --letter-spacing: -0.01em;
}
```

### 5.2 Pulse Indicator

```css
.status-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pulse-color);
  animation: pulse 3s infinite;
}

@keyframes pulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 var(--pulse-glow);
  }
  50% { 
    box-shadow: 0 0 0 8px transparent;
  }
}

.status-pulse.disconnected {
  background: #CCC;
  animation: none;
}
```

### 5.3 Event Rendering Map

| Event Type | UI Action |
|------------|-----------|
| `phase` | Update phase indicator, show/hide sections |
| `triage` | Display routing decision with confidence score |
| `progress` | Update progress bar, show "Searching..." |
| `matrix` | Render contradiction analysis card |
| `boundary` | Show boundary condition annotation |
| `heartbeat` | Pulse banana-yellow indicator |
| `complete` | Fade in final report, hide loading states |
| `error` | Show error toast with retry button |

## 6. Error Recovery Protocol

```typescript
const MAX_RECONNECT_ATTEMPTS = 5;
const BACKOFF_BASE_MS = 1000;
const BACKOFF_MAX_MS = 30000;

async function reconnectWithBackoff(
  queryHash: string, 
  cursor: string,
  attempt: number = 0
): Promise<void> {
  if (attempt >= MAX_RECONNECT_ATTEMPTS) {
    transitionTo('ERROR');
    showErrorToast('Connection lost. Please refresh.');
    return;
  }
  
  const delay = Math.min(
    BACKOFF_BASE_MS * Math.pow(2, attempt),
    BACKOFF_MAX_MS
  );
  
  await sleep(delay);
  
  try {
    reconnectWithCursor(queryHash, cursor);
  } catch {
    reconnectWithBackoff(queryHash, cursor, attempt + 1);
  }
}
```

## 7. Cursor Position Tracking

```typescript
let cursorPosition: string = '0';
let cursorHistory: string[] = [];

function updateCursorPosition(newCursor: string) {
  if (newCursor !== cursorPosition) {
    cursorHistory.push(cursorPosition);
    cursorPosition = newCursor;
    
    // Persist to sessionStorage for tab recovery
    sessionStorage.setItem('swarm_cursor', JSON.stringify({
      queryHash: currentQueryHash,
      cursor: cursorPosition,
      timestamp: Date.now(),
    }));
  }
}

function recoverCursorPosition(): string | null {
  const stored = sessionStorage.getItem('swarm_cursor');
  if (stored) {
    const { queryHash, cursor, timestamp } = JSON.parse(stored);
    if (queryHash === currentQueryHash && Date.now() - timestamp < 300000) {
      return cursor;
    }
  }
  return null;
}
```

## 8. Complete State Machine Implementation

```typescript
class SwarmHydrationMachine {
  private state: SwarmState = 'IDLE';
  private eventSource: EventSource | null = null;
  private cursorPosition: string = '0';
  private lastHeartbeat: number = Date.now();
  private queryHash: string = '';
  
  async connect(queryHash: string): Promise<void> {
    this.queryHash = queryHash;
    this.transitionTo('CONNECTING');
    
    const savedCursor = recoverCursorPosition();
    if (savedCursor) {
      this.cursorPosition = savedCursor;
    }
    
    this.eventSource = new EventSource(
      `/api/stream/${queryHash}?cursor=${this.cursorPosition}`
    );
    
    this.eventSource.onopen = () => {
      this.transitionTo('STREAMING');
      startHeartbeatMonitor();
    };
    
    this.eventSource.onmessage = (event) => {
      const swarmEvent: SwarmEvent = JSON.parse(event.data);
      this.handleEvent(swarmEvent);
      this.cursorPosition = event.lastEventId;
    };
    
    this.eventSource.onerror = () => {
      this.handleError();
    };
  }
  
  private handleEvent(event: SwarmEvent): void {
    switch (event.event_type) {
      case 'heartbeat':
        this.lastHeartbeat = Date.now();
        updatePulseIndicator();
        break;
      case 'complete':
        this.transitionTo('COMPLETE');
        this.disconnect();
        renderFinalReport(event.data);
        break;
      case 'error':
        this.transitionTo('ERROR');
        showErrorToast(event.data.message);
        break;
      default:
        renderSwarmEvent(event);
    }
  }
  
  private handleError(): void {
    if (this.eventSource?.readyState === EventSource.CLOSED) {
      this.transitionTo('RECONNECTING');
      reconnectWithBackoff(this.queryHash, this.cursorPosition);
    }
  }
  
  private transitionTo(newState: SwarmState): void {
    this.state = newState;
    updateStateIndicator(newState);
  }
  
  disconnect(): void {
    this.eventSource?.close();
    this.eventSource = null;
    transitionTo('IDLE');
  }
}
```

---

## Integration with Swarm Cascade

The client connects to the SSE endpoint exposed by `sse_handler.py`:

```
POST /api/research
  → Returns { query_hash: "abc123" }

GET /api/stream/abc123
  → SSE stream with cursor-based replay

GET /api/stream/abc123?cursor=1709420000-5
  → Replay from event 1709420000-5
```

The banana-yellow pulse indicator syncs with the 3-second heartbeat from `heartbeat_mutex.py`. If the pulse stops, the client automatically triggers cursor-based reconnection.
