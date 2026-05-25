package main

import (
	"log"

	"eino-smart-cs/agent"
	"eino-smart-cs/api"
	"eino-smart-cs/config"
	"eino-smart-cs/memory"
)

func main() {
	cfg := config.Load()

	if cfg.OpenAIAPIKey == "" {
		log.Println("WARNING: OPENAI_API_KEY not set. LLM features will be disabled.")
	}

	llm := agent.NewLLMClient(cfg.OpenAIAPIKey, cfg.OpenAIBaseURL, cfg.ModelName)
	wm := memory.NewWorkingMemory(20)
	kb := memory.NewKnowledgeBase()
	ticketStore := memory.NewTicketStore()
	supervisor := agent.NewSupervisor(llm, kb, ticketStore, wm)
	server := api.NewServer(supervisor, wm, llm, &api.ServerConfig{Port: cfg.Port})

	log.Printf("Eino Smart CS starting on port %s (model: %s, llm: %v)\n",
		cfg.Port, cfg.ModelName, llm.IsAvailable())

	if err := server.Start(); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
