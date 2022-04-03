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
        _df = dd.from_pandas(pandas_df, npartitions=self.backend.num_workers) #self.backend.num_workers)
        self.metadata_df = _df.sample(frac=frac)

    def shuffle_shard_data(self):
        shuffled_df = self.metadata_df.sample(frac=1)
        self.sharded_df = shuffled_df.repartition(npartitions=self.backend.num_workers) #self.backend.num_workers)

    def process_row(self, row, kwargs):
        for i in range(len(self.dataset_info.features)):
            feature_name = self.dataset_info.features[i]
            if self.dataset_info.is_feature_download[i]:
                self.download_file(row[feature_name])
        return self.row_routine(row, kwargs)

    def preprocess_data(self, **kwargs):

        def download_file(filepath, params):
            # return filepath
            if params.download_type == constants.DOWNLOAD_FROM_SERVER:
                from_path = os.path.join(params.from_root_path, filepath)
                to_path = os.path.join(params.to_root_path, filepath)
                
                to_path_dir ="/".join(to_path.split("/")[:-1])
                Path(to_path_dir).mkdir(parents=True, exist_ok=True)
                
                if not os.path.isfile(to_path):
                    params.connection.get(from_path, to_path)
                    print("Pulled from {} to {}".format(from_path, to_path))

            elif params.download_type == constants.DOWNLOAD_FROM_URL:
                # import urllib.request
                pass

            else:
                # error
                pass
                
        def process_row(row, dataset_info, params, row_routine, kwargs):
            for i in range(len(dataset_info.features)):
                feature_name = dataset_info.features[i]
                if dataset_info.is_feature_download[i]:
                    download_file(row[feature_name], params)
            return row_routine(row, params.to_root_path, kwargs)

        data_info = self.dataset_info
        params = self.params
        row_routine = self.row_routine
        feats = self.dataset_info.features
        transformed_data = self.sharded_df.map_partitions(
            lambda part: part.apply(process_row, args=(data_info, params, row_routine, kwargs,), axis=1),
            meta=('transformed_data', object)
        )
        print(transformed_data.compute())
        return transformed_data

    def clean_up(self):
        # broadcast fabric connection close to each worker.
        pass