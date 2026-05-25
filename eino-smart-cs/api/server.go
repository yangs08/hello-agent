package api

import (
	"fmt"
	"net/http"
	"sync"
	"time"

	"eino-smart-cs/agent"
	"eino-smart-cs/memory"
	"github.com/gin-gonic/gin"
)

type Server struct {
	supervisor    *agent.Supervisor
	workingMemory *memory.WorkingMemory
	llmClient     *agent.LLMClient
	config        *ServerConfig
	metrics       *MetricsCollector
	engine        *gin.Engine
}

type ServerConfig struct {
	Port string
}

type MetricsCollector struct {
	mu          sync.Mutex
	totalCalls  int
	totalTime   time.Duration
	agentCalls  map[string]int
	agentErrors map[string]int
}

func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		agentCalls:  make(map[string]int),
		agentErrors: make(map[string]int),
	}
}

func (m *MetricsCollector) Record(agentName string, duration time.Duration, err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.totalCalls++
	m.totalTime += duration
	m.agentCalls[agentName]++
	if err != nil {
		m.agentErrors[agentName]++
	}
}

func (m *MetricsCollector) Snapshot() map[string]any {
	m.mu.Lock()
	defer m.mu.Unlock()
	sn := map[string]any{
		"total_calls": m.totalCalls,
		"total_time":  m.totalTime.String(),
	}
	agents := make(map[string]any)
	for name, calls := range m.agentCalls {
		entry := map[string]any{"calls": calls}
		if errs := m.agentErrors[name]; errs > 0 {
			entry["errors"] = errs
		}
		agents[name] = entry
	}
	sn["agents"] = agents
	return sn
}

type ChatRequest struct {
	Message   string `json:"message" binding:"required"`
	UserID    string `json:"user_id"`
	SessionID string `json:"session_id"`
}

type ChatResponse struct {
	Success   bool   `json:"success"`
	Response  string `json:"response"`
	SessionID string `json:"session_id"`
	Intent    string `json:"intent,omitempty"`
}

type ErrorResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
}

func NewServer(supervisor *agent.Supervisor, wm *memory.WorkingMemory, llm *agent.LLMClient, cfg *ServerConfig) *Server {
	s := &Server{
		supervisor:    supervisor,
		workingMemory: wm,
		llmClient:     llm,
		config:        cfg,
		metrics:       NewMetricsCollector(),
		engine:        gin.Default(),
	}
	s.registerRoutes()
	return s
}

func (s *Server) registerRoutes() {
	s.engine.Use(corsMiddleware())
	api := s.engine.Group("/api")
	{
		api.POST("/chat", s.handleChat)
		api.GET("/history/:sessionId", s.handleHistory)
		api.GET("/tools", s.handleTools)
		api.GET("/metrics", s.handleMetrics)
	}
	s.engine.GET("/health", s.handleHealth)
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		c.Header("Access-Control-Max-Age", "86400")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	}
}

func (s *Server) handleChat(c *gin.Context) {
	var req ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Success: false, Error: "invalid request: " + err.Error()})
		return
	}

	userID := req.UserID
	if userID == "" {
		userID = "anonymous"
	}
	sessionID := req.SessionID
	if sessionID == "" {
		sessionID = fmt.Sprintf("sess-%d", time.Now().UnixNano())
	}

	history := s.workingMemory.GetContextWindow(sessionID, 2000)
	s.workingMemory.AddMessage(sessionID, "user", req.Message)

	state := agent.NewAgentState(userID, sessionID, req.Message, history)

	start := time.Now()
	s.supervisor.Process(c.Request.Context(), state)
	s.metrics.Record(state.Intent, time.Since(start), nil)

	s.workingMemory.AddMessage(sessionID, "assistant", state.FinalResponse)

	c.JSON(http.StatusOK, ChatResponse{
		Success:   true,
		Response:  state.FinalResponse,
		SessionID: sessionID,
		Intent:    state.Intent,
	})
}

func (s *Server) handleHistory(c *gin.Context) {
	sessionID := c.Param("sessionId")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{Success: false, Error: "sessionId is required"})
		return
	}
	history := s.workingMemory.GetHistory(sessionID)
	if history == nil {
		history = []memory.Message{}
	}
	c.JSON(http.StatusOK, gin.H{
		"success":   true,
		"sessionId": sessionID,
		"history":   history,
	})
}

func (s *Server) handleTools(c *gin.Context) {
	tools := []map[string]string{
		{"name": "knowledge_search", "description": "Search knowledge base"},
		{"name": "ticket_create", "description": "Create support ticket"},
		{"name": "order_query", "description": "Query order information"},
		{"name": "risk_check", "description": "Check compliance risk"},
	}
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"tools":   tools,
	})
}

func (s *Server) handleMetrics(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"metrics": s.metrics.Snapshot(),
	})
}

func (s *Server) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"version": "1.0.0",
		"llm":     s.llmClient.IsAvailable(),
	})
}

func (s *Server) Start() error {
	port := s.config.Port
	if port == "" {
		port = "8090"
	}
	return s.engine.Run(":" + port)
}
