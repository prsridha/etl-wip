import dask
from dask.distributed import Client

class DaskBackend():
    def __init__(self, scheduler_address="0.0.0.0:8786", dask_cluster=None, logs_path=None, num_workers=None):        
        self.client = Client(scheduler_address)
        # get the dask dashboard link
        print("Client dashboard: ", self.client.dashboard_link)
        # get the number of workers
        self.num_workers = len(self.client.scheduler_info()['workers'])
        print("Number of workers:", self.num_workers)