package agent

import (
	"context"
	"strings"
)

type complianceAgent struct {
	llm *LLMClient
}

func newComplianceAgent(llm *LLMClient) *complianceAgent {
	return &complianceAgent{llm: llm}
}

func (ca *complianceAgent) process(ctx context.Context, state *AgentState) {
	riskLevel, reason := ca.ruleCheck(state.Message)

	if riskLevel != "low" {
		state.CompliancePassed = false
		state.ComplianceRisk = riskLevel
		prefix := "Compliance check failed"
		if riskLevel == "medium" {
			prefix = "Compliance check flagged"
		}
		state.SubResults["compliance"] = prefix + ": " + reason
		return
	}

	if ca.llm.IsAvailable() {
		llmRisk, llmReason := ca.llmCheck(ctx, state.Message)
		if llmRisk == "high" {
			state.CompliancePassed = false
			state.ComplianceRisk = llmRisk
			state.SubResults["compliance"] = "Compliance review flagged: " + llmReason
			return
		}
	}

	state.CompliancePassed = true
	state.ComplianceRisk = "low"
	state.SubResults["compliance"] = "Compliance check passed."
}

func (ca *complianceAgent) ruleCheck(content string) (string, string) {
	forbidden := map[string]string{
		"guaranteed return": "contains prohibited financial promise language",
		"zero risk":         "contains prohibited zero-risk claim",
		"no risk":           "contains prohibited no-risk claim",
		"guaranteed profit": "contains prohibited profit guarantee",
		"insider info":      "contains reference to insider information",
		"保本":                "contains guaranteed principal promise",
		"零风险":               "contains zero-risk promise",
		"保证收益":              "contains guaranteed return promise",
	}

	for phrase, reason := range forbidden {
		if strings.Contains(content, phrase) {
			return "high", reason
		}
	}

	if containsPII(content) {
		return "medium", "message contains personally identifiable information"
	}

	return "low", ""
}

func (ca *complianceAgent) llmCheck(ctx context.Context, content string) (string, string) {
	systemPrompt := `You are a compliance review assistant. Review the following message for:
1. Unauthorized financial promises or guarantees
2. Discriminatory or offensive content
3. Misleading or false claims
4. Regulatory compliance issues

Respond with JSON: {"risk": "low|high", "reason": "..."}`

	result, err := ca.llm.Generate(ctx, systemPrompt, content)
	if err != nil || result == "" {
		return "low", ""
	}

	if strings.Contains(result, `"risk":"high"`) || strings.Contains(result, `"risk": "high"`) {
		reason := extractField(result, "reason")
		if reason == "" {
			reason = "flagged by compliance review"
		}
		return "high", reason
	}
	return "low", ""
}

func extractField(json, field string) string {
	prefix := `"` + field + `":`
	start := strings.Index(json, prefix)
	if start < 0 {
		prefix = `"` + field + `" :`
		start = strings.Index(json, prefix)
	}
	if start < 0 {
		return ""
	}
	start += len(prefix)
	for start < len(json) && (json[start] == '"' || json[start] == ' ') {
		if json[start] == '"' {
			start++
			break
		}
		start++
	}
	end := strings.Index(json[start:], `"`)
	if end < 0 {
		return ""
	}
	return json[start : start+end]
}

func containsPII(content string) bool {
	hasPhone := false
	for i := 0; i <= len(content)-11; i++ {
		if content[i] == '1' && i+11 <= len(content) {
			if content[i+1] >= '3' && content[i+1] <= '9' {
				isDigit := true
				for j := i; j < i+11; j++ {
					if content[j] < '0' || content[j] > '9' {
						isDigit = false
						break
					}
				}
				if isDigit {
					hasPhone = true
					break
				}
			}
		}
	}

	hasID := false
	for i := 0; i <= len(content)-18; i++ {
		isDigit := true
		for j := i; j < i+17; j++ {
			if content[j] < '0' || content[j] > '9' {
				isDigit = false
				break
			}
		}
		if isDigit {
			last := content[i+17]
			if last >= '0' && last <= '9' || last == 'X' || last == 'x' {
				hasID = true
				break
			}
		}
	}

	return hasPhone || hasID
}
