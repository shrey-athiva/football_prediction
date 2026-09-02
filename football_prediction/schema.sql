-- ============================================================
-- Football Score Prediction System — MySQL Schema
-- Run this once:   mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS football_prediction
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE football_prediction;

-- ------------------------------------------------------------
-- users: both regular predictors and admins live in one table,
-- distinguished by is_admin. Admin accounts are created via the
-- create_admin.py helper script, not through the public /register form.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(64)  NOT NULL UNIQUE,
  email         VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(256) NOT NULL,
  is_admin      TINYINT(1)   NOT NULL DEFAULT 0,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- matches: fixtures the admin posts for users to predict.
-- status moves from 'upcoming' -> 'completed' once the admin
-- enters the real result (predictions also close automatically
-- once kickoff_at has passed, checked in application code).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  home_team          VARCHAR(64) NOT NULL,
  away_team          VARCHAR(64) NOT NULL,
  kickoff_at         DATETIME    NOT NULL,
  status             ENUM('upcoming', 'completed') NOT NULL DEFAULT 'upcoming',
  actual_home_score  INT NULL,
  actual_away_score  INT NULL,
  created_by         INT NOT NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- predictions: one row per (user, match). points is NULL until
-- the admin submits the actual score, at which point the app
-- computes and fills it in (3 = exact score, 1 = correct
-- result/outcome, 0 = wrong).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
  id                     INT AUTO_INCREMENT PRIMARY KEY,
  user_id                INT NOT NULL,
  match_id               INT NOT NULL,
  predicted_home_score   INT NOT NULL,
  predicted_away_score   INT NOT NULL,
  points                 INT NULL,
  submitted_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                          ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_match (user_id, match_id),
  FOREIGN KEY (user_id)  REFERENCES users(id)   ON DELETE CASCADE,
  FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Helpful indexes for common lookups / the leaderboard join
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_predictions_user  ON predictions(user_id);
CREATE INDEX idx_matches_status    ON matches(status);
