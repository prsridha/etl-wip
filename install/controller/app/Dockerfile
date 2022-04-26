FROM python:3.7

# RUN apt-get update && apt-get install -y curl
# RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 > get_helm.sh
# RUN chmod 700 get_helm.sh
# RUN ./get_helm.sh

RUN git clone https://github.com/prsridha/etl-wip.git
WORKDIR etl-wip
RUN pip install -r requirements.txt
RUN python3 setup.py install --user 

ENTRYPOINT ["tail", "-f", "/dev/null"]