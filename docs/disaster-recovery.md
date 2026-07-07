# Disaster Recovery Plan

## Recovery Objectives

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | < 4 hours |
| RPO (Recovery Point Objective) | < 1 hour |

## DR Zone

Primary zone: `fi-hel1`
DR target zone: `de-fra1`

## Service Recovery Procedures

### PostgreSQL (Managed)

**Backup strategy:**

- UpCloud managed Point-in-Time Recovery (PITR)
- Daily automated backups
- 30-day retention period
- Backups are provider-managed and stored in the same region

**Recovery procedure:**

1. Create a new managed PostgreSQL instance from the latest backup or PITR target timestamp.
2. Update Terraform state to reference the new instance (`terraform state rm` old, `terraform import` new).
3. Verify data integrity and connectivity from the application network.
4. Redeploy application services pointing to the new instance.

### Valkey (Managed)

**Backup strategy:**

- Provider-managed backup
- 7-day retention period

**Recovery procedure:**

1. Recreate the Valkey instance from the most recent backup.
2. Update Terraform state to reference the new instance.
3. Redeploy application services -- Valkey data is ephemeral/cacheable so partial data loss is acceptable.

### Object Storage (Managed)

**Backup strategy:**

- Versioning enabled on all buckets
- Lifecycle policies manage version retention

**Recovery procedure:**

1. Identify the affected objects and target restore timestamp.
2. Restore objects from the appropriate version using S3-compatible API calls.
3. Verify object integrity.

### UKS Kubernetes Cluster

**Backup strategy:**

- Pods are stateless -- all state lives in managed databases and object storage.
- Cluster configuration is fully defined in Terraform.
- Application manifests are deployed from CI/CD (source of truth is Git).

**Recovery procedure:**

1. Run `terraform apply` targeting the DR zone (`de-fra1`) to provision a new cluster.
2. CI/CD pipeline redeploys all workloads from the Git repository.
3. Verify pod health and service connectivity.

## Full DR Failover

A complete failover to the DR zone (`de-fra1`) requires the following steps:

1. **New Terraform workspace**: Create a new workspace targeting `de-fra1` with zone variable override.
2. **Infrastructure provisioning**: Run `terraform apply` to create all resources in the DR zone.
3. **Database restore**: Restore PostgreSQL from cross-zone backup into the new managed instance.
4. **DNS update**: Update DNS records to point to the new Load Balancer in `de-fra1`.
5. **Application deployment**: CI/CD redeploys all services to the new UKS cluster.
6. **Verification**: Run health checks against the new environment.

## Testing

- DR procedures are tested quarterly.
- Runbook is reviewed after each test and updated as needed.
- Recovery time is measured against RTO/RPO targets.
