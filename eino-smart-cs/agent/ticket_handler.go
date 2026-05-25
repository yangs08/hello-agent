package agent

import (
	"context"
	"fmt"

	"eino-smart-cs/memory"
)

type ticketAgent struct {
	store *memory.TicketStore
}

func newTicketAgent(store *memory.TicketStore) *ticketAgent {
	return &ticketAgent{store: store}
}

func (ta *ticketAgent) process(ctx context.Context, state *AgentState) {
	priority := "medium"
	ticket := ta.store.Create(state.UserID, state.Message, priority)
	result := fmt.Sprintf("Ticket created successfully. Ticket ID: %s, Priority: %s, Status: %s. "+
		"Our support team will follow up within 24 hours.",
		ticket.ID, ticket.Priority, ticket.Status)
	state.SubResults["ticket"] = result
}
