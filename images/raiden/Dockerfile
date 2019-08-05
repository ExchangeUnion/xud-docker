ARG VERSION

FROM raidennetwork/raiden:v$VERSION
COPY entrypoint.sh checksum.py onboarder.py configWriter.py /
ENTRYPOINT [ "./entrypoint.sh" ]
