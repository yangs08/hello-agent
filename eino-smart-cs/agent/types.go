package agent

import "eino-smart-cs/memory"

type AgentState struct {
	UserID    string
	SessionID string
	Message   string
	History   []memory.Message

	Intent           string
	IntentConfidence float64
	SubResults       map[string]string
	CompliancePassed bool
	ComplianceRisk   string
	FinalResponse    string
}

func NewAgentState(userID, sessionID, message string, history []memory.Message) *AgentState {
	return &AgentState{
		UserID:     userID,
		SessionID:  sessionID,
		Message:    message,
		History:    history,
		SubResults: make(map[string]string),
	}
}
