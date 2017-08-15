FROM jonaseck/rpi-raspbian-libcec-py

RUN apt-get update \
 && apt-get install -qqy libxrandr2 liblircclient-dev \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY . /usr/src/app

CMD ["python", "bridge.py"]
