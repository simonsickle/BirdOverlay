FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

HEALTHCHECK CMD curl --fail http://localhost:8000 || exit 1  

CMD [ "python", "./birdoverlay.py" ]