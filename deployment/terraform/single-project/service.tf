# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


resource "google_cloud_run_v2_service" "app" {
  name                = var.project_name
  location            = var.region
  project             = var.project_id
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  labels = {
    "created-by"                  = "adk"
  }

  template {
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      resources {
        limits = {
          cpu    = "1"
          memory = "4Gi"
        }
      }

      env {
        name  = "LOGS_BUCKET_NAME"
        value = google_storage_bucket.logs_data_bucket.name
      }

      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "NO_CONTENT"
      }

      # --- Allow the local ADK Dev UI (reached via `gcloud run services proxy`)
      # to create sessions. ADK's origin-check middleware blocks cross-origin
      # POSTs (CSRF/DNS-rebinding defense); over the proxy the browser origin is
      # http://localhost:8080 while the service sees its run.app host, so the
      # session-create POST is refused (403 "origin not allowed") unless the
      # proxy origin is allowlisted here. Safe: the service is private (IAM-gated).
      env {
        name  = "ALLOW_ORIGINS"
        value = "http://localhost:8080,http://127.0.0.1:8080"
      }

      # --- Model auth on Cloud Run: use Vertex AI via the service account (ADC).
      # 'global' avoids model-not-found (404) errors for gemini-flash-latest.
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }

      # --- Receipt Vault local-first paths -> /tmp.
      # The Cloud Run container filesystem is READ-ONLY except /tmp, so the
      # ledger, vault, audit log, and inbox must live there or the first write
      # crashes the service. For durable storage, back the ledger with Cloud SQL
      # and the vault with a GCS bucket (see ARCHITECTURE.md § Deployment).
      env {
        name  = "RECEIPT_VAULT_DB"
        value = "/tmp/receipt_vault.db"
      }
      env {
        name  = "RECEIPT_VAULT_STORE"
        value = "/tmp/vault"
      }
      env {
        name  = "RECEIPT_VAULT_AUDIT"
        value = "/tmp/audit/audit.log"
      }
      env {
        name  = "RECEIPT_VAULT_INBOX"
        value = "/tmp/inbox"
      }
    }

    service_account = google_service_account.app_sa.email
    max_instance_request_concurrency = 8

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    session_affinity = true
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # This lifecycle block prevents Terraform from overwriting the container image when it's
  # updated by Cloud Run deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  # Make dependencies conditional to avoid errors.
  depends_on = [
    resource.google_project_service.services,
  ]
}
