# Ansible Playbooks Summary

## Available Playbooks

### 1. Organization Management

#### `create_organization.yml`
**Purpose:** Create a new organization in Ops Manager

**Usage:**
```bash
ansible-playbook playbooks/create_organization.yml --ask-vault-pass
```

**Prompts:**
- Organization name

**Output:**
- Organization ID
- Organization name
- Saved to `organization_<ID>_details.txt`

**Note:** Created org won't be visible until you add a user to it.

---

#### `delete_organization.yml`
**Purpose:** Delete an organization (WARNING: Deletes all projects too!)

**Usage:**
```bash
ansible-playbook playbooks/delete_organization.yml --ask-vault-pass
```

**Prompts:**
- Organization ID
- Confirmation: Type "DELETE" (exact case)

**Safeguards:**
- Checks for existing projects
- Requires explicit confirmation

---

### 2. Project Management

#### `create_project.yml`
**Purpose:** Create a new project (interactive)

**Usage:**
```bash
ansible-playbook playbooks/create_project.yml --ask-vault-pass
```

**Prompts:**
- Project name
- Tags (optional, comma-separated)

**Output:**
- Project ID
- Project name
- Agent API Key (needed for agent installation)
- Saved to `project_<ID>_details.txt`

**Note:** Project won't be visible until you add a user to it.

---

#### `create_project_noninteractive.yml`
**Purpose:** Create project via command-line variables (for automation)

**Usage:**
```bash
ansible-playbook playbooks/create_project_noninteractive.yml \
  --ask-vault-pass \
  -e "project_name='My Project'" \
  -e "project_tags=['DEV','PROD']"
```

---

#### `delete_project.yml`
**Purpose:** Delete a project

**Usage:**
```bash
ansible-playbook playbooks/delete_project.yml --ask-vault-pass
```

**Prompts:**
- Project ID
- Confirmation: Type "yes"

**Requirements:**
- No active deployments (replica sets or shards)
- No backup jobs
- Must be Project Owner

**Safeguards:**
- Checks for active deployments
- Shows project details before deletion
- Requires confirmation

---

### 3. Combined Operations

#### `create_org_and_project.yml`
**Purpose:** Create both organization and project in one go

**Usage:**
```bash
ansible-playbook playbooks/create_org_and_project.yml --ask-vault-pass
```

**Prompts:**
- Organization name
- Project name
- Tags (optional)

**Output:**
- Organization ID and name
- Project ID, name, and Agent API Key
- Saved to `org_<ID>_project_<ID>_details.txt`

**Recommended:** Use this instead of separate org/project creation.

---

### 4. User Management

#### `get_user_id.yml`
**Purpose:** Find a user's ID by username or email

**Usage:**
```bash
ansible-playbook playbooks/get_user_id.yml --ask-vault-pass
```

**Prompts:**
- Username or email address

**Output:**
- User ID
- Username
- Email
- Current roles

**Use Case:** Get User ID before adding to org/project

---

#### `add_user_to_org.yml`
**Purpose:** Add a user to an organization (makes org visible in dashboard)

**Usage:**
```bash
ansible-playbook playbooks/add_user_to_org.yml --ask-vault-pass
```

**Prompts:**
- Organization ID
- User ID
- Role (default: ORG_OWNER)

**Available Roles:**
- `ORG_OWNER` - Full admin
- `ORG_MEMBER` - Can view and create projects
- `ORG_READ_ONLY` - View only
- `ORG_GROUP_CREATOR` - Can create projects

**Critical:** Run this after creating org to make it visible!

---

#### `add_user_to_project.yml`
**Purpose:** Add a user to a project (makes project visible in dashboard)

**Usage:**
```bash
ansible-playbook playbooks/add_user_to_project.yml --ask-vault-pass
```

**Prompts:**
- Project ID
- User ID
- Role (default: GROUP_OWNER)

