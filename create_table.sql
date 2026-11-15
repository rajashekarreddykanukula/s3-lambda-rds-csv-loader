CREATE DATABASE IF NOT EXISTS world_data;
USE world_data;

CREATE TABLE country_indicators (
    country_code CHAR(3) PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL,
    birth_rate DECIMAL(10,5),
    internet_users DECIMAL(10,5),
    income_group VARCHAR(50)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
