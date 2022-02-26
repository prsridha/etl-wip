import dask.dataframe as dd
import pandas as pd
import numpy as np
import dask.array as da
from dask.distributed import Client
import glob
import csv
import os.path
from pathlib import Path
from fabric import Connection, Config


def create_metadata():
    mnist_data_path = "data/trainingSet/trainingSet/"
    mnist_metadata_out_path = mnist_data_path + "metadata.csv"
    data_rows = []
    num_labels = 10
    for i in range(num_labels):
        curr_label_path = mnist_data_path + str(i) + "/"
        jpgFilenamesList =  glob.glob(curr_label_path + '*.jpg')
        rows = [[str(fname), i] for fname in jpgFilenamesList]
        data_rows.extend(rows)
        # print(curr_label_path, str(len(jpgFilenamesList)))
    with open(mnist_metadata_out_path, 'w') as f: 
        write = csv.writer(f)
        write.writerows(data_rows)
        

def push():
    user = "prsridha"
    host = "ms0903.utah.cloudlab.us"
    pem_path = "./cloudlab.pem"
    from_path = "/mydata/images/ucsd-geisel-1.jpg"
    to_path = "/mydata/images"

    connect_kwargs = {"key_filename": pem_path}
    conn = Connection(host, user=user, connect_kwargs=connect_kwargs)
    conn.sudo("mkdir -p {}".format(to_path))
    result = conn.put(from_path, remote=to_path)
    print("Uploaded {0.local} to {0.remote}".format(result))


def pull():
    user = "prsridha"
    host = "ms0921.utah.cloudlab.us"
    pem_path = "./cloudlab.pem"
    from_path = "/users/prsridha/data/trainingSet/trainingSet/0/img_19483.jpg"
    to_path = "/users/prsridha/data/0/img_19483.jpg"

    connect_kwargs = {"key_filename": pem_path}
    conn = Connection(host, user=user, connect_kwargs=connect_kwargs)
    conn.sudo("mkdir -p {}".format(to_path))
    result = conn.get(from_path, to_path)
    print("Pulled from {0.remote} to {0.local}".format(result))


def pull1():
    user = "prsridha"
    host = "ms0921.utah.cloudlab.us"
    pem_path = "./cloudlab.pem"
    connect_kwargs = {"key_filename": pem_path}
    conn = Connection(host, user=user, connect_kwargs=connect_kwargs)

    worker_path_list = "/users/prsridha/worker2_list.txt"
    conn.get(worker_path_list)
    paths = []
    with open(worker_path_list, "r") as f:
        paths = f.read().split("\n")

    for i in paths:
        from_path = os.path.join("/users/prsridha", i)
        to_path = os.path.join("/users/prsridha", i)

        to_path_dir = "/".join(to_path.split("/")[:-1])
        Path(to_path_dir).mkdir(parents=True, exist_ok=True)
        result = conn.get(from_path, to_path)
        print("Pulled from {0.remote} to {0.local}".format(result))


def main():
    pull1()

if __name__ == '__main__':
    client = Client()
    main()