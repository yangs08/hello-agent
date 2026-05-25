package tools

import (
	"context"
	"encoding/json"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
)

type TicketCreateTool struct {
	createFunc func(ctx context.Context, userID, summary, priority string) string
}

func NewTicketCreateTool(createFunc func(ctx context.Context, userID, summary, priority string) string) *TicketCreateTool {
	return &TicketCreateTool{createFunc: createFunc}
}

func (t *TicketCreateTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
	return &schema.ToolInfo{
		Name: "ticket_create",
		Desc: "Create a customer service ticket for the user's issue or request. " +
			"Use this when the user reports a problem, makes a request that needs follow-up, or asks to create a ticket.",
		ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
			"user_id": {
				Type:     schema.String,
				Desc:     "The user ID associated with the ticket",
				Required: true,
			},
			"summary": {
				Type:     schema.String,
				Desc:     "A brief summary of the issue or request",
				Required: true,
			},
			"priority": {
				Type: schema.String,
				Desc: "Priority level: low, medium, high, critical (default: medium)",
				Enum: []string{"low", "medium", "high", "critical"},
			},
		}),
	}, nil
}

func (t *TicketCreateTool) InvokableRun(ctx context.Context, argumentsInJSON string, opts ...tool.Option) (string, error) {
	var params struct {
		UserID   string `json:"user_id"`
		Summary  string `json:"summary"`
		Priority string `json:"priority"`
	}
	if err := json.Unmarshal([]byte(argumentsInJSON), &params); err != nil {
		return "", err
	}
	if params.Priority == "" {
		params.Priority = "medium"
	}
	return t.createFunc(ctx, params.UserID, params.Summary, params.Priority), nil
}

var _ tool.BaseTool = (*TicketCreateTool)(nil)
var _ tool.InvokableTool = (*TicketCreateTool)(nil)
