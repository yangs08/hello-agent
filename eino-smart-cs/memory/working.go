package memory

import (
	"sync"
	"time"
)

type Message struct {
	Role    string    `json:"role"`
	Content string    `json:"content"`
	Time    time.Time `json:"time"`
}

type SessionMemory struct {
	Messages  []Message
	Context   map[string]string
	CreatedAt time.Time
}

type WorkingMemory struct {
	mu       sync.RWMutex
	sessions map[string]*SessionMemory
	maxTurns int
}

func NewWorkingMemory(maxTurns int) *WorkingMemory {
	if maxTurns <= 0 {
		maxTurns = 20
	}
	return &WorkingMemory{
		sessions: make(map[string]*SessionMemory),
		maxTurns: maxTurns,
	}
}

func (wm *WorkingMemory) AddMessage(sessionID, role, content string) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	session := wm.getOrCreateSession(sessionID)
	session.Messages = append(session.Messages, Message{Role: role, Content: content, Time: time.Now()})
	if len(session.Messages) > wm.maxTurns*2 {
		session.Messages = session.Messages[len(session.Messages)-wm.maxTurns*2:]
	}
}

func (wm *WorkingMemory) SetContext(sessionID, key, value string) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	session := wm.getOrCreateSession(sessionID)
	session.Context[key] = value
}

func (wm *WorkingMemory) GetContext(sessionID, key string) string {
	wm.mu.RLock()
	defer wm.mu.RUnlock()
	if session, ok := wm.sessions[sessionID]; ok {
		return session.Context[key]
	}
	return ""
}

func (wm *WorkingMemory) GetHistory(sessionID string) []Message {
	wm.mu.RLock()
	defer wm.mu.RUnlock()
	if session, ok := wm.sessions[sessionID]; ok {
		result := make([]Message, len(session.Messages))
		copy(result, session.Messages)
		return result
	}
	return nil
}

func (wm *WorkingMemory) GetContextWindow(sessionID string, maxTokens int) []Message {
	wm.mu.RLock()
	defer wm.mu.RUnlock()
	session, ok := wm.sessions[sessionID]
	if !ok {
		return nil
	}
	msgs := session.Messages
	var result []Message
	tokens := 0
	for i := len(msgs) - 1; i >= 0; i-- {
		msgTokens := len(msgs[i].Content) / 2
		if tokens+msgTokens > maxTokens {
			break
		}
		tokens += msgTokens
		result = append([]Message{msgs[i]}, result...)
	}
	return result
}

func (wm *WorkingMemory) getOrCreateSession(sessionID string) *SessionMemory {
	session, ok := wm.sessions[sessionID]
	if !ok {
		session = &SessionMemory{
			Messages:  make([]Message, 0),
			Context:   make(map[string]string),
			CreatedAt: time.Now(),
		}
		wm.sessions[sessionID] = session
	}
	return session
}
