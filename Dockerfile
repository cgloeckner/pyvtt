FROM python:3

WORKDIR /opt/pyvtt

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "./vtt.py" ]
