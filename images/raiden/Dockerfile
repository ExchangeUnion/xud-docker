ARG version=0.100.3
FROM raidennetwork/raiden:v${version}
COPY entrypoint.sh a.py onboarder.py /
ENTRYPOINT [ "./entrypoint.sh" ]