FROM jonaseck/rpi-raspbian-libcec-py

RUN sed -i '/jessie-updates/d' /etc/apt/sources.list  # Now archived
RUN printf "deb http://archive.debian.org/debian/ jessie main\ndeb-src http://archive.debian.org/debian/ jessie main\ndeb http://security.debi>

RUN apt-get update \
 && apt-get install -qqy libxrandr2 lirc liblircclient-dev \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /usr/src/app

CMD ["python", "bridge.py"]
