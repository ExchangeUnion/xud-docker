ARG PYTHON_VERSION

FROM python:$PYTHON_VERSION
RUN apk add --no-cache bash curl supervisor
COPY --from=xud-simnet /root/xud-simnet/raiden-wd/venv/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY entrypoint.sh onboarder.py /opt/
COPY supervisord.conf /etc/supervisor/conf.d/
WORKDIR /opt
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EXPOSE 5001
