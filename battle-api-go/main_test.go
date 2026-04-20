package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHealthEndpoint(t *testing.T) {
	router := setupRouter(nil)
	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	assert.Equal(t, http.StatusOK, response.Code)

	var payload map[string]any
	err := json.Unmarshal(response.Body.Bytes(), &payload)
	assert.NoError(t, err)
	assert.Equal(t, "ok", payload["status"])
	assert.Equal(t, "battle-api-go", payload["service"])
}
