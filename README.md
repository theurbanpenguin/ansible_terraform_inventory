# ansible_terraform_inventory
Ansible Dynamic Inventory Example Using Terraform Output

Example of dynamic inventory for ansible using IP address of terraform deployed AWS hosts
```bash
ansible -i inventory.py all -m ping
```
