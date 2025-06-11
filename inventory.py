#!/usr/bin/env python3

import json
import subprocess
import argparse
import sys
import os

class TerraformInventory:
    def __init__(self, terraform_dir="."):
        self.terraform_dir = terraform_dir
        self.inventory = {
            "_meta": {
                "hostvars": {}
            },
            "all": {
                "hosts": [],
                "children": ["aws_instances"]
            },
            "aws_instances": {
                "hosts": []
            }
        }

    def get_terraform_outputs(self):
        """Get Terraform outputs as JSON"""
        try:
            # Change to terraform directory
            original_dir = os.getcwd()
            os.chdir(self.terraform_dir)
            
            # Run terraform output -json
            result = subprocess.run(
                ['terraform', 'output', '-json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            os.chdir(original_dir)
            return json.loads(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"Error running terraform output: {e}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing terraform output JSON: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error getting terraform outputs: {e}", file=sys.stderr)
            sys.exit(1)

    def build_inventory(self):
        """Build Ansible inventory from Terraform outputs"""
        outputs = self.get_terraform_outputs()
        
        hosts_added = False
        
        # Look for outputs containing IP addresses (simple list format)
        for output_name, output_data in outputs.items():
            value = output_data.get('value')
            
            # Handle list of IP addresses (like ubuntu_ip = ["13.42.7.8"])
            if isinstance(value, list):
                for i, ip in enumerate(value):
                    if isinstance(ip, str) and self.is_valid_ip(ip):
                        # Create hostname based on output name and index
                        base_name = output_name.replace('_ip', '').replace('_', '-')
                        hostname = f"{base_name}-{i + 1}" if len(value) > 1 else base_name
                        self.add_host(hostname, ip)
                        hosts_added = True
            
            # Handle single IP address string
            elif isinstance(value, str) and self.is_valid_ip(value):
                hostname = output_name.replace('_ip', '').replace('_', '-')
                self.add_host(hostname, value)
                hosts_added = True
        
        if not hosts_added:
            print("Warning: No IP address outputs found in Terraform state", file=sys.stderr)
            print("Available outputs:", list(outputs.keys()), file=sys.stderr)

    def is_valid_ip(self, ip):
        """Basic IP address validation"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False

    def add_host(self, hostname, ip, extra_vars=None):
        """Add a host to the inventory"""
        self.inventory["all"]["hosts"].append(hostname)
        self.inventory["aws_instances"]["hosts"].append(hostname)
        
        host_vars = {
            "ansible_host": ip,
            "ansible_python_interpreter": "/usr/bin/python3",
            "ansible_connection": "ssh"
        }
        
        # Add any extra variables from Terraform outputs
        if extra_vars:
            for key, value in extra_vars.items():
                if key not in ['public_ip', 'private_ip']:  # Don't duplicate IP info
                    host_vars[f"terraform_{key}"] = value
        
        self.inventory["_meta"]["hostvars"][hostname] = host_vars

    def to_json(self):
        """Return the inventory as JSON"""
        return json.dumps(self.inventory, indent=2)

    def output_list(self):
        """Output the list of hosts (for --list)"""
        self.build_inventory()
        print(self.to_json())

    def output_host(self, host):
        """Output the variables for a specific host (for --host)"""
        self.build_inventory()
        host_vars = self.inventory["_meta"]["hostvars"].get(host, {})
        print(json.dumps(host_vars, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Ansible dynamic inventory from Terraform outputs')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true', help='List all hosts')
    group.add_argument('--host', help='Get variables for a specific host')
    parser.add_argument('--terraform-dir', default='.',
                       help='Path to Terraform directory (default: current directory)')
    args = parser.parse_args()

    inventory = TerraformInventory(args.terraform_dir)
    
    if args.list:
        inventory.output_list()
    elif args.host:
        inventory.output_host(args.host)


if __name__ == '__main__':
    main()
