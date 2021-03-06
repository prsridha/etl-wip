from fabric import Connection

class Params:
    def __init__(self, metadata_path, from_root_path, to_root_path, output_path, requirements_path, username, host, pem_path, download_type):
        # no need to get from_url and to_path from the user as paths are collected from tabular metadata file.
        # requirements_path is the path to the requirements.txt containing user-defined row preprocessing python
        # dependencies to be installed on all workers.
        self.metadata_path = metadata_path
        self.username = username
        self.host = host
        self.pem_path = pem_path
        self.from_root_path = from_root_path
        self.to_root_path = to_root_path
        self.output_path = output_path
        self.requirements_path = requirements_path
        self.download_type = download_type

    def create_connection(self):
        connect_kwargs = {"key_filename": self.pem_path}
        self.connection = Connection(self.host, user=self.username, connect_kwargs=connect_kwargs)