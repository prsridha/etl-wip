class DatasetInfo:
    def __init__(self, features, input_features, output_features, dtypes, is_feature_download):
        self.features = features
        self.input_features = input_features
        self.output_features = output_features
        self.dtypes = dtypes
        self.is_feature_download = is_feature_download