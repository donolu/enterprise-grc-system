variable "rg_name" {
  type        = string
  description = "Azure Resource Group name"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "storage_name" {
  type        = string
  description = "Azure Storage Account name"
}

variable "redis_name" {
  type        = string
  description = "Azure Cache for Redis name"
}

variable "pg_name" {
  type        = string
  description = "Azure PostgreSQL server name"
}

variable "pg_admin" {
  type        = string
  description = "PostgreSQL admin username"
}

variable "pg_password" {
  type      = string
  sensitive = true
  description = "PostgreSQL admin password"
}
