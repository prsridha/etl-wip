dask-scheduler --host=0.0.0.0

k get svc cerebro-controller-....

dask-worker tcp://<>:8786





cd /data/cerebro_data_storage
wget http://images.cocodataset.org/zips/val2014.zip
wget http://images.cocodataset.org/annotations/annotations_trainval2014.zip
mkdir coco
unzip -d ./coco/ annotations_trainval2014.zip
unzip -d ./coco/ val2014.zip