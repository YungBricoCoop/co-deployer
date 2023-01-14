import sys
import json
import paramiko
import pysftp
import ftplib
from argparse import ArgumentParser

CONFIG_FILE = "deploy.config.json"

def load_config():
	"""
	This function reads the configuration from a file named 'deploy.config.json'
	:param file_path: the path of the file to read
	:return: the configuration as a dictionary
	"""
	try:
		with open(CONFIG_FILE, "r") as f:
			config = json.loads(f.read())
			return config
	except FileNotFoundError:
		print(f"File {CONFIG_FILE} not found.")
		sys.exit(1)
	except json.decoder.JSONDecodeError:
		print(f"Invalid JSON in file {CONFIG_FILE}.")
		sys.exit(1)

def validate_hosts(config):
	"""
	This function validates the hosts in the configuration
	:param config: the configuration as a dictionary
	:return: True if the hosts are valid, False otherwise
	"""
	required_fields = ["name", "host"]
	user_fields = ["user", "ftp_user", "ssh_user"]
	password_fields = ["password", "ftp_password", "ssh_password"]

	valid = True
	
	for host in config["hosts"]:
		# check if the required fields are present
		is_required_field_missing = any([field not in host for field in required_fields])
		if is_required_field_missing: print(f"Missing required field : {', '.join(required_fields)}")
		
		# check if one of the user fields is present
		is_user_field_missing = not any([field in host for field in user_fields])
		if is_user_field_missing: print(f"Need at least one user field : {', '.join(user_fields)}")
		
		# check if one of the password fields is present
		is_password_field_missing = not any([field in host for field in password_fields])
		if is_password_field_missing: print(f"Need at least one password field : {', '.join(password_fields)}")

		valid = valid and not is_required_field_missing and not is_user_field_missing and not is_password_field_missing
	
	if not valid:
		print("Invalid hosts configuration.")
		sys.exit(1)
	
	return config["hosts"]

def validate_deployments(config):
	"""
	This function validates the deployments in the configuration
	:param config: the configuration as a dictionary
	:return: True if the deployments are valid, False otherwise
	"""
	required_fields = ["name", "host", "arg", "protocol"]
	protocol_fields = ["ftp", "sftp", "ssh"]
	files_cmd_fields = ["files", "cmd"]
	
	valid = True
	
	for deployment in config["deployments"]:
		# check if the required fields are present
		is_required_field_missing = any([field not in deployment for field in required_fields])
		if is_required_field_missing: print(f"Missing required field : {', '.join(required_fields)}")
		
		# check if the protocol is valid
		protocol = deployment.get("protocol")
		is_protocol_field_invalid = protocol not in protocol_fields
		if is_protocol_field_invalid: print(f"Invalid protocol ({protocol}) : {', '.join(protocol_fields)}")

		is_files_or_cmd_missing = not any([field in deployment for field in files_cmd_fields])
		if is_files_or_cmd_missing: print(f"Need at least one of the following fields : {', '.join(files_cmd_fields)}")

		valid = valid and not is_required_field_missing and not is_protocol_field_invalid and not is_files_or_cmd_missing
	
	if not valid:
		print("Invalid deployments configuration.")
		sys.exit(1)

	return config["deployments"]

def parse_arguments(deployments):
	"""
	This function parses the command line arguments

	Parameters:
		deployments (list): the list of deployments

	:return: the arguments as a dictionary
	"""
	parser = ArgumentParser()
	for deployment in deployments:
		parser.add_argument(deployment["arg"], f"--{deployment['name']}", help=f"Execute the deployment {deployment['name']}", action="store_true")
	
	# only get the arguments that are present
	arguments = [x for x in  vars(parser.parse_args()) if vars(parser.parse_args())[x]]
	
	return arguments

def deploy_all(deployments, arguments):
	"""
	This function deploys all the deployments that are present in the arguments

	Parameters:
		deployments (list): the list of deployments
		arguments (list): the list of arguments
	"""
	deployments = [deployment for deployment in deployments if deployment["name"] in arguments]
	for deployment in deployments:
		deploy(deployment)

def deploy(deployment):
	"""
	This function deploys using the specified deployment settings

	Parameters:
		deployment (dict): the deployment settings
	
	"""

if __name__ == "__main__":
	config = load_config()
	hosts = validate_hosts(config)
	deployments = validate_deployments(config)
	arguments = parse_arguments(deployments)
	deploy_all(deployments, arguments)