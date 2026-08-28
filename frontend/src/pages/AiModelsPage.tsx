import React, { useCallback, useEffect, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Grid, LinearProgress,
  Paper, Stack, Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { aiModelStatus, pullAiModel, validateAiModel } from "@/services/api";
import { AiModelStatus } from "@/types";
import { useAuth } from "@/contexts/AuthContext";

export const AiModelsPage = () => {
  const { user } = useAuth();
  const canInstallModels = user?.role === "Admin";
  const [status, setStatus] = useState<AiModelStatus | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ severity: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await aiModelStatus();
      setStatus(response.data);
    } catch {
      setMessage({ severity: "error", text: "AI runtime status could not be loaded." });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const action = async (model: string, kind: "install" | "validate") => {
    setBusy(model); setMessage(null);
    try {
      if (kind === "install") await pullAiModel(model); else await validateAiModel(model);
      setMessage({ severity: "success", text: `${model} ${kind === "install" ? "installed" : "validated"} successfully.` });
      await load();
    } catch {
      setMessage({ severity: "error", text: `${model} could not be ${kind === "install" ? "installed" : "validated"}. Check Ollama capacity and logs.` });
    } finally { setBusy(null); }
  };

  if (!status) return <LinearProgress />;
  return <Box>
    <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
      <Box><Typography variant="h4" fontWeight={700}>Local AI Models</Typography><Typography color="text.secondary">Manage the air-gapped Ollama runtime used by grounded CSOS agents.</Typography></Box>
      <Button startIcon={<RefreshIcon />} variant="outlined" onClick={() => void load()}>Refresh</Button>
    </Stack>
    {message && <Alert severity={message.severity} onClose={() => setMessage(null)} sx={{ mb: 2 }}>{message.text}</Alert>}
    <Alert severity={status.healthy ? "success" : "warning"} sx={{ mb: 2 }}>
      Ollama runtime is {status.healthy ? "online" : "offline"}. CSOS falls back to deterministic, grounded summaries when a local model is unavailable.
    </Alert>
    {!canInstallModels && <Alert severity="info" sx={{ mb: 2 }}>Engineers can validate installed models. Only administrators can install a new model package.</Alert>}
    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid item xs={12} md={4}><Card variant="outlined"><CardContent><Typography variant="overline">Provider</Typography><Typography variant="h5">{status.provider}</Typography><Typography variant="body2" color="text.secondary">{status.runtime_url}</Typography></CardContent></Card></Grid>
      <Grid item xs={12} md={4}><Card variant="outlined"><CardContent><Typography variant="overline">Default model</Typography><Typography variant="h5">{status.default_model}</Typography><Typography variant="body2" color="text.secondary">Used for grounded responses</Typography></CardContent></Card></Grid>
      <Grid item xs={12} md={4}><Card variant="outlined"><CardContent><Typography variant="overline">Deployment</Typography><Typography variant="h5">Air-gapped ready</Typography><Typography variant="body2" color="text.secondary">No cloud inference is required</Typography></CardContent></Card></Grid>
    </Grid>
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>Approved model catalog</Typography>
      <Grid container spacing={2}>{status.configured_models.map((model) => {
        const installed = status.installed_models.some((name) => name === model || name.startsWith(`${model}:`));
        return <Grid item xs={12} sm={6} lg={4} key={model}><Card variant="outlined"><CardContent><Stack direction="row" justifyContent="space-between" alignItems="center"><Typography fontWeight={700}>{model}</Typography><Chip size="small" color={installed ? "success" : "default"} label={installed ? "Installed" : "Not installed"} /></Stack><Typography variant="body2" color="text.secondary" sx={{ my: 2 }}>{model === status.default_model ? "Default CSOS model" : "Approved compatible local model"}</Typography><Stack direction="row" spacing={1}>{!installed && canInstallModels && <Button size="small" variant="contained" disabled={Boolean(busy) || !status.healthy} onClick={() => void action(model, "install")}>Install</Button>}{installed && <Button size="small" variant="outlined" disabled={Boolean(busy) || !status.healthy} onClick={() => void action(model, "validate")}>Validate</Button>}</Stack></CardContent></Card></Grid>;
      })}</Grid>
    </Paper>
  </Box>;
};
