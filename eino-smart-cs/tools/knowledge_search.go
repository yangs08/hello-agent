package tools

import (
	"context"
	"encoding/json"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/schema"
)

type KnowledgeSearchTool struct {
	searchFunc func(ctx context.Context, query string, limit int) string
}

func NewKnowledgeSearchTool(searchFunc func(ctx context.Context, query string, limit int) string) *KnowledgeSearchTool {
	return &KnowledgeSearchTool{searchFunc: searchFunc}
}

func (k *KnowledgeSearchTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
	return &schema.ToolInfo{
		Name: "knowledge_search",
		Desc: "Search the knowledge base for relevant document snippets. " +
			"Use this when the user asks a question that may be answered by documentation, FAQ, or policy.",
		ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
			"query": {
				Type:     schema.String,
				Desc:     "The search query string",
				Required: true,
			},
			"limit": {
				Type: schema.Integer,
				Desc: "Maximum number of results to return (default 5)",
			},
		}),
	}, nil
}

func (k *KnowledgeSearchTool) InvokableRun(ctx context.Context, argumentsInJSON string, opts ...tool.Option) (string, error) {
	var params struct {
		Query string `json:"query"`
		Limit int    `json:"limit"`
	}
	if err := json.Unmarshal([]byte(argumentsInJSON), &params); err != nil {
		return "", err
	}
	if params.Limit <= 0 {
		params.Limit = 5
	}
	return k.searchFunc(ctx, params.Query, params.Limit), nil
}

var _ tool.BaseTool = (*KnowledgeSearchTool)(nil)
var _ tool.InvokableTool = (*KnowledgeSearchTool)(nil)
