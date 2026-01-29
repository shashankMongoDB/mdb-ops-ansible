# MDBaaS Ansible Playbooks

## Environment setup
1. Populate `./.env` using the placeholders provided (Ops Manager credentials, VM details, Prometheus, etc.).
2. Load those values in every shell session before invoking Ansible:
   ```bash
   source ./load_env.sh
   ```

## Running playbooks
- Always prefix playbook runs with the loader to guarantee a consistent environment, for example:
  ```bash
  source ./load_env.sh && ansible-playbook playbooks/list_organizations.yml
  source ./load_env.sh && ansible-playbook playbooks/create_project.yml
  source ./load_env.sh && ansible-playbook playbooks/cluster_creation/install_agents.yml -i playbooks/cluster_creation/replica_set/inventory_simple.yml
  ```
- All playbooks now consume settings exclusively via the exported environment variables, so no other vars files or prompts are required beyond runtime inputs (e.g., IDs or confirmations).
  The automation-agent installer now lives at `playbooks/cluster_creation/install_agents.yml`, with a thin compatibility shim left under `replica_set/`.
