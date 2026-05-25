package agent

import (
	"context"
	"strings"

	openai "github.com/cloudwego/eino-ext/libs/acl/openai"
	"github.com/cloudwego/eino/schema"
)

type LLMClient struct {
	chatModel *openai.Client
}

func NewLLMClient(apiKey, baseURL, model string) *LLMClient {
	t := float32(0.7)
	cfg := &openai.Config{
		APIKey:      apiKey,
		BaseURL:     baseURL,
		Model:       model,
		Temperature: &t,
	}
	cm, err := openai.NewClient(context.Background(), cfg)
	if err != nil {
		return &LLMClient{chatModel: nil}
	}
	return &LLMClient{chatModel: cm}
}

func (l *LLMClient) Generate(ctx context.Context, system, user string) (string, error) {
	if l.chatModel == nil {
		return "", nil
	}
	msgs := []*schema.Message{
		{Role: schema.System, Content: system},
		{Role: schema.User, Content: user},
	}
	result, err := l.chatModel.Generate(ctx, msgs)
	if err != nil {
		return "", err
	}
	if result != nil && len(result.Content) > 0 {
		return result.Content, nil
	}
	return "", nil
}

func (l *LLMClient) GenerateWithMessages(ctx context.Context, msgs []*schema.Message) (string, error) {
	if l.chatModel == nil {
		return "", nil
	}
	result, err := l.chatModel.Generate(ctx, msgs)
	if err != nil {
		return "", err
	}
	if result != nil && len(result.Content) > 0 {
		return result.Content, nil
	}
	return "", nil
}

func (l *LLMClient) IsAvailable() bool {
	return l.chatModel != nil
}

type intentRouter struct {
	llm *LLMClient
}

func newIntentRouter(llm *LLMClient) *intentRouter {
	return &intentRouter{llm: llm}
}

func (ir *intentRouter) classify(ctx context.Context, state *AgentState) {
	systemPrompt := `You are an intent classifier for a customer service system.
Classify the user's message into one of the following intents:
- "knowledge_rag": The user is asking a question seeking information, knowledge, or explanation about products, policies, or procedures.
- "ticket": The user is reporting a problem, making a complaint, requesting support, or asking to create a ticket.
- "compliance": The user's request involves compliance, risk assessment, or regulatory matters.
- "chat": General conversation, greetings, or messages that don't fit the above categories.

Respond with a JSON object: {"intent": "...", "confidence": 0.0}`

	if ir.llm.IsAvailable() {
		result, err := ir.llm.Generate(ctx, systemPrompt, state.Message)
		if err == nil && result != "" {
			state.Intent = extractIntent(result)
			state.IntentConfidence = 0.8
			if state.Intent == "" {
				state.Intent = fallbackIntent(state.Message)
			}
			return
		}
	}
	state.Intent = fallbackIntent(state.Message)
	state.IntentConfidence = 0.5
}

func extractIntent(jsonResp string) string {
	for _, prefix := range []string{`"intent":"`, `"intent": "`} {
		start := strings.Index(jsonResp, prefix)
		if start < 0 {
			continue
		}
		start += len(prefix)
		end := strings.Index(jsonResp[start:], `"`)
		if end < 0 {
			continue
		}
		intent := jsonResp[start : start+end]
		switch intent {
		case "knowledge_rag", "ticket", "compliance", "chat":
			return intent
		}
	}
	return ""
}

func fallbackIntent(msg string) string {
	msgLower := strings.ToLower(msg)
	knowledgeKeywords := []string{"what", "how", "why", "when", "where", "tell me", "explain",
		"什么是", "怎么", "为什么", "如何", "说明", "解释"}
	ticketKeywords := []string{"problem", "issue", "broken", "error", "not working", "help", "fix", "complaint",
		"问题", "坏了", "错误", "不能用", "帮忙", "投诉"}
	complianceKeywords := []string{"compliance", "risk", "regulatory", "legal", "audit", "secure",
		"合规", "风险", "监管", "法规", "安全"}

	knowledgeScore := countKeywordHits(msgLower, knowledgeKeywords)
	ticketScore := countKeywordHits(msgLower, ticketKeywords)
	complianceScore := countKeywordHits(msgLower, complianceKeywords)

	if complianceScore >= ticketScore && complianceScore >= knowledgeScore && complianceScore > 0 {
		return "compliance"
	}
	if ticketScore >= knowledgeScore && ticketScore > 0 {
		return "ticket"
	}
	if knowledgeScore > 0 {
		return "knowledge_rag"
	}
	return "knowledge_rag"
}

func countKeywordHits(msg string, keywords []string) int {
	count := 0
	for _, kw := range keywords {
		if strings.Contains(msg, kw) {
			count++
		}
	}
	return count
}
