# scheduler
dask-scheduler --host=0.0.0.0

jupyter notebook

# workers
dask-worker tcp://128.110.218.13:8786

# local
ssh -N -f -L localhost:8787:localhost:8787 -p 22 prsridha@ms0801.utah.cloudlab.us

ssh -N -f -L localhost:9999:localhost:8888 -p 22 vik1497@ms1319.utah.cloudlab.us

# autocomplete history
cat >> ~/.inputrc <<'EOF'
"\e[A": history-search-backward
"\e[B": history-search-forward
EOF
bind -f  ~/.inputrc

# commands to copy python package
# manually copy setup.py and requirements.txt 
zip cerebro.zip cerebro/*
scp -i cloudlab.pem 128.110.218.13:/users/vik1497/etl-wip/cerebro.zip .
unzip cerebro.zip
python3 setup.py install --user

rm -rf /mydata/coco/



ssh -p 22 vik1497@ms1319.utah.cloudlab.us
ssh -p 22 vik1497@ms1344.utah.cloudlab.us
ssh -p 22 vik1497@ms1338.utah.cloudlab.us
ssh -p 22 vik1497@ms1323.utah.cloudlab.us

/bin/bash   
clear