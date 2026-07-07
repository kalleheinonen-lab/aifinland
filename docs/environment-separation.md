# Environment Separation

## Overview

Production, staging, and development environments run under separate UpCloud sub-accounts to provide strong isolation boundaries (ARC-UPCLOUD-4).

## Sub-Account Isolation

Each environment operates within its own UpCloud sub-account:

| Environment | Sub-Account Purpose | Zone |
|-------------|--------------------|---------|
| dev | Development and experimentation | fi-hel1 |
| stg | Pre-production validation | fi-hel1 |
| prod | Production workloads | fi-hel1 |

This ensures:

- Resource-level isolation (no accidental cross-environment access)
- Independent billing and quota tracking
- Separate API credential scopes
- Blast-radius containment for infrastructure changes

## Credential Separation

Each environment uses its own set of credentials:

- `UPCLOUD_USERNAME` / `UPCLOUD_PASSWORD` -- unique per sub-account
- Object Storage access keys -- unique per environment
- Terraform state backend -- separate state files per environment

Credentials are stored as environment-scoped GitHub Actions secrets. A CI/CD job targeting `prod` cannot access `dev` or `stg` credentials, and vice versa.

## Data Isolation

### Production Data Protection (SDLC-6.2)

Production data must not be used in development or staging environments. This includes:

- Database contents (user data, application state)
- Object storage files (uploaded documents, generated assets)
- Logs and audit trails containing production identifiers

When realistic test data is needed, use synthetic data generators or anonymized datasets.

### Secret Isolation (SDLC-6.4)

Environment-specific secrets are never shared across environments:

- API keys and tokens are issued per environment
- Encryption keys are unique per environment
- Service account credentials are scoped to a single sub-account
- Vault/OpenBao paths are namespaced by environment

## Terraform Configuration

Environment-specific settings are managed via tfvars files:

```
terraform/environments/
  dev.tfvars   -- development defaults (open access, minimal resources)
  stg.tfvars   -- staging (restricted access, dev-sized resources)
  prod.tfvars  -- production (restricted access, HA resources, termination protection)
```

Each environment is applied with:

```bash
terraform plan -var-file=environments/<env>.tfvars
```

## Compliance References

- **ARC-UPCLOUD-4**: Environments run under separate UpCloud sub-accounts
- **SDLC-6.2**: Production data must not be used in non-production environments
- **SDLC-6.4**: Environment-specific secrets never shared across environments
