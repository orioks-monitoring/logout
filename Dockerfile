FROM python:3.11
WORKDIR logout
ADD app app
ADD run.py run.py
ADD requirements.txt requirements.txt
ADD entrypoint.sh entrypoint.sh
RUN chmod 700 entrypoint.sh
RUN pip install -r requirements.txt
