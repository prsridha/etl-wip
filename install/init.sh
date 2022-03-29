# Run the following on the scheduler
# first copy cloudlab.pem to the scheduler
chmod 400 cloudlab.pem
ssh-keygen -p -N "" -f ./cloudlab.pem
# enter the passphrase

# Install pip and dask
sudo apt update
sudo apt install -y python3-pip
pip install "dask[complete]"
pip install jupyter-server-proxy
pip install notebook
pip install spacy
# dask-scheduler breaks without this
pip install click==6.6

sudo chmod 777 -R /mydata/
#
echo "export PATH=$PATH:$HOME/.local/bin" >> ~/.bashrc
source ~/.bashrc

# copy .pem file to each of the workers
#scp -i cloudlab.pem cloudlab.pem <workerip>:/users/<username>

# Run the following on each of the workers
sudo apt update
sudo apt install -y python3-pip
pip install fabric
pip install spacy
# dask-scheduler breaks without this
pip install click==6.6
#chmod 400 cloudlab.pem
sudo chmod 777 -R /mydata/

cat >> ~/.inputrc <<'EOF'
"\e[A": history-search-backward
"\e[B": history-search-forward
EOF
bind -f  ~/.inputrc