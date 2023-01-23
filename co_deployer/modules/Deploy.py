import os
import sys
import shutil
import tempfile
import uuid
from rich import print

if __package__ is None or __package__ == '':
	# uses current directory visibility
	import modules.Ftp
	import modules.Ssh
	import modules.Sftp
	import modules.Cmd
else:
	# uses current package visibility
	from .Ftp import Ftp
	from .Ssh import Ssh
	from .Sftp import Sftp
	from .Cmd import Cmd

class Deploy:
	deployments = None
	ftp = None
	sftp = None
	ssh = None
	cmd = None

	def __init__(self, deployments):
		self.deployments = deployments
		self.cmd = Cmd()	
	def __del__(self):
		self._close_connections()
		
	def deploy_all(self):
		for d in self.deployments:
			self._deploy(d)
	
		self._close_connections()
		
	def _deploy(self, deployment):
		# deployment variables
		name = deployment.get("name")
		protocol = deployment.get("protocol")
		local_path = deployment.get("local_path", ".")
		remote_path = deployment.get("remote_path", "/")
		exclude = deployment.get("exclude", [])
		cmd = deployment.get("cmd", "") or {}
		cmd_shell = cmd.get("cmd")
		cmd_ssh = cmd.get("ssh")
		cmd_before = cmd.get("before")
		cmd_after = cmd.get("after")
		cmd_ssh_before = cmd.get("ssh_before")
		cmd_ssh_after = cmd.get("ssh_after")

		# host variables
		host = deployment.get("host")
		ftp = host.get("ftp")
		sftp = host.get("sftp")
		ssh = host.get("ssh")

		# create temporary directory
		tmp_dir = self._create_tmp_directory(local_path, exclude)

		# reset connections
		self._close_connections()

		# create connections	
		if cmd_ssh or cmd_ssh_before or cmd_ssh_after:
			self.ssh = Ssh(ssh)
		
		if protocol == "sftp":
			self.sftp = Sftp(sftp)

		if protocol == "ftp":
			self.ftp = Ftp(ftp)
		
		# execute base commands
		if cmd_shell:
			result = self.cmd.execute(cmd_shell)
			print(f"[bold cyan][CMD][/bold cyan] : {result}")
		
		if cmd_ssh:
			result = self.ssh.execute(cmd_ssh)
			print(f"[bold cyan][SSH][/bold cyan] : {result}")

		# execute the commands before the deployment
		if cmd_before:
			result = self.cmd.execute(cmd_before)
			print(f"[bold cyan][CMD][/bold cyan] : {result}")

		if cmd_ssh_before:
			result = self.ssh.execute(cmd_ssh_before)
			print(f"[bold cyan][SSH][/bold cyan] : {result}")

		# deploy
		if protocol == "sftp":
			print("[bold cyan][SFTP][/bold cyan] Deploying[FTP]...")
			self.sftp.upload(tmp_dir, remote_path)
			print("[bold cyan][SFTP][/bold cyan] [bold green]Successfully[/bold green] deployed")
		
		if protocol == "ftp":
			print("[bold cyan][FTP][/bold cyan] Deploying...")
			self.ftp.upload(tmp_dir, remote_path)
			print("[bold cyan][FTP][/bold cyan] [bold green]Successfully[/bold green] deployed")
		
		# execute the commands after the deployment
		if cmd_after:
			result = self.cmd.execute(cmd_after)
			print(f"[bold cyan][CMD][/bold cyan] : {result}")

		if cmd_ssh_after:
			result = self.cmd.execute(cmd_ssh_after)
			print(f"[bold cyan][SSH][/bold cyan] : {result}")
	
		# delete the remote directory
		self._delete_tmp_directory(tmp_dir)
	
	def _create_tmp_directory(self, local_path, exclude):
		# create a temporary directory
		tmp_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
		
		# copy the local directory to the temporary directory and exclude files
		try:
			shutil.copytree(local_path, tmp_dir)
			for item in exclude:
				item_path = os.path.join(tmp_dir, item)
				if os.path.isfile(item_path):
					os.remove(item_path)
				elif os.path.isdir(item_path):
					shutil.rmtree(item_path)			
		except Exception as e:
			print(f"[bold red]Error[/bold red] creating temporary directory: {e}")
			sys.exit(1)
		
		return tmp_dir
	
	def _delete_tmp_directory(self, tmp_dir):
		try:
			shutil.rmtree(tmp_dir)
		except Exception as e:
			print(f"[bold red]Error[/bold red] deleting temporary directory: {e}")
			sys.exit(1)

	def _close_connections(self):
		if self.ftp:
			self.ftp.disconnect()
		if self.sftp:
			self.sftp.disconnect()
		if self.ssh:
			self.ssh.disconnect()
