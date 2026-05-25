package tools

import (
	"context"
	"encoding/json"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
)

type OrderQueryTool struct{}

func NewOrderQueryTool() *OrderQueryTool {
	return &OrderQueryTool{}
}

func (o *OrderQueryTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
	return &schema.ToolInfo{
		Name: "order_query",
		Desc: "Query order information by order ID or user ID. " +
			"Use this when the user asks about their order status, history, or specific order details.",
		ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
			"order_id": {
				Type: schema.String,
				Desc: "The order ID to look up",
			},
			"user_id": {
				Type: schema.String,
				Desc: "The user ID to look up orders for",
			},
		}),
	}, nil
}

func (o *OrderQueryTool) InvokableRun(ctx context.Context, argumentsInJSON string, opts ...tool.Option) (string, error) {
	var params struct {
		OrderID string `json:"order_id"`
		UserID  string `json:"user_id"`
	}
	if err := json.Unmarshal([]byte(argumentsInJSON), &params); err != nil {
		return "", err
	}
	if params.OrderID != "" {
		return `{"order_id":"` + params.OrderID + `","status":"shipped","amount":299.00,"date":"2025-12-01"}`, nil
	}
	if params.UserID != "" {
		return `{"orders":[{"order_id":"ORD-001","status":"delivered","amount":199.00},{"order_id":"ORD-002","status":"processing","amount":599.00}]}`, nil
	}
	return `{"message":"no query parameters provided"}`, nil
}

var _ tool.BaseTool = (*OrderQueryTool)(nil)
var _ tool.InvokableTool = (*OrderQueryTool)(nil)
