import os
import pandas as pd
from constants import DOWNLOAD_FROM_URL, DOWNLOAD_FROM_SERVER

class etl:
    def __init__(self, backend, params, row_preprocessing_routine, dataset_info):
        self.backend = backend
        self.params = params
        self.dataset_info = dataset_info
        self.row_routine = row_preprocessing_routine

    def load_data(self, frac=1):
        pandas_df = pd.DataFrame(self.params.metadata_path)
        _df = dd.from_pandas(pandas_df, npartitions=self.backend.num_workers)
        self.metadata_df = _df.sample(frac=frac)

    def shuffle_shard_data(self):
        shuffled_df = self.metadata_df.sample(frac=1)
        self.sharded_df = shuffled_df.repartition(npartitions=self.backend.num_workers)
    
    def download_file(self, filepath):
        if self.params.download_type == DOWNLOAD_FROM_SERVER:
            from_path = os.join(self.params.from_root_path, filepath)
            to_path = os.join(self.params.to_root_path, filepath)
            
            to_path_dir ="/".join(to_path.split("/")[:-1])
            Path(to_path_dir).mkdir(parents=True, exist_ok=True)
            
            if not os.path.isfile(to_path):
                self.connection.get(from_path, to_path)

        elif self.params.download_type == DOWNLOAD_FROM_URL:
            # import urllib.request
            pass

        else:
            # error
            pass
    
    def process_row(self, row):
        for i in range(len(self.dataset_info.features)):
            feature_name = self.dataset_info.features[i]
            if self.dataset_info.is_feature_download[i]:
                self.download_file(row[feature_name])
        return self.row_routine(row)

    def preprocess_data(self):
        self.processed_df = self.sharded_df.map_partitions(
            lambda part: part.apply(
                lambda row: self.process_row(row)
                ), meta=('processed_df', object)
            )