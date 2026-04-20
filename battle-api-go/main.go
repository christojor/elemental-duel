package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
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

			if req.ComputerChoice == "" {
				req.ComputerChoice = "pending-ai"
			}

			round := Round{
				PlayerChoice:   req.PlayerChoice,
				ComputerChoice: req.ComputerChoice,
				Result:         "not-implemented",
			}

			if db != nil {
				if err := db.Create(&round).Error; err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to store round"})
					return
				}
			}

			c.JSON(http.StatusCreated, gin.H{
				"message": "Battle scaffold ready. Game logic will be added later.",
				"round":   round,
			})
		})

		api.GET("/stats", func(c *gin.Context) {
			var totalRounds int64
			if db != nil {
				_ = db.Model(&Round{}).Count(&totalRounds).Error
			}

			c.JSON(http.StatusOK, gin.H{
				"service":      "battle-api-go",
				"total_rounds": totalRounds,
				"win_rate":     0,
				"notes":        "Scaffold mode: no duel logic implemented yet.",
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
