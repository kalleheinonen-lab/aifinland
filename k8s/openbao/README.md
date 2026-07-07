# OpenBao Bootstrap Procedure

This document describes the steps to initialize and configure the self-hosted
OpenBao instance running in the `ai-finland-secrets` namespace.

## Prerequisites

- UKS cluster is running and `kubectl` is configured
- Helm chart deployed: `helm install openbao openbao/openbao -n ai-finland-secrets -f values.yaml`
- The `ai-finland-app` namespace has the label `openbao-injection: enabled`

## 1. Initialize OpenBao

```bash
kubectl exec -n ai-finland-secrets openbao-0 -- bao operator init \
  -key-shares=5 \
  -key-threshold=3 \
  -format=json > init-keys.json
```

Store the unseal keys and root token securely (offline, split custody).
Never commit `init-keys.json` to source control.

## 2. Unseal OpenBao

Repeat with 3 of the 5 unseal keys:

```bash
kubectl exec -n ai-finland-secrets openbao-0 -- bao operator unseal <KEY_1>
kubectl exec -n ai-finland-secrets openbao-0 -- bao operator unseal <KEY_2>
kubectl exec -n ai-finland-secrets openbao-0 -- bao operator unseal <KEY_3>
```

## 3. Configure Kubernetes Auth Method

```bash
# Port-forward to access OpenBao API
kubectl port-forward -n ai-finland-secrets svc/openbao 8200:8200 &

export BAO_ADDR="http://127.0.0.1:8200"
export BAO_TOKEN="<root-token-from-init>"

# Enable Kubernetes auth
bao auth enable kubernetes

# Configure it to use the in-cluster service account
bao write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc"
```

## 4. Enable KV v2 Secrets Engine

```bash
bao secrets enable -path=secret kv-v2
```

## 5. Create Policies for Application Pods

### API Policy

```bash
bao policy write api - <<EOF
path "secret/data/ai-finland/db-creds" {
  capabilities = ["read"]
}
path "secret/data/ai-finland/api-secrets" {
  capabilities = ["read"]
}
path "secret/data/ai-finland/object-storage" {
  capabilities = ["read"]
}
EOF
```

### Worker Policy

```bash
bao policy write worker - <<EOF
path "secret/data/ai-finland/db-creds" {
  capabilities = ["read"]
}
path "secret/data/ai-finland/valkey-creds" {
  capabilities = ["read"]
}
path "secret/data/ai-finland/object-storage" {
  capabilities = ["read"]
}
EOF
```

### Scheduler Policy

```bash
bao policy write scheduler - <<EOF
path "secret/data/ai-finland/db-creds" {
  capabilities = ["read"]
}
path "secret/data/ai-finland/valkey-creds" {
  capabilities = ["read"]
}
EOF
```

## 6. Bind Policies to Kubernetes Service Accounts

Bind each policy to the corresponding service account in the
`ai-finland-app` namespace:

```bash
# API role -- binds to 'api' service account in ai-finland-app namespace
bao write auth/kubernetes/role/api \
  bound_service_account_names=api \
  bound_service_account_namespaces=ai-finland-app \
  policies=api \
  ttl=1h

# Worker role -- binds to 'worker' service account in ai-finland-app namespace
bao write auth/kubernetes/role/worker \
  bound_service_account_names=worker \
  bound_service_account_namespaces=ai-finland-app \
  policies=worker \
  ttl=1h

# Scheduler role -- binds to 'scheduler' service account in ai-finland-app namespace
bao write auth/kubernetes/role/scheduler \
  bound_service_account_names=scheduler \
  bound_service_account_namespaces=ai-finland-app \
  policies=scheduler \
  ttl=1h
```

## 7. Seed Initial Secrets

Populate secrets from Terraform outputs (run after `terraform apply`):

```bash
# Database credentials (from terraform output -json)
bao kv put secret/ai-finland/db-creds \
  username="$(terraform output -raw pg_service_username)" \
  password="$(terraform output -raw pg_service_password)"

# Object storage credentials
bao kv put secret/ai-finland/object-storage \
  access_key="$(terraform output -raw object_storage_access_key)" \
  secret_key="$(terraform output -raw object_storage_secret_key)"
```

## 8. Verify

```bash
# Check OpenBao status
bao status

# Verify Kubernetes auth is configured
bao read auth/kubernetes/config

# List policies
bao policy list

# Test a role binding
bao read auth/kubernetes/role/api
```

## Security Notes

- Root token must be revoked after initial setup: `bao token revoke <root-token>`
- Unseal keys must be stored in separate secure locations (split custody)
- Audit logging is enabled -- all access is recorded to `/openbao/audit/audit.log`
- UI is disabled in production for security
- The injector only processes pods in namespaces with the label `openbao-injection: enabled`
- All secrets are accessed via the KV v2 engine at path `secret/`
