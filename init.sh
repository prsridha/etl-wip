# Run the following on the scheduler
# first copy cloudlab.pem to the scheduler
chmod 400 cloudlab.pem
ssh-keygen -p -N "" -f ./cloudlab.pem
# enter the passphrase

# Install pip and dask
apt update
apt install python3-pip
pip install "dask[complete]"
pip install jupyter-server-proxy

#
echo "export PATH=$PATH:$HOME/.local/bin" >> ~/.bashrc

# copy .pem file to each of the workers
scp -i cloudlab.pem cloudlab.pem <workerip>:/users/<username>

# Run the following on each of the workers
apt update
apt install python3-pip
pip install fabric
chmod 400 cloudlab.pem