# scheduler
dask-scheduler --host=0.0.0.0

jupyter notebook

# workers
dask-worker tcp://128.110.217.26:8786 &

# local
ssh -N -f -L localhost:8787:localhost:8787 -p 22 prsridha@ms0801.utah.cloudlab.us

ssh -N -f -L localhost:8888:localhost:8888 -p 22 prsridha@ms0801.utah.cloudlab.us

# autocomplete history
cat >> ~/.inputrc <<'EOF'
"\e[A": history-search-backward
"\e[B": history-search-forward
EOF
bind -f  ~/.inputrc

# copy python package commands
zip cerebro.zip cerebro/*
scp -i cloudlab.pem 128.110.217.26:/users/prsridha/etl-wip/cerebro.zip .
unzip cerebro.zip
python3 setup.py install --user

rm -rf /mydata/coco/