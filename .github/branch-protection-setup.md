# Branch Protection Setup Guide

This document provides instructions for setting up branch protection rules for the GRC Platform repository.

## Required Branch Protection Rules

### Main Branch Protection

Navigate to your repository **Settings** → **Branches** and add the following protection rule for the `main` branch:

#### General Settings
- **Branch name pattern:** `main`
- **Restrict pushes that create files larger than:** `100` MB

#### Protect matching branches
- ✅ **Require a pull request before merging**
  - ✅ **Require approvals:** `2`
  - ✅ **Dismiss stale reviews when new commits are pushed**
  - ✅ **Require review from code owners**
  - ✅ **Restrict reviews to users with write access**
  - ✅ **Allow specified actors to bypass required pull requests:** (Leave empty for maximum security)

- ✅ **Require status checks to pass before merging**
  - ✅ **Require branches to be up to date before merging**
  - **Required status checks:**
    - `Backend Tests`
    - `Frontend Tests`
    - `Security Scanning / Code Security Analysis`
    - `Security Scanning / Dependency Security Check`
    - `Security Scanning / Secrets Detection`
    - `Build Test / Test Docker Build`

- ✅ **Require conversation resolution before merging**

- ✅ **Require signed commits**

- ✅ **Require linear history**

- ✅ **Require deployments to succeed before merging**
  - Required deployment environments: `staging`

#### Restrictions
- ✅ **Restrict pushes that create files larger than 100 MB**
- ✅ **Lock branch** (optional - only for extra security)

#### Rules applied to everyone including administrators
- ✅ **Include administrators**
- ✅ **Allow force pushes:** ❌ (Never enable)
- ✅ **Allow deletions:** ❌ (Never enable)

### Develop Branch Protection (Optional)

If using a develop branch for integration:

- **Branch name pattern:** `develop`
- ✅ **Require a pull request before merging**
  - ✅ **Require approvals:** `1`
  - ✅ **Dismiss stale reviews when new commits are pushed**
- ✅ **Require status checks to pass before merging**
  - Required status checks:
    - `Backend Tests`
    - `Frontend Tests`
    - `Security Scanning / Code Security Analysis`

## Repository Settings

### General Security Settings
Go to **Settings** → **Security & analysis**:

- ✅ **Dependency graph**
- ✅ **Dependabot alerts**
- ✅ **Dependabot security updates**
- ✅ **Code scanning alerts**
- ✅ **Secret scanning alerts**
- ✅ **Push protection for secret scanning**

### Actions Settings
Go to **Settings** → **Actions** → **General**:

- **Actions permissions:** `Allow enterprise, and select non-enterprise, actions and reusable workflows`
- **Artifact and log retention:** `90` days
- **Fork pull request workflows:** `Require approval for first-time contributors`
- ✅ **Prevent GitHub Actions from creating or approving pull requests**

### Pages Settings (if using GitHub Pages)
Go to **Settings** → **Pages**:

- **Source:** `GitHub Actions` (for static documentation)
- **Custom domain:** (if applicable)
- ✅ **Enforce HTTPS**

## Environment Protection Rules

### Staging Environment
Go to **Settings** → **Environments** → Create `staging` environment:

- **Deployment branches:** `Selected branches` → Add `main`
- **Environment secrets:** Add staging-specific secrets
- **Protection rules:**
  - ✅ **Required reviewers:** (Optional - 1 reviewer)
  - ✅ **Wait timer:** `0` minutes
  - ✅ **Prevent secrets from being accessed by:** (Leave unchecked)

### Production Environment
Create `production` environment:

- **Deployment branches:** `Selected branches` → Add `main`
- **Environment secrets:** Add production-specific secrets
- **Protection rules:**
  - ✅ **Required reviewers:** `2` reviewers (different from code reviewers)
  - ✅ **Wait timer:** `30` minutes (cooling-off period)
  - ✅ **Prevent secrets from being accessed by:** (Leave unchecked)

## Required Secrets

### Repository Secrets
Add these in **Settings** → **Secrets and variables** → **Actions**:

```
# Azure Staging
AZURE_CREDENTIALS_STAGING
AZURE_RESOURCE_GROUP_STAGING  
AZURE_WEBAPP_NAME_STAGING

# Azure Production
AZURE_CREDENTIALS_PRODUCTION
AZURE_RESOURCE_GROUP_PRODUCTION
AZURE_WEBAPP_NAME_PRODUCTION
AZURE_SQL_SERVER_PRODUCTION
AZURE_SQL_DATABASE_PRODUCTION
AZURE_SQL_ADMIN_USER
AZURE_SQL_ADMIN_PASSWORD
AZURE_STORAGE_ACCOUNT
AZURE_STORAGE_KEY
```

### Environment-Specific Secrets
Add appropriate secrets to each environment as needed.

## Code Owners File

Ensure you have a `.github/CODEOWNERS` file:

```
# Global owners
* @your-team

# Backend specific
/app/ @backend-team
/requirements.txt @backend-team

# Frontend specific  
/frontend/ @frontend-team

# Infrastructure
/Dockerfile @devops-team
/.github/ @devops-team
/scripts/ @devops-team

# Documentation
/docs/ @tech-writers @product-team
```

## Verification Checklist

After setting up branch protection:

- [ ] Create a test PR to verify all checks run
- [ ] Verify required number of approvals
- [ ] Test that stale reviews are dismissed
- [ ] Confirm status checks block merging when failing
- [ ] Verify deployment protection works
- [ ] Test secret scanning blocks pushes with secrets
- [ ] Confirm administrators are subject to rules

## Troubleshooting

### Common Issues

1. **Status checks not appearing:**
   - Ensure workflow names match exactly
   - Run workflows at least once to register them

2. **Deployment protection not working:**
   - Verify environment names match in workflows
   - Check environment protection rules are saved

3. **Required reviewers bypass:**
   - Ensure users have appropriate repository permissions
   - Check if users are in the bypass list

### Contact

For questions about branch protection setup, contact the DevOps team or repository administrators.