FROM python

RUN apt-get update \
 && apt-get install -y \
      python-lxml \
      fontconfig \
      libcairo2 \
      libpango1.0-0 \
      libgdk-pixbuf2.0-0 \
      libffi-dev \
      shared-mime-info \
      unzip \
 && apt-get autoremove \
 && apt-get clean

WORKDIR /opt

ENV WEASYPRINT_VERSION 0.40

ADD https://noto-website.storage.googleapis.com/pkgs/NotoSerifCJKjp-hinted.zip .
RUN unzip -d noto NotoSerifCJKjp-hinted.zip \
 && mkdir -p /usr/share/fonts/opentype \
 && mv -fv noto /usr/share/fonts/opentype/noto \
 && rm -rfv NotoSerifCJKjp-hinted.zip \
 && fc-cache -fv

RUN git clone https://747790320b96074cf5a35551eef6257eac25e74a:x-oauth-basic@github.com/henpin/myflask.git \
 && cd myflask/md_pdf \
 && pip install -r requirements.txt

CMD python myflask/md_pdf/app.py
