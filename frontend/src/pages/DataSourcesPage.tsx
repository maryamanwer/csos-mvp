import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControlLabel, Grid, LinearProgress, MenuItem,
  Paper, Stack, Switch, Tab, Table, TableBody, TableCell, TableHead, TableRow,
  Tabs, TextField, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  createConnectorConfig, createIngestApiKey, deleteConnectorConfig,
  listConnectorConfigs, listConnectorTypes, listIngestApiKeys,
  recentConnectorRuns, revokeIngestApiKey, runConnectorConfig,
  testConnectorConfig,
} from "@/services/api";
import {
  ConnectorConfig, ConnectorField, ConnectorRun, ConnectorType, IngestApiKey,
} from "@/types";
import { useAuth } from "@/contexts/AuthContext";

const statusColor = (status?: string): "default" | "success" | "warning" | "error" => {
  if (status === "success") return "success";
  if (status === "partial" || status === "running") return "warning";
  if (status === "failed") return "error";
  return "default";
};

export const DataSourcesPage = () => {
  const { user } = useAuth();
  const canManageIngestKeys = user?.role === "Admin";
  const [tab, setTab] = useState(0);
  const [types, setTypes] = useState<ConnectorType[]>([]);
  const [configs, setConfigs] = useState<ConnectorConfig[]>([]);
  const [runs, setRuns] = useState<ConnectorRun[]>([]);
  const [keys, setKeys] = useState<IngestApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ kind: "success" | "error" | "info"; text: string } | null>(null);
  const [dialog, setDialog] = useState(false);
  const [selectedKey, setSelectedKey] = useState("");
  const [name, setName] = useState("");
  const [schedule, setSchedule] = useState("");
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [keyDialog, setKeyDialog] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [keyScope, setKeyScope] = useState<"agent" | "syslog">("agent");
  const [issuedKey, setIssuedKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [typeResponse, configResponse, runResponse, keyResponse] = await Promise.all([
        listConnectorTypes(), listConnectorConfigs(), recentConnectorRuns(),
        canManageIngestKeys ? listIngestApiKeys() : Promise.resolve({ data: [] as IngestApiKey[] }),
      ]);
      setTypes(typeResponse.data);
      setConfigs(configResponse.data);
      setRuns(runResponse.data);
      setKeys(keyResponse.data);
    } catch {
      setMessage({ kind: "error", text: "Collection-layer data could not be loaded." });
    } finally {
      setLoading(false);
    }
  }, [canManageIngestKeys]);

  useEffect(() => { void load(); }, [load]);

  const selectedType = useMemo(
    () => types.find((item) => item.key === selectedKey), [selectedKey, types],
  );

  const chooseType = (key: string) => {
    const definition = types.find((item) => item.key === key);
    setSelectedKey(key);
    setValues(Object.fromEntries(
      (definition?.config_fields ?? [])
        .filter((field) => field.default !== null && field.default !== undefined)
        .map((field) => [field.name, field.default]),
    ));
  };

  const renderField = (field: ConnectorField) => {
    const value = values[field.name] ?? "";
    if (field.type === "boolean") {
      return <FormControlLabel key={field.name} label={field.label} control={
        <Switch checked={Boolean(value)} onChange={(_, checked) => setValues({ ...values, [field.name]: checked })} />
      } />;
    }
    return <TextField
      key={field.name}
      fullWidth
      select={field.type === "select"}
      multiline={field.type === "textarea"}
      minRows={field.type === "textarea" ? 3 : undefined}
      type={field.secret ? "password" : field.type === "number" ? "number" : "text"}
      label={field.label}
      required={field.required}
      value={value as string | number}
      helperText={field.help}
      onChange={(event) => setValues({
        ...values,
        [field.name]: field.type === "number" ? Number(event.target.value) : event.target.value,
      })}
    >
      {(field.choices ?? []).map((choice) => <MenuItem key={choice} value={choice}>{choice}</MenuItem>)}
    </TextField>;
  };

  const saveConnector = async () => {
    if (!selectedType || !name.trim()) return;
    try {
      await createConnectorConfig({
        name, connector_key: selectedType.key, config: values,
        schedule_minutes: schedule ? Number(schedule) : null,
      });
      setDialog(false); setName(""); setSchedule(""); setSelectedKey(""); setValues({});
      setMessage({ kind: "success", text: "Data source configured. Credentials are encrypted at rest." });
      await load();
    } catch {
      setMessage({ kind: "error", text: "The data source could not be saved. Check the required fields and target policy." });
    }
  };

  const action = async (config: ConnectorConfig, kind: "test" | "run" | "delete") => {
    try {
      if (kind === "test") {
        const response = await testConnectorConfig(config.id);
        setMessage({ kind: response.data.success ? "success" : "error", text: response.data.message });
      } else if (kind === "run") {
        const response = await runConnectorConfig(config.id);
        setMessage({ kind: response.data.status === "failed" ? "error" : "success", text: `Collection finished: ${response.data.status}.` });
      } else if (window.confirm(`Delete data source "${config.name}"?`)) {
        await deleteConnectorConfig(config.id);
        setMessage({ kind: "success", text: "Data source removed." });
      }
      await load();
    } catch {
      setMessage({ kind: "error", text: `Unable to ${kind} this data source.` });
    }
  };

  const issueKey = async () => {
    try {
      const response = await createIngestApiKey({ name: keyName, scope: keyScope });
      setIssuedKey(response.data.api_key);
      setKeyDialog(false); setKeyName("");
      await load();
    } catch {
      setMessage({ kind: "error", text: "The ingestion key could not be created." });
    }
  };

  return <Box>
    <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
      <Box>
        <Typography variant="h4" fontWeight={700}>Data Sources & Collection</Typography>
        <Typography color="text.secondary">Connect EDR, SIEM, CMDB, identity, cloud, network and endpoint evidence to the CSOS correlation layer.</Typography>
      </Box>
      <Stack direction="row" spacing={1}>
        <Button startIcon={<RefreshIcon />} variant="outlined" onClick={() => void load()}>Refresh</Button>
        <Button startIcon={<AddIcon />} variant="contained" onClick={() => setDialog(true)}>Add Source</Button>
      </Stack>
    </Stack>
    {loading && <LinearProgress sx={{ mb: 2 }} />}
    {message && <Alert severity={message.kind} onClose={() => setMessage(null)} sx={{ mb: 2 }}>{message.text}</Alert>}
    {issuedKey && <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setIssuedKey(null)}>
      Copy this key now; it will not be shown again: <strong>{issuedKey}</strong>
    </Alert>}

    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid item xs={6} md={3}><Card variant="outlined"><CardContent><Typography variant="h4">{configs.length}</Typography><Typography color="text.secondary">Configured sources</Typography></CardContent></Card></Grid>
      <Grid item xs={6} md={3}><Card variant="outlined"><CardContent><Typography variant="h4">{types.length}</Typography><Typography color="text.secondary">Available adapters</Typography></CardContent></Card></Grid>
      <Grid item xs={6} md={3}><Card variant="outlined"><CardContent><Typography variant="h4">{configs.filter((item) => item.last_run_status === "success").length}</Typography><Typography color="text.secondary">Healthy sources</Typography></CardContent></Card></Grid>
      <Grid item xs={6} md={3}><Card variant="outlined"><CardContent><Typography variant="h4">{runs.reduce((sum, run) => sum + run.assets_found + run.vulnerabilities_found, 0)}</Typography><Typography color="text.secondary">Recent records collected</Typography></CardContent></Card></Grid>
    </Grid>

    <Paper variant="outlined">
      <Tabs value={tab} onChange={(_, value) => setTab(value)}>
        <Tab label="Configured Sources" /><Tab label="Run History" /><Tab label="Agent & Syslog Keys" /><Tab label="Adapter Catalog" />
      </Tabs>
      {tab === 0 && <Table><TableHead><TableRow><TableCell>Name</TableCell><TableCell>Adapter</TableCell><TableCell>Schedule</TableCell><TableCell>Status</TableCell><TableCell>Last run</TableCell><TableCell>Actions</TableCell></TableRow></TableHead><TableBody>
        {configs.map((config) => <TableRow key={config.id}>
          <TableCell><Typography fontWeight={700}>{config.name}</Typography><Typography variant="caption" color="text.secondary">{config.description}</Typography></TableCell>
          <TableCell>{types.find((item) => item.key === config.connector_key)?.display_name ?? config.connector_key}</TableCell>
          <TableCell>{config.schedule_minutes ? `Every ${config.schedule_minutes} min` : "Manual"}</TableCell>
          <TableCell><Chip size="small" color={statusColor(config.last_run_status)} label={config.last_run_status ?? (config.enabled ? "ready" : "disabled")} /></TableCell>
          <TableCell>{config.last_run_at ? new Date(config.last_run_at).toLocaleString() : "Never"}</TableCell>
          <TableCell><Stack direction="row" spacing={0.5}><Button size="small" onClick={() => void action(config, "test")}>Test</Button><Button size="small" startIcon={<PlayArrowIcon />} onClick={() => void action(config, "run")}>Run</Button><Button size="small" color="error" onClick={() => void action(config, "delete")}>Delete</Button></Stack></TableCell>
        </TableRow>)}
        {!configs.length && <TableRow><TableCell colSpan={6}>No live source is configured yet. Use “Add Source” when credentials are available.</TableCell></TableRow>}
      </TableBody></Table>}
      {tab === 1 && <Table><TableHead><TableRow><TableCell>Started</TableCell><TableCell>Source</TableCell><TableCell>Trigger</TableCell><TableCell>Status</TableCell><TableCell>Assets</TableCell><TableCell>Interfaces</TableCell><TableCell>Findings</TableCell><TableCell>Events</TableCell><TableCell>Duration</TableCell></TableRow></TableHead><TableBody>
        {runs.map((run) => <TableRow key={run.id}><TableCell>{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</TableCell><TableCell>{run.connector_key}</TableCell><TableCell>{run.trigger}</TableCell><TableCell><Chip size="small" color={statusColor(run.status)} label={run.status} /></TableCell><TableCell>{run.assets_found}</TableCell><TableCell>{run.interfaces_found}</TableCell><TableCell>{run.vulnerabilities_found}</TableCell><TableCell>{run.events_found}</TableCell><TableCell>{run.duration_seconds ?? "—"}s</TableCell></TableRow>)}
      </TableBody></Table>}
      {tab === 2 && <Box sx={{ p: 2 }}>
        {!canManageIngestKeys ? <Alert severity="info">Only CSOS administrators can create or view ingestion keys.</Alert> : <>
          <Button variant="contained" onClick={() => setKeyDialog(true)} sx={{ mb: 2 }}>Create ingestion key</Button>
          <Table><TableHead><TableRow><TableCell>Name</TableCell><TableCell>Prefix</TableCell><TableCell>Scope</TableCell><TableCell>Uses</TableCell><TableCell>Last used</TableCell><TableCell>Status</TableCell><TableCell /></TableRow></TableHead><TableBody>{keys.map((key) => <TableRow key={key.id}><TableCell>{key.name}</TableCell><TableCell>{key.key_prefix}…</TableCell><TableCell>{key.scope}</TableCell><TableCell>{key.use_count}</TableCell><TableCell>{key.last_used_at ? new Date(key.last_used_at).toLocaleString() : "Never"}</TableCell><TableCell>{key.enabled ? "Active" : "Revoked"}</TableCell><TableCell>{key.enabled && <Button color="error" size="small" onClick={async () => { await revokeIngestApiKey(key.id); await load(); }}>Revoke</Button>}</TableCell></TableRow>)}</TableBody></Table>
        </>}
      </Box>}
      {tab === 3 && <Grid container spacing={2} sx={{ p: 2 }}>{types.map((type) => <Grid item xs={12} sm={6} lg={4} key={type.key}><Card variant="outlined"><CardContent><Stack direction="row" justifyContent="space-between"><Typography fontWeight={700}>{type.display_name}</Typography><Chip size="small" label={type.category} /></Stack><Typography variant="body2" color="text.secondary" sx={{ my: 1 }}>{type.description}</Typography><Typography variant="caption">{type.schedulable ? "Scheduled or manual collection" : "Push ingestion"}</Typography></CardContent></Card></Grid>)}</Grid>}
    </Paper>

    <Dialog open={dialog} onClose={() => setDialog(false)} fullWidth maxWidth="md"><DialogTitle>Add data source</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
      <TextField select fullWidth label="Adapter" value={selectedKey} onChange={(event) => chooseType(event.target.value)}>{types.map((type) => <MenuItem key={type.key} value={type.key}>{type.display_name} · {type.category}</MenuItem>)}</TextField>
      <TextField fullWidth label="Source name" value={name} onChange={(event) => setName(event.target.value)} required />
      {selectedType?.schedulable && <TextField fullWidth type="number" label="Schedule (minutes, optional)" inputProps={{ min: 5 }} value={schedule} onChange={(event) => setSchedule(event.target.value)} />}
      {selectedType?.config_fields.map(renderField)}
    </Stack></DialogContent><DialogActions><Button onClick={() => setDialog(false)}>Cancel</Button><Button variant="contained" onClick={() => void saveConnector()} disabled={!selectedType || !name.trim()}>Save source</Button></DialogActions></Dialog>

    <Dialog open={keyDialog} onClose={() => setKeyDialog(false)} fullWidth maxWidth="sm"><DialogTitle>Create ingestion key</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField label="Name" value={keyName} onChange={(event) => setKeyName(event.target.value)} /><TextField select label="Scope" value={keyScope} onChange={(event) => setKeyScope(event.target.value as "agent" | "syslog")}><MenuItem value="agent">Endpoint agent</MenuItem><MenuItem value="syslog">Syslog HTTP forwarding</MenuItem></TextField></Stack></DialogContent><DialogActions><Button onClick={() => setKeyDialog(false)}>Cancel</Button><Button variant="contained" onClick={() => void issueKey()} disabled={!keyName.trim()}>Create key</Button></DialogActions></Dialog>
  </Box>;
};
