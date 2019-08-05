ARG PYTHON_VERSION

FROM python:$PYTHON_VERSION
RUN apk add --no-cache bash
COPY --from=xud-simnet /root/xud-simnet/raiden-wd/venv/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY entrypoint.sh onboarder.py /opt/
WORKDIR /opt
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 5001
