FROM python:3.10-slim

RUN useradd -d /app -m vtt

USER vtt 
WORKDIR /app/
RUN python3 -m venv /app
ENV PATH="/app/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "./main.py", "--appname=prod", "--prefdir=/opt/pyvtt", "--no-logs" ]
