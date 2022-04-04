# scheduler
dask-scheduler --host=0.0.0.0

jupyter notebook

# workers
dask-worker tcp://128.110.219.134:8786

# local
ssh -N -f -L localhost:8787:localhost:8787 -p 22 vik1497@amd223.utah.cloudlab.us

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



ssh -p 22 vik1497@amd223.utah.cloudlab.us
ssh -p 22 vik1497@amd227.utah.cloudlab.us
ssh -p 22 vik1497@amd214.utah.cloudlab.us
ssh -p 22 vik1497@amd220.utah.cloudlab.us

bash
clear

128.110.219.138
128.110.219.125
128.110.219.131