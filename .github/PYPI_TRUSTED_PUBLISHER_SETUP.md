# PyPI Trusted Publisher Setup Guide

This guide helps you configure PyPI Trusted Publisher for secure, automated publishing using GitHub Actions.

## Step 1: Configure PyPI Trusted Publisher

### For PyPI (Production)

1. **Login to PyPI**: Go to [pypi.org](https://pypi.org) and log in to your account

2. **Navigate to Publishing**: Go to your account settings → Publishing → Add a new pending publisher

3. **Fill in the details**:
   - **PyPI project name**: `automagik`
   - **Owner**: `namastexlabs`
   - **Repository name**: `automagik`
   - **Workflow filename**: `publish-to-pypi.yml`
   - **Environment name**: `pypi` (optional but recommended)

4. **Submit**: Click "Add" to create the pending publisher

### For TestPyPI (Optional - for testing)

1. **Login to TestPyPI**: Go to [test.pypi.org](https://test.pypi.org) and log in

2. **Repeat the same process** with these details:
   - **PyPI project name**: `automagik`
   - **Owner**: `namastexlabs`
   - **Repository name**: `automagik`
   - **Workflow filename**: `publish-to-pypi.yml`
   - **Environment name**: `testpypi`

## Step 2: Configure GitHub Repository

### Create Environments (Recommended)

1. **Go to your GitHub repository**: [https://github.com/namastexlabs/automagik](https://github.com/namastexlabs/automagik)

2. **Navigate to Settings** → Environments

3. **Create `pypi` environment**:
   - Click "New environment"
   - Name: `pypi`
   - Add deployment protection rules if needed
   - Set environment URL: `https://pypi.org/p/automagik`

4. **Create `testpypi` environment** (optional):
   - Name: `testpypi`
   - Set environment URL: `https://test.pypi.org/p/automagik`

## Step 3: Test the Setup

### Option A: Create a Release (Recommended)

1. **Create a new tag**:
   ```bash
   git tag v0.4.0
   git push origin v0.4.0
   ```

2. **Create a GitHub Release**:
   - Go to your repository → Releases → Create a new release
   - Choose tag: `v0.4.0`
   - Release title: `v0.4.0`
   - Add release notes
   - Click "Publish release"

### Option B: Manual Trigger

1. **Go to Actions tab** in your GitHub repository
2. **Select "Publish to PyPI" workflow**
3. **Click "Run workflow"**
4. **Enter version**: `0.4.0`
5. **Click "Run workflow"**

## Step 4: Verify Publication

1. **Check GitHub Actions**: Monitor the workflow execution in the Actions tab
2. **Verify on PyPI**: Check that your package appears at [https://pypi.org/project/automagik/](https://pypi.org/project/automagik/)
3. **Test installation**: `pip install automagik==0.4.0`

## Workflow Features

✅ **Secure**: Uses OpenID Connect tokens instead of API keys  
✅ **Automated**: Triggers on releases and tags  
✅ **Verified**: Includes package verification before publishing  
✅ **Flexible**: Can be triggered manually with custom versions  
✅ **Signed**: Packages are signed with Sigstore for security  
✅ **TestPyPI**: Optional testing on TestPyPI before production  

## Troubleshooting

### Common Issues

1. **"Trusted publisher not configured"**:
   - Ensure you've added the pending publisher on PyPI
   - Check that repository owner/name matches exactly
   - Verify workflow filename is correct

2. **"Environment protection rules"**:
   - Go to repository Settings → Environments
   - Review protection rules for the `pypi` environment

3. **"Permission denied"**:
   - Ensure the workflow has `id-token: write` permission
   - Check that the repository settings allow Actions

### Get Help

- **PyPI Help**: [https://pypi.org/help/](https://pypi.org/help/)
- **GitHub Actions Docs**: [https://docs.github.com/en/actions](https://docs.github.com/en/actions)
- **Trusted Publisher Guide**: [https://docs.pypi.org/trusted-publishers/](https://docs.pypi.org/trusted-publishers/)

## Next Steps

After setup is complete:

1. **Remove API tokens**: Delete any PyPI API tokens you no longer need
2. **Update documentation**: Document the new release process for your team
3. **Set up branch protection**: Consider requiring PR reviews for the main branch
4. **Automate versioning**: Consider tools like `bump2version` for version management