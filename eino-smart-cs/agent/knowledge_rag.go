package agent

import (
	"context"
	"fmt"
	"strings"

	"eino-smart-cs/memory"
)

type ragAgent struct {
	llm *LLMClient
	kb  *memory.KnowledgeBase
}

func newRAGAgent(llm *LLMClient, kb *memory.KnowledgeBase) *ragAgent {
	return &ragAgent{llm: llm, kb: kb}
}

func (ra *ragAgent) process(ctx context.Context, state *AgentState) {
	query := ra.rewriteQuery(ctx, state.Message)
	results := ra.kb.Search(query, 5)
	if len(results) == 0 {
		state.SubResults["knowledge"] = "I don't have specific information about that in my knowledge base."
		return
	}

	var docs []memory.Document
	if ra.llm.IsAvailable() {
		docs = ra.rerank(ctx, results, query)
	} else {
		docs = results
		if len(docs) > 3 {
			docs = docs[:3]
		}
	}

	var snippets []string
	for _, doc := range docs {
		snippets = append(snippets, fmt.Sprintf("[%s] %s", doc.Title, doc.Content))
	}
	contextStr := strings.Join(snippets, "\n\n")

	answer := ra.generateAnswer(ctx, query, docs, contextStr)
	state.SubResults["knowledge"] = answer
}

func (ra *ragAgent) rerank(ctx context.Context, docs []memory.Document, query string) []memory.Document {
	if len(docs) <= 3 {
		return docs
	}

	systemPrompt := `You are a relevance scorer. Given a user query and a list of documents,
rank the documents by relevance and return the indices of the top 3 most relevant ones.
Return JSON format: {"indices": [0, 2, 3]}`

	var docStrs []string
	for i, doc := range docs {
		docStrs = append(docStrs, fmt.Sprintf("[%d] Title: %s\nContent: %s", i, doc.Title, doc.Content))
	}
	userPrompt := fmt.Sprintf("Query: %s\n\nDocuments:\n%s", query, strings.Join(docStrs, "\n---\n"))

	result, err := ra.llm.Generate(ctx, systemPrompt, userPrompt)
	if err != nil || result == "" {
		if len(docs) > 3 {
			return docs[:3]
		}
		return docs
	}

	var top []memory.Document
	for i := 0; i < len(docs); i++ {
		idxStr := fmt.Sprintf("%d", i)
		if strings.Contains(result, idxStr) {
			top = append(top, docs[i])
			if len(top) >= 3 {
				break
			}
		}
	}
	if len(top) == 0 {
		if len(docs) > 3 {
			return docs[:3]
		}
		return docs
	}
	return top
}

func (ra *ragAgent) generateAnswer(ctx context.Context, query string, docs []memory.Document, contextStr string) string {
	if !ra.llm.IsAvailable() {
		return buildFallbackAnswer(docs)
	}

	systemPrompt := `You are a knowledgeable customer service assistant. Answer the user's question
based on the provided context. If the context doesn't contain enough information, say so honestly.
Do not make up information. Cite the source document titles when possible.`

	userPrompt := fmt.Sprintf("Context:\n%s\n\nQuestion: %s", contextStr, query)

	result, err := ra.llm.Generate(ctx, systemPrompt, userPrompt)
	if err != nil || result == "" {
		return buildFallbackAnswer(docs)
	}
	return result
}

func buildFallbackAnswer(docs []memory.Document) string {
	parts := make([]string, len(docs))
	for i, doc := range docs {
		parts[i] = fmt.Sprintf("Based on '%s': %s", doc.Title, truncateText(doc.Content, 200))
	}
	return strings.Join(parts, "\n\n")
}

func truncateText(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) <= maxLen {
		return s
	}
	return string(runes[:maxLen]) + "..."
}

func (ra *ragAgent) rewriteQuery(ctx context.Context, original string) string {
	if !ra.llm.IsAvailable() {
		return original
	}
	systemPrompt := "Rewrite the following user query to be more search-friendly. Return only the rewritten query, nothing else."
	result, err := ra.llm.Generate(ctx, systemPrompt, original)
	if err != nil || result == "" {
		return original
	}
	result = strings.TrimSpace(result)
	if len(result) < 3 {
		return original
	}
	return result
}

