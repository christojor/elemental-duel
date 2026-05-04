package main

import (
	"bytes"
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

func TestDetermineResult(t *testing.T) {
	result, err := determineResult("fire", "air")
	assert.NoError(t, err)
	assert.Equal(t, "win", result)

	result, err = determineResult("fire", "water")
	assert.NoError(t, err)
	assert.Equal(t, "lose", result)

	result, err = determineResult("lightning", "lightning")
	assert.NoError(t, err)
	assert.Equal(t, "draw", result)
}

func TestDetermineResultRejectsInvalidChoice(t *testing.T) {
	_, err := determineResult("invalid", "fire")
	assert.Error(t, err)
}

func TestCreateRoundEndpoint(t *testing.T) {
	router := setupRouter(nil)
	body := bytes.NewBufferString(`{"player_choice":"Fire","computer_choice":"Earth"}`)
	request := httptest.NewRequest(http.MethodPost, "/api/v1/rounds", body)
	request.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	assert.Equal(t, http.StatusCreated, response.Code)

	var payload map[string]any
	err := json.Unmarshal(response.Body.Bytes(), &payload)
	assert.NoError(t, err)
	assert.Equal(t, "Round resolved successfully.", payload["message"])

	round := payload["round"].(map[string]any)
	assert.Equal(t, "fire", round["player_choice"])
	assert.Equal(t, "earth", round["computer_choice"])
	assert.Equal(t, "win", round["result"])
}
