# Branch Protection & Development Workflow

## 🔒 Branch Protection Rules

The `main` branch is now protected with the following rules:

### ✅ **Protection Settings Applied:**
- **Pull Request Required**: All changes to `main` must go through a Pull Request
- **Review Required**: At least 1 approving review required before merge
- **Dismiss Stale Reviews**: Reviews are dismissed when new commits are pushed
- **Conversation Resolution**: All PR conversations must be resolved before merge
- **No Force Push**: Force pushes to `main` are blocked
- **No Direct Commits**: Direct commits to `main` are blocked (except for admins)

### 👑 **Admin Privileges:**
- **Repository admins can bypass** branch protection rules
- Admins can push directly to `main` in emergency situations
- `enforce_admins: false` allows admin override when necessary

## 🔄 Development Workflow

### **Standard Development Process:**

1. **Start from `dev` branch:**
   ```bash
   git checkout dev
   git pull origin dev
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # Make your changes
   git add .
   git commit -m "feat: your feature description"
   git push -u origin feature/your-feature-name
   ```

3. **Create Pull Request:**
   - **Source**: `feature/your-feature-name`
   - **Target**: `dev` (for feature development)
   - **Target**: `main` (for releases from `dev`)

4. **Review Process:**
   - At least 1 reviewer must approve
   - All conversations must be resolved
   - CI/CD checks must pass (if configured)

5. **Merge & Cleanup:**
   ```bash
   # After PR is merged, clean up locally
   git checkout dev
   git pull origin dev
   git branch -d feature/your-feature-name
   ```

### **Release Process (`dev` → `main`):**

1. **Create Release PR:**
   ```bash
   gh pr create --base main --head dev --title "Release v0.x.x" --body "Release notes..."
   ```

2. **Review & Merge:**
   - Requires admin approval for production releases
   - Comprehensive testing on `dev` branch first
   - All conversations resolved

3. **Post-Release:**
   ```bash
   # Tag the release
   git checkout main
   git pull origin main
   git tag -a v0.x.x -m "Release v0.x.x"
   git push origin v0.x.x
   
   # Create GitHub release
   gh release create v0.x.x --title "v0.x.x" --generate-notes
   ```

## 🚨 Emergency Hotfix Process

**For critical production fixes (Admin Only):**

1. **Direct hotfix to `main`:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/critical-issue
   # Make minimal fix
   git commit -m "hotfix: critical issue description"
   git push -u origin hotfix/critical-issue
   ```

2. **Emergency PR to `main`:**
   ```bash
   gh pr create --base main --head hotfix/critical-issue --title "HOTFIX: Critical Issue"
   ```

3. **Admin merge with bypass** (if necessary)

4. **Backport to `dev`:**
   ```bash
   git checkout dev
   git merge main  # Bring hotfix back to dev
   git push origin dev
   ```

## 🔧 Branch Management

### **Branch Structure:**
```
main (protected)     ← Production releases only
├── dev              ← Main development branch  
│   ├── feature/auth-system
│   ├── feature/api-improvement
│   └── feature/ui-update
└── hotfix/critical  ← Emergency fixes (rare)
```

### **Branch Permissions:**
- **`main`**: Protected, PR required, admin bypass allowed
- **`dev`**: Open for direct commits by team members
- **`feature/*`**: Personal feature branches
- **`hotfix/*`**: Emergency fixes (admin-managed)

## ⚙️ Configuration Details

The branch protection was configured using GitHub API with these settings:

```json
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "enforce_admins": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
```

## 🛠️ Modifying Protection Rules

**To update branch protection settings:**

```bash
# Edit the protection settings
gh api --method PUT /repos/namastexlabs/automagik/branches/main/protection \
  --input updated_protection.json
```

**Or use GitHub Web UI:**
- Go to: Repository Settings → Branches → main → Edit
- Modify protection rules as needed

This workflow ensures code quality while allowing admin flexibility for emergency situations.