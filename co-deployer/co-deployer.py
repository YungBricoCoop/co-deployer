# imports
import os
import sys
import json
import shutil
import uuid
import subprocess
import tempfile
import ftplib
from argparse import ArgumentParser

# modules
import Config
import Ftp
import Sftp
import Ssh
import Cmd


def deploy(deployment):

	# deployment variables
	name = deployment.get("name")
	protocol = deployment.get("protocol")
	local_path = deployment.get("local_path", ".")
	remote_path = deployment.get("remote_path", "/")
	exclude = deployment.get("exclude", [])
	cmd = deployment.get("cmd", "") or {}

	# host variables
	host = deployment.get("host")
	
	print(f"[bold green]Deploying[/bold green] : {name}")

	# create temporary directory
	tmp_dir = create_tmp_file_structure(local_path, exclude)

	# build the protocol configs
	ssh = build_protocol_dict(host, "ssh")
	ftp = build_protocol_dict(host, "ftp")
	sftp = build_protocol_dict(host, "sftp")

	# opened connections
	opened_connections =  {
		"ssh": False,
		"ftp": False,
		"sftp": False
	}

	# create connections	
	if cmd.get("ssh_before") or cmd.get("ssh_after"):
		ssh = ssh_connect(ssh)
		opened_connections["ssh"] = ssh
	
	if protocol == "sftp":
		sftp = sftp_connect(sftp)
		opened_connections["sftp"] = sftp

	if protocol == "ftp":
		ftp = ftp_connect(ftp)
		opened_connections["ftp"] = ftp
	
	# execute the commands before the deployment
	if cmd.get("before"):
		result = execute(cmd.get("before"))
		print(f"[bold cyan][BEFORE CMD OUT][/bold cyan] : {result}")
	
	if cmd.get("ssh_before"):
		result = ssh_execute(ssh, cmd.get("ssh_before"))
		print(f"[bold cyan][BEFORE CMD OUT][/bold cyan] : {result}")
	
	# deploy
	if protocol == "sftp":
		print("[bold cyan][SFTP][/bold cyan] Deploying[FTP]...")
		sftp_upload(sftp, tmp_dir, remote_path)
		print("[bold green][SFTP]Successfully deployed[/bold green]")
	
	if protocol == "ftp":
		print("[bold cyan][FTP][/bold cyan] Deploying...")
		ftp_upload(ftp, tmp_dir, remote_path)
		print("[bold cyan][FTP][/bold cyan] Successfully deployed")
	
	# execute the commands after the deployment
	if cmd.get("after"):
		result = execute(cmd.get("after"))
		print(f"[bold cyan][AFTER CMD OUT][/bold cyan] : {result}")

	if cmd.get("ssh_after"):
		result = ssh_execute(ssh, cmd.get("ssh_after"))
		print(f"[bold cyan][AFTER SSH CMD OUT][/bold cyan] : {result}")
	
	close_connections(opened_connections)
	remove_tmp_dir(tmp_dir)

def create_tmp_file_structure(localpath = ".", exclude = []):
	# create a temporary directory
	tmp_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
	
	# copy the local directory to the temporary directory
	try:
		shutil.copytree(localpath, tmp_dir)
	except Exception as e:
		print(f"[bold red]Error[/bold red] creating temporary directory: {e}")
		sys.exit(1)
	
	# remove the excluded files and folders
	for item in track(exclude, description = "Removing excluded files and folders..."):
		item_path = os.path.join(tmp_dir, item)
		if os.path.isfile(item_path):
			os.remove(item_path)
		elif os.path.isdir(item_path):
			shutil.rmtree(item_path)
	
	# return the temporary directory
	return tmp_dir

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

if __name__ == "__main__":
	# create workers
	config = Config.Config()
	to_deploy = config.get_arguments()
	for d in to_deploy: 
		deploy(d)