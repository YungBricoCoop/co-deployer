# modules
if __package__ is None or __package__ == '':
	# uses current directory visibility
	from modules.Config import Config
	from modules.Deploy import Deploy
else:
	# uses current package visibility
	from .modules.Config import Config
	from .modules.Deploy import Deploy


def main():
	# load and build config
	config = Config()
	# get the deployment list from the given arguments
	to_deploy = config.get_arguments()
	# create the worker
	deploy = Deploy(to_deploy)
	# deploy the list
	deploy.deploy_all()