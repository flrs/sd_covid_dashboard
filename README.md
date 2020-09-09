# sd_covid_dashboard
San Diego COVID-19 Dashboard on Kubernetes

## Pipeline Status

**Cloud Foundational Layer** 

![Deploy Infrastructure on GCP](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/flrs/78f880bf0781dd1ed6d5d676400d1ebe/raw/sha_infrastructure.json)

**Kubernetes Foundational Layer**

![Deploy Infrastructure on GKE](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/flrs/78f880bf0781dd1ed6d5d676400d1ebe/raw/sha_app.json)

**App Layer**

|  | Docker Build | Built Image | K8s Deployment |
|-|-|-|-|
| Crawler | ![Build Docker Crawler](https://github.com/flrs/sd_covid_dashboard/workflows/Build%20Docker%20Crawler/badge.svg) | [![Built Docker Crawler Image](https://images.microbadger.com/badges/version/flrs/sd_covid_dashboard_crawler.svg)](https://microbadger.com/images/flrs/sd_covid_dashboard_crawler "Get your own version badge on microbadger.com") | ![Deploy Infrastructure on GKE](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/flrs/78f880bf0781dd1ed6d5d676400d1ebe/raw/sha_crawler.json) |
| Dashboard | ![Build Docker Dashboard](https://github.com/flrs/sd_covid_dashboard/workflows/Build%20Docker%20Dashboard/badge.svg) | [![Built Docker Dashboard Image](https://images.microbadger.com/badges/version/flrs/sd_covid_dashboard_dashboard.svg)](https://microbadger.com/images/flrs/sd_covid_dashboard_dashboard "Get your own version badge on microbadger.com") | ![Deploy Infrastructure on GKE](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/flrs/78f880bf0781dd1ed6d5d676400d1ebe/raw/sha_dashboard.json) |