**Available Roles:**
- `GROUP_OWNER` - Full admin
- `GROUP_AUTOMATION_ADMIN` - Manage deployments
- `GROUP_BACKUP_ADMIN` - Manage backups
- `GROUP_MONITORING_ADMIN` - Manage monitoring
- `GROUP_READ_ONLY` - View only

**Critical:** Run this after creating project to make it visible!

---

## Typical Workflows

### Workflow 1: Create Organization + Project (Fresh Start)

```bash
# Step 1: Create org and project
ansible-playbook playbooks/create_org_and_project.yml --ask-vault-pass

# Step 2: Get your user ID
ansible-playbook playbooks/get_user_id.yml --ask-vault-pass

# Step 3: Add yourself to org
ansible-playbook playbooks/add_user_to_org.yml --ask-vault-pass

# Step 4: Add yourself to project
ansible-playbook playbooks/add_user_to_project.yml --ask-vault-pass

# Step 5: Verify in dashboard
```

---

### Workflow 2: Create Multiple Projects in Existing Org

```bash
# Create project 1
ansible-playbook playbooks/create_project.yml --ask-vault-pass
ansible-playbook playbooks/add_user_to_project.yml --ask-vault-pass

# Create project 2
ansible-playbook playbooks/create_project.yml --ask-vault-pass
ansible-playbook playbooks/add_user_to_project.yml --ask-vault-pass
```

---

### Workflow 3: Cleanup/Teardown

```bash
# Delete projects first (one by one)
ansible-playbook playbooks/delete_project.yml --ask-vault-pass

# Then delete organization (if needed)
ansible-playbook playbooks/delete_organization.yml --ask-vault-pass
```

---

### Workflow 4: Add Team Member to Existing Resources

```bash
# Get the new user's ID
ansible-playbook playbooks/get_user_id.yml --ask-vault-pass

# Add to organization
ansible-playbook playbooks/add_user_to_org.yml --ask-vault-pass

# Add to specific projects
ansible-playbook playbooks/add_user_to_project.yml --ask-vault-pass
```

---

## Important Notes

### API Key Requirements

- **Create Org**: Requires `Global Owner` role
- **Create Project**: Requires `Organization Owner` or `Organization Project Creator`
- **Add Users**: Requires `Organization Owner` (for org) or `Project Owner` (for project)
- **Delete Resources**: Requires respective Owner roles

### Visibility Issue

**Organizations and projects created via API are NOT visible in the dashboard by default!**

You MUST add at least one user with appropriate permissions to make them visible.

### Idempotency

Current playbooks are **NOT idempotent**:
- Re-running create operations will create duplicate resources
- Use unique names or check manually before re-running

### State Management

- IDs are saved to text files in the current directory
- Keep these files for reference when deleting resources
- No centralized state management yet

---

## Configuration Files

### `group_vars/all.yml`
Contains:
- Ops Manager URL
- API version
- Organization ID (if using existing org)

### `group_vars/vault.yml`
Contains (encrypted):
- API Public Key
- API Private Key

**Encrypt with:**
```bash
ansible-vault encrypt group_vars/vault.yml
```

**Edit with:**
```bash
ansible-vault edit group_vars/vault.yml
```

---

## Error Handling

### Common Errors

**401 Unauthorized:**
- Check API keys in vault.yml
- Verify API key has required permissions
- Check Ops Manager URL

**404 Not Found:**
- Verify resource IDs are correct
- Resource may have been deleted
- Check you have access to the resource

**Cannot delete project with active deployments:**
- Delete all clusters first
- Disable backups
- Remove snapshots
- Then retry

**User not found:**
- Verify username/email spelling
- User may not exist in Ops Manager
- You may not have permission to view the user

---

## Next Steps

Coming soon:
- Agent installation playbooks
- Cluster deployment playbooks
- Backup management playbooks
- Monitoring configuration playbooks
- Update/upgrade playbooks
- Complete idempotent lifecycle management
