# CSOS Endpoint Agent

The endpoint agent is a read-only, standard-library Python collector for Linux,
Windows, and macOS. It reports hostname, OS, hardware identity, interfaces,
listening ports, and an optional bounded package inventory to CSOS. It does not
make changes to the endpoint.

## Enrolment

1. In CSOS, open **Data Sources → Agent & Syslog Keys** and create an
   `agent`-scoped key.
2. Copy `csos_agent.py` to the endpoint using the organization's approved
   software-distribution process.
3. Put the server URL and key in the service environment, keeping the key out
   of command history and process listings.

```bash
export CSOS_SERVER=https://csos.internal
export CSOS_API_KEY=csos_replace_with_issued_key
python3 csos_agent.py --dry-run
python3 csos_agent.py --asset-type server --criticality high
```

For continuous collection, run it through the operating system's service
manager with `--daemon --interval 3600`. Use an internal CA trusted by the host.
`--insecure` exists for temporary testing only and must not be used in
production.

The API key is write-only and scope-limited: it can submit endpoint inventory
but cannot read CSOS data or invoke MCP tools. Revoke the key in the portal when
the source is retired.
