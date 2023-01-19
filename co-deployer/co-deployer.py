import os
import sys
import json
import shutil
import uuid
import subprocess
import tempfile
import paramiko
import ftplib
from argparse import ArgumentParser
from rich import print
from rich.progress import track

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
	
	valid = True
	
	for deployment in config["deployments"]:
		# check if the required fields are present
		is_required_field_missing = any([field not in deployment for field in required_fields])
		if is_required_field_missing: print(f"Missing required field : {', '.join(required_fields)}")
		
		# check if the protocol is valid
		protocol = deployment.get("protocol")
		is_protocol_field_invalid = protocol not in protocol_fields
		if is_protocol_field_invalid: print(f"Invalid protocol ({protocol}) : {', '.join(protocol_fields)}")

		host = [host for host in config["hosts"] if host["name"] == deployment["host"]]
		if not host or not len(hosts): print(f"Host {deployment['host']} not found.")
		else: host = host[0]
		deployment["host"] = host

		valid = valid and not is_required_field_missing and not is_protocol_field_invalid and host
	
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
	host = deployment["host"]
	hostname = host.get("host")

	ftp_user = host.get("ftp_user") or host.get("user")
	ftp_password = host.get("ftp_password") or host.get("password")
	ftp_port = host.get("ftp_port") or 21
	ftp_remote_path = deployment.get("ftp_remote_path") or deployment.get("remote_path")

	sfpt_user = host.get("sfpt_user") or host.get("user")
	sfpt_password = host.get("sfpt_password") or host.get("password")
	sfpt_port = host.get("sfpt_port") or 22
	sfpt_remote_path = deployment.get("sfpt_remote_path") or deployment.get("remote_path")

	ssh_user = host.get("ssh_user") or host.get("user")
	ssh_password = host.get("ssh_password") or host.get("password")
	ssh_port = host.get("ssh_port") or 22


	# protocol to use
	protocol = deployment.get("protocol")
	
	# commands to execute
	cmd = deployment.get("cmd")
	start_cmd = deployment.get("start_cmd")
	end_cmd = deployment.get("end_cmd")
	start_ssh_cmd = deployment.get("start_ssh_cmd")
	end_ssh_cmd = deployment.get("end_ssh_cmd")


	exclude = deployment.get("exclude") or ["deploy.config.json"]
	

	# define connection
	ssh = None
	ftp = None
	sftp = None

	# create tmp directory
	tmp_dir = create_tmp_file_structure(".", exclude)


	# init connection(s)
	if protocol == "ssh" or (start_ssh_cmd or end_ssh_cmd):
		ssh = ssh_connect(hostname, ssh_user, ssh_password, ssh_port)

	if protocol == "ftp":
		ftp = ftp_connect(hostname, ftp_user, ftp_password, ftp_port)
	
	if protocol == "sftp":
		sftp = sftp_connect(hostname, sfpt_user, sfpt_password, sfpt_port)

	
	# execute commands, upload files, etc.
	if start_cmd: print(f"Command result : {execute(start_cmd)}")
	if protocol == "ssh" or (start_ssh_cmd or end_ssh_cmd):
		if start_ssh_cmd: print(f"SSH command result : {ssh_execute(ssh, start_ssh_cmd)}")
		if cmd : print(f"SSH command result : {ssh_execute(ssh, cmd)}")
	
	if protocol == "ftp":
		ftp_upload(ftp, tmp_dir, ftp_remote_path)
	
	if protocol == "sftp":
		sftp_upload(sftp, tmp_dir, sfpt_remote_path)
	
	if end_ssh_cmd:
		if ssh: print(f"SSH command result : {ssh_execute(ssh, end_ssh_cmd)}")
		else: print("SSH connection required to execute command after transfer.")
	
	if end_cmd: print(f"Command result : {execute(end_cmd)}")
	
	# close connections
	close_connections(ssh, ftp, sftp)

	# remove tmp directory
	remove_tmp_dir(tmp_dir)

def close_connections(ssh, ftp, sftp):
	"""
	This function closes the connections

	Parameters:
		ssh (SSHClient): the SSH client
		ftp (FTP): the FTP client
		sftp (SFTP): the SFTP client
	"""
	try:
		if ssh: 
			ssh.close()
			print("[bold green]Closed connection[/bold green] : SSH")
		if ftp: 
			ftp.close()
			print("[bold green]Closed connection[/bold green] : FTP")
		if sftp: 
			sftp.close()
			print("[bold green]Closed connection[/bold green] : SFTP")

	except Exception as e:
		print("[bold red]Error while closing connection(s)[/bold red] :", e)

	
def remove_tmp_dir(tmp_dir):
	"""
	This function removes the tmp directory

	Parameters:
		tmp_dir (str): the tmp directory
	"""
	try:
		shutil.rmtree(tmp_dir)
		print(f"[bold green]Removed[/bold green] : Temp directory")
	except Exception as e:
		print("[bold red]Error while removing tmp directory[/bold red] :", e)
	
def ssh_connect(hostname, ssh_user, ssh_password, ssh_port):
	"""
	This function connects to the SSH server

	Parameters:
		ssh_user (str): the SSH user
		ssh_password (str): the SSH password
		ssh_port (int): the SSH port

	:return: the SSH client
	"""
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(hostname, username=ssh_user, password=ssh_password, port=ssh_port)
	except Exception as e:
		print("[bold red]SSH Error[/bold red] :", e)
		sys.exit(1)
	return ssh

