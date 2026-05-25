package tools

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
)

type RiskCheckTool struct{}

func NewRiskCheckTool() *RiskCheckTool {
	return &RiskCheckTool{}
}

func (r *RiskCheckTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
	return &schema.ToolInfo{
		Name: "risk_check",
		Desc: "Check the risk level of a transaction or action. " +
			"Use this when compliance verification is needed or when assessing the risk of a user action.",
		ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
			"content": {
				Type:     schema.String,
				Desc:     "The content or action description to evaluate for risk",
				Required: true,
			},
		}),
	}, nil
}

func (r *RiskCheckTool) InvokableRun(ctx context.Context, argumentsInJSON string, opts ...tool.Option) (string, error) {
	var params struct {
		Content string `json:"content"`
	}
	if err := json.Unmarshal([]byte(argumentsInJSON), &params); err != nil {
		return "", err
	}
	forbiddenFinancial := []string{"guaranteed return", "zero risk", "no risk", "guaranteed profit", "insider info"}
	for _, phrase := range forbiddenFinancial {
		if strings.Contains(params.Content, phrase) {
			return `{"risk":"high","reason":"contains prohibited financial language: ` + phrase + `"}`, nil
		}
	}
	return `{"risk":"low","reason":"no risk indicators detected"}`, nil
}

var _ tool.BaseTool = (*RiskCheckTool)(nil)
var _ tool.InvokableTool = (*RiskCheckTool)(nil)
