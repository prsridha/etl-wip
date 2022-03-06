from cerebro.dask_backend import DaskBackend
from cerebro.params import Params
from cerebro.etl import etl
import cerebro.constants as constants

def prepare_data():
    data = None
    with open("/mydata/coco/annotations/captions_val2014.json") as f:
        data = json.load(f)
    feature_names = ["id", "file_name", "height", "width", "caption", "date_captured"]
    dataset = {
        'id': [],
        'file_name': [],
        'height': [],
        'width': [],
        'captions': [],
        'date_captured': [] 
    }

    annotations = {}
    annotations_list = data['annotations']
    for i in annotations_list:
        if not i["image_id"] in annotations:
            annotations[i["image_id"]] = []
        annotations[i["image_id"]].append(i["caption"])

    for i in range(len(data['images'])):
        dataset['id'].append(data["images"][i]['id'])
        dataset['file_name'].append(data["images"][i]['file_name'])
        dataset['height'].append(data["images"][i]['height'])
        dataset['width'].append(data["images"][i]['width'])
        dataset['captions'].append(annotations[data["images"][i]['id']])
        dataset['date_captured'].append(data["images"][i]['date_captured'])

        dataset.to_csv("/mydata/coco/annotations/captions_val2014_modified.json", index=False)

def row_preprocessing_routine(row):
    pass

def main():
    prepare_data()

    metadata_path = "/mydata/coco/annotations/captions_val2014_modified.json"
    from_root_path = "/mydata/coco/images/val2014/"
    to_root_path = "/mydata/coco/val2014/"
    output_path = ""
    requirements_path = ""
    download_type = [constants.No_DOWNLOAD, constants.DOWNLOAD_FROM_SERVER, constants.No_DOWNLOAD, constants.No_DOWNLOAD, constants.No_DOWNLOAD, constants.No_DOWNLOAD]
    username = "prsridha"
    host = "128.110.217.26"
    pem_path = "/users/prsridha/cloudlab.pem"

    dsk_bknd = DaskBackend("0.0.0.0:8786")
    params = Params(metadata_path, from_root_path, to_root_path,
        output_path, requirements_path, username, host, pem_path,
        download_type)
    
    etl = etl(backend, params, )

if __name__ == '__main__':
    main()