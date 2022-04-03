import dask
from dask.distributed import Client

class DaskBackend():
    def __init__(self, scheduler_address="0.0.0.0:8786", dask_cluster=None, logs_path=None, num_workers=None):        
        self.client = Client(scheduler_address)
        # get the dask dashboard link
        print("Client dashboard: ", self.client.dashboard_link)
        # get the number of workers
        if num_workers == None:
            self.num_workers = len(self.client.scheduler_info()['workers'])
        else:
            self.num_workers = num_workers
        print("Number of workers:", self.num_workers)
    
    def show_results(self, res):
        print(self.client)
        print(self.client.compute(res))