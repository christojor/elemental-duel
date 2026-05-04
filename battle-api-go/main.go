package main

import (
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

type Round struct {
	ID             uint      `json:"id" gorm:"primaryKey"`
	PlayerChoice   string    `json:"player_choice"`
	ComputerChoice string    `json:"computer_choice"`
	Result         string    `json:"result"`
	CreatedAt      time.Time `json:"created_at"`
}

type RoundRequest struct {
	PlayerChoice   string `json:"player_choice" binding:"required"`
	ComputerChoice string `json:"computer_choice"`
}

type AppConfig struct {
	Port       string
	DBUser     string
	DBPassword string
	DBHost     string
	DBPort     string
	DBName     string
	RetryCount int
}

var validChoices = map[string]bool{
	"fire":      true,
	"water":     true,
	"earth":     true,
	"air":       true,
	"lightning": true,
}

var beats = map[string]map[string]bool{
	"fire": {
		"air":   true,
		"earth": true,
	},
	"water": {
		"fire":      true,
		"lightning": true,
	},
	"earth": {
		"water":     true,
		"lightning": true,
	},
	"air": {
		"water": true,
		"earth": true,
	},
	"lightning": {
		"fire": true,
		"air":  true,
	},
}

var rng = rand.New(rand.NewSource(time.Now().UnixNano()))
var rngMu sync.Mutex

func normalizeChoice(value string) string {
	return strings.ToLower(strings.TrimSpace(value))
}

func randomChoice() string {
	choices := []string{"fire", "water", "earth", "air", "lightning"}
	rngMu.Lock()
	defer rngMu.Unlock()
	return choices[rng.Intn(len(choices))]
}

func determineResult(playerChoice string, computerChoice string) (string, error) {
	player := normalizeChoice(playerChoice)
	computer := normalizeChoice(computerChoice)

	if !validChoices[player] {
		return "", fmt.Errorf("invalid player_choice: %s", playerChoice)
	}

	if !validChoices[computer] {
		return "", fmt.Errorf("invalid computer_choice: %s", computerChoice)
	}

	if player == computer {
		return "draw", nil
	}

	if beats[player][computer] {
		return "win", nil
	}

	return "lose", nil
}

func getEnv(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func loadConfig() AppConfig {
	retryCount, err := strconv.Atoi(getEnv("DB_RETRY_COUNT", "10"))
	if err != nil {
		retryCount = 10
	}

	return AppConfig{
		Port:       getEnv("PORT", "8080"),
		DBUser:     getEnv("MYSQL_USER", "elemental"),
		DBPassword: getEnv("MYSQL_PASSWORD", "elementalpass"),
		DBHost:     getEnv("MYSQL_HOST", "mysql"),
		DBPort:     getEnv("MYSQL_PORT", "3306"),
		DBName:     getEnv("MYSQL_DATABASE", "elemental_duel"),
		RetryCount: retryCount,
	}
}

func connectDB(cfg AppConfig) *gorm.DB {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?charset=utf8mb4&parseTime=True&loc=Local", cfg.DBUser, cfg.DBPassword, cfg.DBHost, cfg.DBPort, cfg.DBName)

	for attempt := 1; attempt <= cfg.RetryCount; attempt++ {
		db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
		if err == nil {
			if migrateErr := db.AutoMigrate(&Round{}); migrateErr != nil {
				log.Printf("database migration warning: %v", migrateErr)
			}
			return db
		}

		log.Printf("database connection attempt %d/%d failed: %v", attempt, cfg.RetryCount, err)
		time.Sleep(3 * time.Second)
	}

	log.Println("starting without database connection; persistence is temporarily disabled")
	return nil
}

func setupRouter(db *gorm.DB) *gin.Engine {
	router := gin.Default()
	router.Use(cors.Default())

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":   "ok",
			"service":  "battle-api-go",
			"database": db != nil,
		})
	})

	api := router.Group("/api/v1")
	{
		api.GET("/rounds", func(c *gin.Context) {
			if db == nil {
				c.JSON(http.StatusOK, gin.H{"items": []Round{}, "message": "database unavailable"})
				return
			}

			var rounds []Round
			if err := db.Order("id desc").Find(&rounds).Error; err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query rounds"})
				return
			}

			c.JSON(http.StatusOK, gin.H{"items": rounds})
		})

		api.POST("/rounds", func(c *gin.Context) {
			var req RoundRequest
			if err := c.ShouldBindJSON(&req); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}

			req.PlayerChoice = normalizeChoice(req.PlayerChoice)
			if !validChoices[req.PlayerChoice] {
				c.JSON(http.StatusBadRequest, gin.H{"error": "player_choice must be one of: fire, water, earth, air, lightning"})
				return
			}

			req.ComputerChoice = normalizeChoice(req.ComputerChoice)
			if req.ComputerChoice == "" {
				req.ComputerChoice = randomChoice()
			}

			result, err := determineResult(req.PlayerChoice, req.ComputerChoice)
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "computer_choice must be one of: fire, water, earth, air, lightning"})
				return
			}

			round := Round{
				PlayerChoice:   req.PlayerChoice,
				ComputerChoice: req.ComputerChoice,
				Result:         result,
			}

			if db != nil {
				if err := db.Create(&round).Error; err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to store round"})
					return
				}
			}

			c.JSON(http.StatusCreated, gin.H{
				"message": "Round resolved successfully.",
				"round":   round,
			})
		})

		api.GET("/stats", func(c *gin.Context) {
			var totalRounds int64
			var totalWins int64
			var totalLosses int64
			var totalDraws int64
			if db != nil {
				_ = db.Model(&Round{}).Count(&totalRounds).Error
				_ = db.Model(&Round{}).Where("result = ?", "win").Count(&totalWins).Error
				_ = db.Model(&Round{}).Where("result = ?", "lose").Count(&totalLosses).Error
				_ = db.Model(&Round{}).Where("result = ?", "draw").Count(&totalDraws).Error
			}

			winRate := 0.0
			if totalRounds > 0 {
				winRate = float64(totalWins) / float64(totalRounds) * 100
			}

			c.JSON(http.StatusOK, gin.H{
				"service":      "battle-api-go",
				"total_rounds": totalRounds,
				"wins":         totalWins,
				"losses":       totalLosses,
				"draws":        totalDraws,
				"win_rate":     winRate,
			})
		})
	}

	return router
}

func main() {
	if getEnv("GIN_MODE", "") == "" {
		gin.SetMode(gin.ReleaseMode)
	}

	cfg := loadConfig()
	db := connectDB(cfg)
	router := setupRouter(db)

	log.Printf("battle api listening on port %s", cfg.Port)
	if err := router.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
