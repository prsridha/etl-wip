import os
import pandas as pd
from pathlib import Path
import cerebro.constants as constants
import dask.dataframe as dd
from dask.distributed import Client

class etl:
    def __init__(self, backend, params, row_preprocessing_routine, dataset_info):
        self.metadata_df = None
        self.backend = backend
        self.params = params
        self.dataset_info = dataset_info
        self.row_routine = row_preprocessing_routine
        self.params.create_connection()

    def load_data(self, frac=1):
        pandas_df = pd.read_csv(self.params.metadata_path)
        _df = dd.from_pandas(pandas_df, npartitions=2) #self.backend.num_workers)
        self.metadata_df = _df.sample(frac=frac)

    def shuffle_shard_data(self):
        shuffled_df = self.metadata_df.sample(frac=1)
        self.sharded_df = shuffled_df.repartition(npartitions=2) #self.backend.num_workers)

    def download_file(self, filepath):
        if self.params.download_type == constants.DOWNLOAD_FROM_SERVER:
            from_path = os.path.join(self.params.from_root_path, filepath)
            to_path = os.path.join(self.params.to_root_path, filepath)
            
            to_path_dir ="/".join(to_path.split("/")[:-1])
            Path(to_path_dir).mkdir(parents=True, exist_ok=True)
            
            if not os.path.isfile(to_path):
                self.params.connection.get(from_path, to_path)
                print("Pulled from {} to {}".format(from_path, to_path))

        elif self.params.download_type == constants.DOWNLOAD_FROM_URL:
            # import urllib.request
            pass

        else:
            # error
            pass
    
    def process_row(self, row, kwargs):
        for i in range(len(self.dataset_info.features)):
            feature_name = self.dataset_info.features[i]
            if self.dataset_info.is_feature_download[i]:
                self.download_file(row[feature_name])
        return self.row_routine(row, kwargs)

    def preprocess_data(self, **kwargs):
        tensor = self.sharded_df.map_partitions(
            lambda part: part.apply(self.process_row, args=(kwargs,), axis=1),
            meta=('tensor', object)
        )
        return tensor

    def clean_up(self):
        # broadcast fabric connection close to each worker.
        pass