package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	OpenAIAPIKey  string
	OpenAIBaseURL string
	ModelName     string
	Port          string
}

func Load() *Config {
	// .env is optional; if missing, rely on environment variables
	_ = godotenv.Load()

	apiKey := os.Getenv("OPENAI_API_KEY")
	baseURL := os.Getenv("OPENAI_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.openai.com/v1"
	}
	model := os.Getenv("MODEL_NAME")
	if model == "" {
		model = "gpt-4o"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8090"
	}
	return &Config{
		OpenAIAPIKey:  apiKey,
		OpenAIBaseURL: baseURL,
		ModelName:     model,
		Port:          port,
	}
}
