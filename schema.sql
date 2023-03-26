-- MySQL dump 10.13  Distrib 8.0.32, for Linux (x86_64)
--
-- Host: localhost    Database: google_mail
-- ------------------------------------------------------
-- Server version	8.0.32-0ubuntu0.20.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `email`
--

DROP TABLE IF EXISTS `email`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `email` (
  `id` bigint unsigned NOT NULL,
  `thread_id` bigint unsigned NOT NULL,
  `refreshed_on` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `email_attributes`
--

DROP TABLE IF EXISTS `email_attributes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `email_attributes` (
  `message_id` bigint unsigned NOT NULL,
  `history_id` bigint unsigned DEFAULT NULL,
  `internal_timestamp` timestamp NOT NULL,
  `from` varchar(100) NOT NULL,
  `to` varchar(5000) NOT NULL,
  `subject` text NOT NULL,
  `cc` varchar(5000) DEFAULT NULL,
  `bcc` varchar(5000) DEFAULT NULL,
  `size_estimate` int NOT NULL,
  `payload_headers` json DEFAULT NULL,
  `refreshed_on` datetime NOT NULL,
  PRIMARY KEY (`message_id`),
  KEY `idx_email_timestamp` (`internal_timestamp`),
  KEY `idx_ea_from` (`from`),
  KEY `idx_ea_to` (`to`(100)),
  KEY `idx_ea_subject` (`subject`(200)),
  CONSTRAINT `fk_ea_lbl_email_id` FOREIGN KEY (`message_id`) REFERENCES `email` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `label`
--

DROP TABLE IF EXISTS `label`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `label` (
  `id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `type` enum('system','user') NOT NULL,
  `refreshed_on` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_label_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `message_label`
--

DROP TABLE IF EXISTS `message_label`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `message_label` (
  `message_id` bigint unsigned NOT NULL,
  `labels` json NOT NULL,
  `refreshed_on` datetime NOT NULL,
  PRIMARY KEY (`message_id`),
  CONSTRAINT `fk_ml_lbl_email_id` FOREIGN KEY (`message_id`) REFERENCES `email` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `message_part`
--

DROP TABLE IF EXISTS `message_part`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `message_part` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `message_id` bigint unsigned NOT NULL,
  `part_id` varchar(20) NOT NULL,
  `parent_id` varchar(20) DEFAULT NULL,
  `content` text NOT NULL,
  `mime_type` varchar(50) DEFAULT NULL,
  `filename` varchar(100) DEFAULT NULL,
  `refreshed_on` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_message_part` (`message_id`,`part_id`),
  KEY `idx_part_id` (`part_id`),
  KEY `idx_mp_message_id` (`message_id`),
  KEY `idx_mp_search_content` (`message_id`,`content`(500)),
  KEY `fk_part_parent_id` (`parent_id`),
  CONSTRAINT `fk_part_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `message_part` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-03-26 19:55:12
