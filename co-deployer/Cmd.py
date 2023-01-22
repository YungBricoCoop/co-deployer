import subprocess

class Cmd:
	def execute(self, cmd):
		try:
			result = subprocess.check_output(cmd, shell=True).decode("utf-8")
			return result
		except Exception as e:
			print("[bold red]Error while executing command[/bold red] :", e)
			return ""