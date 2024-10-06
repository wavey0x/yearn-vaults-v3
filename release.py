import os
import time
import json
import yaml
from web3 import Web3
from solcx import compile_source, install_solc
import vyper

# Initialize web3 (assuming you are connecting to a local node)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

INIT_GOV = '0x6f3cBE2ab3483EC4BA7B672fbdCa0E9B33F88db8'
V3_VAULT_ORIGINAL = '0xcA78AF7443f3F8FA0148b746Cb18FF67383CDF3f'
RELEASE_DATA_FILE_PATH = "./release/release_data.json"
config_file = "release_config.yaml"

# Optionally install a specific Solidity compiler version (adjust if needed)
install_solc('0.8.19')

def main():
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
    for contract_file in contracts_list:
        contract_name, bytecode, abi = compile_contract(contract_file)

        if bytecode and abi:
            data["releases"][release]["contracts"][contract_name] = {
                "bytecode": bytecode,
                "abi": abi,
                "constructor_args": extract_constructor_args(abi)
            }
            print(f"Processed contract: {contract_name}")

    # Convert data to JSON and print (or save to file if needed)
    json_data = json.dumps(data, indent=2)

    save_to_file(RELEASE_DATA_FILE_PATH, json_data)

    print(f"Release data written to {RELEASE_DATA_FILE_PATH}")


def get_contract_files():
    """
    Searches for files with .sol or .vy extensions within the specified root directory,
    excluding any paths that are within the exclude_dir.
    """
    root_directory = './contracts'
    directories_to_exclude = ['contracts/.cache', 'contracts/interfaces', 'contracts/test']
    contracts = []

    for root, dirs, files in os.walk(root_directory, topdown=True):
        # Normalize the root to simplify path handling
        normalized_root = os.path.normpath(root)
        # Filter out directories to exclude by checking the full normalized path
        dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(normalized_root, d)) not in directories_to_exclude]

        for file in files:
            if file.endswith('.sol') or file.endswith('.vy'):
                contracts.append(os.path.join(normalized_root, file))  # Append the full path

    return contracts

def compile_contract(contract_path):
    """
    Compiles a Solidity or Vyper contract depending on the file extension.
    Returns the contract name, bytecode, and ABI.
    """
    contract_name = os.path.splitext(os.path.basename(contract_path))[0]

    if contract_path.endswith('.sol'):
        return compile_solidity_contract(contract_path, contract_name)
    elif contract_path.endswith('.vy'):
        return compile_vyper_contract(contract_path, contract_name)
    else:
        return contract_name, None, None

def compile_solidity_contract(contract_path, contract_name):
    """
    Compiles a Solidity contract using solcx.
    Returns the contract name, bytecode, and ABI.
    """
    with open(contract_path, 'r') as f:
        source_code = f.read()

    try:
        compiled_sol = compile_source(source_code)
        contract_interface = compiled_sol[f'<stdin>:{contract_name}']
        bytecode = contract_interface['bin']
        abi = contract_interface['abi']
        return contract_name, bytecode, abi
    except Exception as e:
        print(f"Error compiling Solidity contract {contract_name}: {e}")
        return contract_name, None, None

def compile_vyper_contract(contract_path, contract_name):
    """
    Compiles a Vyper contract using the Vyper compiler.
    Returns the contract name, bytecode, and ABI.
    """
    with open(contract_path, 'r') as f:
        source_code = f.read()

    try:
        bytecode = vyper.compile_code(source_code, ['bytecode'])['bytecode']
        abi = vyper.compile_code(source_code, ['abi'])['abi']
        return contract_name, bytecode, abi
    except Exception as e:
        print(f"Error compiling Vyper contract {contract_name}: {e}")
        return contract_name, None, None

# Load the YAML config file
def load_config(config_file):
    with open(config_file, "r") as file:
        return yaml.safe_load(file)

# Extract constructor arguments from the ABI
def extract_constructor_args(abi):
    constructor = next((item for item in abi if item['type'] == 'constructor'), None)
    if not constructor:
        return {}  # No constructor, return an empty dict
    
    abi_args = constructor['inputs']
    constructor_args = {arg['name']: arg['type'] for arg in abi_args}
    return constructor_args

def save_to_file(file_path, data):
    # Extract the directory from the file path
    directory = os.path.dirname(file_path)
    
    # If the directory does not exist, create it
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory {directory} created.")
    
    # Write the data to the file
    with open(file_path, 'w') as file:
        file.write(data)
        print(f"File saved to {file_path}")

if __name__ == "__main__":
    main()