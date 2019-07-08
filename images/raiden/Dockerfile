ARG version=0.100.3
FROM raidennetwork/raiden:v${version}
COPY entrypoint.sh checksum.py onboarder.py configWriter.py /
ENTRYPOINT [ "./entrypoint.sh" ]
