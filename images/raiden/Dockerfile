ARG version
FROM raidennetwork/raiden:v$version
COPY entrypoint.sh checksum.py onboarder.py configWriter.py /
ENTRYPOINT [ "./entrypoint.sh" ]
