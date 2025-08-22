terraform {
  required_version = ">= 1.6"
  required_providers { azurerm = { source = "hashicorp/azurerm", version = "~> 3.115" } }
}
provider "azurerm" { features {} }

resource "azurerm_resource_group" "rg" {
  name     = var.rg_name
  location = var.location
}

resource "azurerm_storage_account" "sa" {
  name                     = var.storage_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "ZRS"
}

resource "azurerm_redis_cache" "redis" {
  name                = var.redis_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = 1
  family              = "C"
  sku_name            = "Basic"
}

# PostgreSQL Flexible Server + DB
resource "azurerm_postgresql_flexible_server" "pg" {
  name                = var.pg_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  administrator_login = var.pg_admin
  administrator_password = var.pg_password
  version             = "16"
  storage_mb          = 32768
  sku_name            = "B_Standard_B2ms"
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "grc"
  server_id = azurerm_postgresql_flexible_server.pg.id
  collation = "en_US.utf8"
  charset   = "utf8"
}
