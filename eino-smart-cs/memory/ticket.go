package memory

import (
	"sync"
	"time"
)

type Ticket struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	Summary   string    `json:"summary"`
	Priority  string    `json:"priority"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
}

type TicketStore struct {
	mu      sync.RWMutex
	tickets []Ticket
	counter int
}

func NewTicketStore() *TicketStore {
	return &TicketStore{
		tickets: make([]Ticket, 0),
	}
}

func (ts *TicketStore) Create(userID, summary, priority string) Ticket {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	ts.counter++
	now := time.Now()
	id := now.Format("20060102") + "-" + itoa(ts.counter)
	if priority == "" {
		priority = "medium"
	}
	ticket := Ticket{
		ID:        "TK-" + id,
		UserID:    userID,
		Summary:   summary,
		Priority:  priority,
		Status:    "created",
		CreatedAt: now,
	}
	ts.tickets = append(ts.tickets, ticket)
	return ticket
}

func (ts *TicketStore) List() []Ticket {
	ts.mu.RLock()
	defer ts.mu.RUnlock()
	result := make([]Ticket, len(ts.tickets))
	copy(result, ts.tickets)
	return result
}
