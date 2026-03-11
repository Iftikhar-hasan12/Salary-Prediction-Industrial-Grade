-- ============================================================
--  SalaryAI — MySQL Database Setup
--  Run this in phpMyAdmin (XAMPP) or MySQL CLI
--  © 2026 SalaryAI
-- ============================================================

-- 1. Create the database
CREATE DATABASE IF NOT EXISTS salaryai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 2. Select it
USE salaryai;

-- 3. Create predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id               INT           NOT NULL AUTO_INCREMENT,
    predicted_salary DECIMAL(12,2) NOT NULL,
    years_experience DECIMAL(5,1)  NOT NULL,
    age              TINYINT       NOT NULL,
    education_level  VARCHAR(50)   NOT NULL,
    job_role         VARCHAR(100)  NOT NULL,
    location         VARCHAR(50)   NOT NULL,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_job_role   (job_role),
    INDEX idx_location   (location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Verify
SELECT 'Database and table created successfully ✅' AS status;
DESCRIBE predictions;
