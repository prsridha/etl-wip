# scheduler
dask-scheduler --host=0.0.0.0

jupyter notebook

# workers
dask-worker tcp://128.110.217.26:8786 &

# local
ssh -N -f -L localhost:8787:localhost:8787 -p 22 prsridha@ms0801.utah.cloudlab.us

ssh -N -f -L localhost:8888:localhost:8888 -p 22 prsridha@ms0801.utah.cloudlab.us