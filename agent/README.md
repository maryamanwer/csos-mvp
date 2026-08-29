# CSOS Endpoint Reporter

This optional CSOS component sends read-only endpoint observations from Linux,
Windows and macOS systems. It uses the Python standard library and reports a
bounded inventory containing system identity, interfaces, listeners and,
optionally, installed packages. It never changes endpoint configuration.

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

For periodic reporting, use the operating system's service manager with
`--daemon --interval 3600`. Production endpoints should trust the organization's
internal CA. The `--insecure` option is limited to temporary lab validation.

The issued key is write-only and limited to endpoint ingestion. It cannot read
CSOS data or call MCP tools. Revoke it from the portal when a source is retired.
