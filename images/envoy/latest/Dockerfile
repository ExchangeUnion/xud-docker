FROM envoyproxy/envoy:v1.14.1
COPY envoy.yaml /etc/envoy/envoy.yaml
CMD ["envoy", "-c", "/etc/envoy/envoy.yaml", "-l", "trace"]
