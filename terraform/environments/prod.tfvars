environment             = "prod"
project_name            = "ai-finland"
control_plane_ip_filter = ["10.0.0.0/8"]
pg_plan                 = "2x2xCPU-4GB-50GB"
valkey_plan             = "2x2xCPU-4GB"
worker_node_count       = 3
