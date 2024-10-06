import os
import time
import json
import yaml
from ape import project

"""
This script is designed to run via GitHub Actions when a new release is cut.
It generates release data for smart contracts, agnostic to Ape and Foundry repositories.
The generated data is published to api/deploy_data.json, providing a standardized
format for contract deployment information across different development frameworks.
"""

INIT_GOV = '0x6f3cBE2ab3483EC4BA7B672fbdCa0E9B33F88db8'
V3_VAULT_ORIGINAL = '0xcA78AF7443f3F8FA0148b746Cb18FF67383CDF3f'
config_file = "release_config.yaml"

def main(release_name):
    # Validate the config
    # config = load_config(config_file)
    # try:
    #     validate_config(config, contracts_list)
    # except ValueError as e:
    #     print(f"Validation failed: {e}")
    #     exit(1)
    if not release_name:
        release_name = "v3.0.3"
    build_release_data(release_name)

def build_release_data(release: str):
    data = {
        "releases": {
            release: {
                "release_timestamp": int(time.time()),
                "contracts": {}
            }
        }
    }

    contracts_list = get_contract_files()
    # READ FROM CONFIG FILE
    # SHOULD CONTAIN A REGISTRY OF CONTRACTS FOR THE ACTIVE REPOSITORY
    # SHOULD DEFINE THE CONSTRUCTOR ARGUMENTS
    for contract in contracts_list:
        c = getattr(project, contract).contract_type
        bytecode = c.deployment_bytecode.bytecode
        abi = c.dict()['abi']
        data["releases"][release]["contracts"][contract] = {
            "bytecode": bytecode,
            "abi": abi,
            "constructor_args": extract_constructor_args(abi)
        }
        print(contract)

    json_data = json.dumps(data)
    print(contracts_list)

def get_contract_files():
    """
    Searches for files with .sol or .vy extensions within the specified root directory,
    excluding any paths that are within the exclude_dir.

    :return: List of full file paths with the specified extensions.
    """
    root_directory = './contracts'
    directories_to_exclude = ['contracts/.cache','contracts/interfaces','contracts/test']
    contracts = []

    for root, dirs, files in os.walk(root_directory, topdown=True):
        # Normalize the root to simplify path handling
        normalized_root = os.path.normpath(root)
        # Filter out directories to exclude by checking the full normalized path
        dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(normalized_root, d)) not in directories_to_exclude]

        for file in files:
            if file.endswith('.sol') or file.endswith('.vy'):
                contracts.append(file.split('.')[0])  # Append the full path, not just the file name

    return contracts

# Load the YAML config file
def load_config(config_file):
    with open(config_file, "r") as file:
        return yaml.safe_load(file)

# Check if constructor args match the ABI from the config
def extract_constructor_args(abi):
    constructor = None
    for item in abi:
        if item['type'] == 'constructor':
            constructor = item
            break

    if not constructor:
        return {}  # No constructor, but config has args, invalid
    
    # Ensure the number of arguments match
    abi_args = constructor['inputs']

    return constructor