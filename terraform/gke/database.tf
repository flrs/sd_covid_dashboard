resource "google_sql_database_instance" "sd-covid-dashboard-postgres" {
  name  = "sd-covid-dashboard-postgres"
  database_version = "POSTGRES_12"
  project = var.project
  region = var.region

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        value = google_compute_address.static-ingress.address
      }
    }
    disk_size = 10
    disk_type = "PD_HDD"
    disk_autoresize = false
    backup_configuration {
      enabled = false
    }
    location_preference {
      zone = var.location
    }
  }
}

resource "google_sql_user" "users" {
  project  = var.project
  name     = var.db_user
  instance = google_sql_database_instance.sd-covid-dashboard-postgres.name
  password = var.db_password
}

output "db_host" {
  value = google_sql_database_instance.sd-covid-dashboard-postgres.ip_address[0].ip_address
}