def ftp_connect(hostname, ftp_user, ftp_password, ftp_port):
	"""
	This function connects to the FTP server

	Parameters:
		hostname (str): the hostname
		ftp_user (str): the FTP user
		ftp_password (str): the FTP password
		ftp_port (int): the FTP port

	:return: the FTP client
	"""
	try:
		ftp = ftplib.FTP()
		ftp.connect(hostname, ftp_port)
		ftp.login(ftp_user, ftp_password)
	except Exception as e:
		print("[bold red]FTP Error[/bold red] :", e)
		sys.exit(1)
	return ftp

def sftp_connect(hostname, sfpt_user, sfpt_password, sfpt_port):
	"""
	This function connects to the SFTP server

	Parameters:
		hostname (str): the hostname
		sfpt_user (str): the SFTP user
		sfpt_password (str): the SFTP password
		sfpt_port (int): the SFTP port

	:return: the SFTP client
	"""
	try:
		transport = paramiko.Transport((hostname, sfpt_port))
		transport.connect(username=sfpt_user, password=sfpt_password)
		sftp = transport.open_sftp_client()
		return sftp
	except Exception as e:
		print("[bold red]SFTP Error[/bold red] :", e)
		sys.exit(1)

def ssh_execute(ssh, cmd):
	"""
	This function executes a command on the SSH server

	Parameters:
		ssh (SSHClient): the SSH client
		cmd (str): the command to execute

	:return: the output of the command
	"""
	stdin, stdout, stderr = ssh.exec_command(cmd)
	return stdout.read().decode("utf-8")

def execute(cmd):
	"""
	This function executes a command

	Parameters:
		cmd (str): the command to execute

	:return: the output of the command
	"""
	return subprocess.check_output(cmd, shell=True).decode("utf-8")

def sftp_upload(sftp, local_dir, remote_dir):
	if remote_dir and not remote_dir_exists_sftp(sftp, remote_dir):
		sftp.mkdir(remote_dir)
		
	for item in os.listdir(local_dir):
		local_path = os.path.join(local_dir, item)
		remote_path = os.path.join(remote_dir, item)
		remote_path = remote_path.replace("\\", "/")
		if os.path.isfile(local_path):
			name = os.path.basename(local_path)
			try:
				sftp.put(local_path, remote_path)
				print(f"[bold green]Uploaded[/bold green] : {name}")
			except Exception as e:
				print(f"[bold red]Error[/bold red] uploading file {name}: {e}")
		elif os.path.isdir(local_path):
			name = os.path.basename(local_path)
			try:
				sftp.mkdir(remote_path)
				print(f"[bold green]Created folder[/bold green] : {name}")
			except Exception as e:
				print(f"[bold red]Error[/bold red] creating folder {remote_path}: {e}")
			sftp_upload(sftp, local_path, remote_path)
			
def remote_dir_exists_sftp(sftp, remote_dir):
	try:
		sftp.stat(remote_dir)
		return True
	except IOError:
		return False

def ftp_upload(ftp, local_dir, remote_dir):
	if remote_dir and not remote_dir_exists_ftp(ftp, remote_dir):
		ftp.mkd(remote_dir)
	
	for item in os.listdir(local_dir):
		local_path = os.path.join(local_dir, item)
		remote_path = os.path.join(remote_dir, item)
		remote_path = remote_path.replace("\\", "/")
		if os.path.isfile(local_path):
			name = os.path.basename(local_path)
			with open(local_path, 'rb') as f:
				try:
					ftp.storbinary('STOR ' + remote_path, f)
					print(f"[bold green]Uploaded[/bold green] : {name}")
				except Exception as e:
					print(f"[bold red]Error[/bold red] uploading file {name}: {e}")
		elif os.path.isdir(local_path):
			name = os.path.basename(local_path)
			try:
				ftp.mkd(remote_path)
				print(f"[bold green]Created folder[/bold green] : {name}")
			except Exception as e:
				print(f"[bold red]Error[/bold red] creating folder {remote_path}: {e}")
			ftp_upload(ftp, local_path, remote_path)

def remote_dir_exists_ftp(ftp, remote_dir):
    try:
        ftp.cwd(remote_dir)
        ftp.cwd('..') 
        return True
    except ftplib.error_perm:
        return False


def create_tmp_file_structure(localpath = ".", exclude = []):
	# Create a temporary directory
	tmp_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
	# Copy the local directory to the temporary directory
	shutil.copytree(localpath, tmp_dir)
	
	# Remove the excluded files and folders
	for item in track(exclude, description = "Removing excluded files and folders..."):
		item_path = os.path.join(tmp_dir, item)
		if os.path.isfile(item_path):
			os.remove(item_path)
		elif os.path.isdir(item_path):
			shutil.rmtree(item_path)
	
	# Return the temporary directory
	return tmp_dir


if __name__ == "__main__":
	config = load_config()
	hosts = validate_hosts(config)
	deployments = validate_deployments(config)
	arguments = parse_arguments(deployments)
	deploy_all(deployments, arguments)