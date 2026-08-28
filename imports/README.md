# Authorized scanner imports

Place approved Nmap XML files in this directory when running the local Compose
stack. CSOS mounts it read-only at `/data/imports`; the Nmap connector refuses
paths outside that directory and enforces the configured import-size limit.

Only import scan output produced under the customer's authorized scanning
process. Imported files are evidence inputs and are not executed by CSOS.
