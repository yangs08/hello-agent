package agent

import (
	"context"
	"fmt"
	"strings"

	"eino-smart-cs/memory"
)

type Supervisor struct {
	intentRouter    *intentRouter
	ragAgent        *ragAgent
	ticketAgent     *ticketAgent
	complianceAgent *complianceAgent
	llm             *LLMClient
	workingMemory   *memory.WorkingMemory
}

func NewSupervisor(llm *LLMClient, kb *memory.KnowledgeBase, store *memory.TicketStore, wm *memory.WorkingMemory) *Supervisor {
	return &Supervisor{
		intentRouter:    newIntentRouter(llm),
		ragAgent:        newRAGAgent(llm, kb),
		ticketAgent:     newTicketAgent(store),
		complianceAgent: newComplianceAgent(llm),
		llm:             llm,
		workingMemory:   wm,
	}
}

func (s *Supervisor) Process(ctx context.Context, state *AgentState) {
	s.intentRouter.classify(ctx, state)

	switch state.Intent {
	case "knowledge_rag":
		s.ragAgent.process(ctx, state)
	case "ticket":
		s.ticketAgent.process(ctx, state)
	case "chat":
		s.handleChat(ctx, state)
	default:
		s.ragAgent.process(ctx, state)
	}

	s.complianceAgent.process(ctx, state)

	s.synthesize(state)
}

func (s *Supervisor) handleChat(ctx context.Context, state *AgentState) {
	if s.llm.IsAvailable() {
		var historyStr string
		for _, msg := range state.History {
			historyStr += fmt.Sprintf("%s: %s\n", msg.Role, msg.Content)
		}

		systemPrompt := `You are a friendly customer service assistant. Respond to the user in a helpful and conversational manner.`
		userPrompt := fmt.Sprintf("Conversation history:\n%s\n\nUser: %s\nAssistant:", historyStr, state.Message)

		result, err := s.llm.Generate(ctx, systemPrompt, userPrompt)
		if err == nil && result != "" {
			state.SubResults["chat"] = result
			return
		}
	}
	state.SubResults["chat"] = fmt.Sprintf("Hello! I'm your customer service assistant. " +
		"I can help you with product information, account queries, ticket creation, and compliance-related questions. " +
		"How can I help you today?")
}

func (s *Supervisor) synthesize(state *AgentState) {
	if !state.CompliancePassed {
		state.FinalResponse = "I've noted your request. However, it has been flagged for compliance review " +
			"and will be forwarded to our specialized team for handling. We'll get back to you shortly. " +
			"If you have any other questions, feel free to ask."
		return
	}

	var parts []string
	if result, ok := state.SubResults[state.Intent]; ok && result != "" {
		parts = append(parts, result)
	}

	for intent, result := range state.SubResults {
		if intent != state.Intent && result != "" {
			parts = append(parts, result)
		}
	}

	if len(parts) > 0 {
		state.FinalResponse = strings.Join(parts, "\n\n")
	} else {
		state.FinalResponse = "Thank you for your message. How can I assist you further?"
	}
}
