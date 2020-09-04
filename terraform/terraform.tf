terraform {
  required_version = "~> 0.12"
  backend "remote" {
    organization = "flrs-test"

    workspaces {
      name = "flrs-test-workspace"
    }
  }
}
