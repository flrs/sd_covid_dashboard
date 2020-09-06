resource "google_compute_global_address" "private_ip_address" {
  provider = google-beta

  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.gke-network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  provider = google-beta

  network                 = google_compute_network.gke-network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "sd-covid-dashboard-postgres" {
  name  = "sd-covid-dashboard-db-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_12"
  project = var.project
  region = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        value = google_compute_address.static-ingress.address
      }
      private_network = google_compute_network.gke-network.id
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

