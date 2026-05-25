package memory

import (
	"math"
	"strings"
	"sync"
)

type Document struct {
	ID      string
	Title   string
	Content string
	Tags    []string
}

type KnowledgeBase struct {
	mu        sync.RWMutex
	documents []Document
}

func NewKnowledgeBase() *KnowledgeBase {
	kb := &KnowledgeBase{documents: make([]Document, 0)}
	kb.seed()
	return kb
}

func (kb *KnowledgeBase) seed() {
	kb.documents = append(kb.documents,
		Document{
			ID:    "doc-1",
			Title: "Product FAQ - Financial Product A",
			Content: "Financial Product A offers annual returns between 3.5%% and 5.2%% APR. " +
				"The investment period ranges from 6 months to 3 years. " +
				"Minimum investment amount is 10,000 RMB. " +
				"Early withdrawal penalties may apply.",
			Tags: []string{"product", "financial", "investment"},
		},
		Document{
			ID:    "doc-2",
			Title: "Refund Policy",
			Content: "Our refund policy allows 7-day no-questions-asked returns. " +
				"Refunds are processed within 3-5 business days. " +
				"Late fees may apply for cancellations after the grace period.",
			Tags: []string{"refund", "policy"},
		},
		Document{
			ID:    "doc-3",
			Title: "Account Opening Procedure",
			Content: "Account opening requires: 1) valid ID document, " +
				"2) proof of address, 3) completed application form. " +
				"The process takes approximately 15-30 minutes. " +
				"In-person verification may be required for high-value accounts.",
			Tags: []string{"account", "procedure", "onboarding"},
		},
	)
}

func (kb *KnowledgeBase) Search(query string, limit int) []Document {
	kb.mu.RLock()
	defer kb.mu.RUnlock()
	if limit <= 0 {
		limit = 5
	}
	type scored struct {
		doc   Document
		score int
	}
	var results []scored
	query = strings.ToLower(query)
	terms := strings.Fields(query)
	for _, doc := range kb.documents {
		content := strings.ToLower(doc.Content)
		score := 0
		for _, term := range terms {
			if strings.Contains(content, term) {
				score++
			}
		}
		for _, tag := range doc.Tags {
			if strings.Contains(query, strings.ToLower(tag)) {
				score += 2
			}
		}
		if score > 0 {
			results = append(results, scored{doc: doc, score: score})
		}
	}
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			if results[j].score > results[i].score {
				results[i], results[j] = results[j], results[i]
			}
		}
	}
	if len(results) > limit {
		results = results[:limit]
	}
	out := make([]Document, len(results))
	for i, r := range results {
		out[i] = r.doc
	}
	return out
}

func (kb *KnowledgeBase) ChunkText(text string, chunkSize, overlap int) []string {
	if chunkSize <= 0 {
		chunkSize = 200
	}
	if overlap < 0 {
		overlap = 0
	}
	sentences := strings.FieldsFunc(text, func(r rune) bool {
		return r == '.' || r == '!' || r == '?' || r == '。' || r == '！' || r == '？'
	})
	var chunks []string
	current := strings.Builder{}
	count := 0
	for _, sentence := range sentences {
		sentence = strings.TrimSpace(sentence)
		if sentence == "" {
			continue
		}
		words := len(sentence)
		if count+words > chunkSize && count > 0 {
			chunks = append(chunks, current.String())
			current.Reset()
			count = 0
		}
		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(sentence)
		count += words
	}
	if current.Len() > 0 {
		chunks = append(chunks, current.String())
	}
	return chunks
}

func cosineSimilarity(a, b []float64) float64 {
	if len(a) != len(b) {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}
	if normA == 0 || normB == 0 {
		return 0
	}
	return dot / (math.Sqrt(normA) * math.Sqrt(normB))
}

func simpleEmbed(text string) []float64 {
	dim := 64
	vec := make([]float64, dim)
	for i, ch := range text {
		idx := i % dim
		vec[idx] += float64(ch) * float64(i+1)
	}
	var norm float64
	for _, v := range vec {
		norm += v * v
	}
	norm = math.Sqrt(norm)
	if norm > 0 {
		for i := range vec {
			vec[i] /= norm
		}
	}
	return vec
}
