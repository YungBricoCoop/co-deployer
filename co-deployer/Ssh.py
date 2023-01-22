import sys
import paramiko
from rich import print

class Ssh:
	config = None
	ssh = None

	def __init__(self, config):
		self.config = config
		self.ssh = None

	def __del__(self):
		if self.ssh: self.disconnect()

	
	def _connect(self):
		"""
		Connects to the ssh server
		"""
		config = self.config
		try:
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(hostname=config.get("hostname"), username=config.get("username"), password=config.get("password"), port=config.get("port"))
			self.ssh = ssh
		except Exception as e:
			print("[bold red]SSH Error[/bold red] :", e)
			self.ssh = None
			sys.exit(1)
	
	def disconnect(self):
		"""
		Disconnects from the SSH server
		"""
		self.ssh.close()
		self.ssh = None
	
	def execute(self, cmd):
		"""
		Executes a command over SSH

		Parameters:
			cmd (str): the command to execute

		Returns: the output of the command
		"""
		stdin, stdout, stderr = self.ssh.exec_command(cmd)
		return stdout.read().decode("utf-8")