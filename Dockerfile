FROM ubuntu:24.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      git build-essential autoconf automake libtool \
      pkg-config libxml2-dev libxslt1-dev ca-certificates \
      less iputils-ping iproute2 net-tools jq jc \
      lua5.3 liblua5.3-dev

WORKDIR /opt

# Build and install libfaux (required by klish v3)
RUN git clone --branch 2.2.1 https://src.libcode.org/pkun/faux.git && \
    cd faux && \
    ./autogen.sh && \
    ./configure --prefix=/usr && \
    make -j"$(nproc)" && \
    make install

# Build and install klish
RUN git clone --branch 3.2.0 https://src.libcode.org/pkun/klish.git && \
    cd klish && \
    ./autogen.sh && \
    ./configure --prefix=/usr --with-libxml2=/usr --with-lua && \
    make -j"$(nproc)" && \
    make install

WORKDIR /opt/netlab-cli

COPY klish/xml ./xml
COPY klish/scripts ./scripts

RUN mkdir -p /opt/netlab-cli/data && \
    chmod +x ./scripts/*.sh

# Put XML where klishd (libxml2 DB) expects it for root: ~/.klish/*.xml
RUN mkdir -p /root/.klish && \
    cp ./xml/*.xml /root/.klish/

# Klish daemon/client configs
COPY klish/config/klishd.conf /etc/klish/klishd.conf
COPY klish/config/klish.conf  /etc/klish/klish.conf

COPY klish/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
