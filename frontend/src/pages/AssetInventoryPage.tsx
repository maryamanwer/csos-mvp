import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { useNavigate } from "react-router-dom";
import {
  createAsset,
  deleteAsset,
  importAssets,
  listAssets,
  updateAsset,
} from "@/services/api";
import { Asset } from "@/types";
import { riskColor } from "@/theme";
import { useAuth } from "@/contexts/AuthContext";

type AssetDraft = Omit<Asset, "id" | "risk_score">;

const EMPTY_ASSET: AssetDraft = {
  name: "",
  type: "server",
  environment: "production",
  criticality: "medium",
  owner: "",
  hostname: "",
  ip_address: "",
  operating_system: "",
  edr_status: "unknown",
  edr_product: "",
  edr_agent_version: "",
  edr_agent_outdated: false,
  managed_status: "unknown",
  data_sources: [],
};

export const AssetInventoryPage = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [draft, setDraft] = useState<AssetDraft>(EMPTY_ASSET);
  const [message, setMessage] = useState<{ severity: "success" | "error"; text: string } | null>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = user?.role === "Admin" || user?.role === "Engineer";

  const loadAssets = useCallback(() => {
    listAssets(search ? { search } : undefined)
      .then((response) => setAssets(response.data))
      .catch(() => setMessage({ severity: "error", text: "Assets could not be loaded from Neo4j." }));
  }, [search]);

  useEffect(() => { loadAssets(); }, [loadAssets]);

  const openCreate = () => {
    setEditing(null);
    setDraft(EMPTY_ASSET);
    setDialogOpen(true);
  };

  const openEdit = (asset: Asset) => {
    setEditing(asset);
    setDraft({
      name: asset.name,
      type: asset.type,
      environment: asset.environment,
      criticality: asset.criticality,
      owner: asset.owner ?? "",
      hostname: asset.hostname ?? "",
      ip_address: asset.ip_address ?? "",
      operating_system: asset.operating_system ?? "",
      edr_status: asset.edr_status ?? "unknown",
      edr_product: asset.edr_product ?? "",
      edr_agent_version: asset.edr_agent_version ?? "",
      edr_agent_outdated: asset.edr_agent_outdated ?? false,
      managed_status: asset.managed_status ?? "unknown",
      data_sources: asset.data_sources ?? [],
    });
    setDialogOpen(true);
  };

  const saveAsset = async () => {
    try {
      if (editing) await updateAsset(editing.id, draft);
      else await createAsset(draft);
      setDialogOpen(false);
      setMessage({ severity: "success", text: editing ? "Asset updated." : "Asset created." });
      loadAssets();
    } catch {
      setMessage({ severity: "error", text: "The asset could not be saved." });
    }
  };

  const removeAsset = async (asset: Asset) => {
    if (!window.confirm(`Delete ${asset.name} and its relationships?`)) return;
    try {
      await deleteAsset(asset.id);
      setMessage({ severity: "success", text: "Asset deleted." });
      loadAssets();
    } catch {
      setMessage({ severity: "error", text: "The asset could not be deleted." });
    }
  };

  const uploadAssets = async (file?: File) => {
    if (!file) return;
    try {
      const { data } = await importAssets(file);
      setMessage({
        severity: data.failed ? "error" : "success",
        text: `${data.imported} assets imported; ${data.failed} rows failed.`,
      });
      loadAssets();
    } catch {
      setMessage({ severity: "error", text: "Import failed. Use a CSV/XLSX file with name, type, environment, criticality, and owner columns." });
    }
  };

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, gap: 2, flexWrap: "wrap" }}>
        <Typography variant="h4">Asset Inventory</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          {canWrite && (
            <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
              Import CSV/Excel
              <input hidden type="file" accept=".csv,.xlsx,.xls" onChange={(event) => void uploadAssets(event.target.files?.[0])} />
            </Button>
          )}
          {canWrite && <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add Asset</Button>}
        </Box>
      </Box>

      {message && <Alert severity={message.severity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>{message.text}</Alert>}
      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <TextField
          size="small"
          label="Search assets or owners"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") loadAssets(); }}
          sx={{ minWidth: 320 }}
        />
        <Button variant="outlined" onClick={loadAssets}>Search</Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Hostname / IP</TableCell>
              <TableCell>Owner</TableCell>
              <TableCell>Criticality</TableCell>
              <TableCell>Environment</TableCell>
              <TableCell>Risk Score</TableCell>
              <TableCell>EDR</TableCell>
              {canWrite && <TableCell align="right">Actions</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.map((asset) => (
              <TableRow key={asset.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/assets/${asset.id}`)}>
                <TableCell>{asset.name}</TableCell>
                <TableCell>{asset.type.replace(/_/g, " ")}</TableCell>
                <TableCell><Typography variant="body2">{asset.hostname ?? "—"}</Typography><Typography variant="caption" color="text.secondary">{asset.ip_address ?? "IP not reported"}</Typography></TableCell>
                <TableCell>{asset.owner ?? "—"}</TableCell>
                <TableCell><Chip label={asset.criticality} sx={{ bgcolor: riskColor(asset.criticality), color: "#fff" }} size="small" /></TableCell>
                <TableCell>{asset.environment}</TableCell>
                <TableCell>{asset.risk_score ?? 0}</TableCell>
                <TableCell><Chip size="small" label={(asset.edr_status ?? "unknown").replace(/_/g, " ")} color={asset.edr_status === "active" ? "success" : asset.edr_status === "outdated" ? "warning" : "default"} /></TableCell>
                {canWrite && (
                  <TableCell align="right">
                    <Tooltip title="Edit asset"><IconButton onClick={(event) => { event.stopPropagation(); openEdit(asset); }}><EditIcon /></IconButton></Tooltip>
                    <Tooltip title="Delete asset"><IconButton color="error" onClick={(event) => { event.stopPropagation(); void removeAsset(asset); }}><DeleteIcon /></IconButton></Tooltip>
                  </TableCell>
                )}
              </TableRow>
            ))}
            {assets.length === 0 && <TableRow><TableCell colSpan={canWrite ? 9 : 8}>No matching assets.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Edit Asset" : "Add Asset"}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: "16px !important" }}>
          <TextField label="Asset name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} required />
          <TextField select label="Type" value={draft.type} onChange={(event) => setDraft({ ...draft, type: event.target.value as AssetDraft["type"] })}>
            {[
              ["server", "Server"], ["application", "Application"], ["network_device", "Network device"],
              ["router", "Router"], ["switch", "Switch"], ["firewall", "Firewall"],
              ["database", "Database"], ["endpoint", "Endpoint"], ["workstation", "Workstation"],
              ["cloud_resource", "Cloud resource"], ["other", "Other"],
            ].map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
          </TextField>
          <TextField label="Environment" value={draft.environment} onChange={(event) => setDraft({ ...draft, environment: event.target.value })} required />
          <TextField select label="Criticality" value={draft.criticality} onChange={(event) => setDraft({ ...draft, criticality: event.target.value as AssetDraft["criticality"] })}>
            {["low", "medium", "high", "critical"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}
          </TextField>
          <TextField label="Owner" value={draft.owner ?? ""} onChange={(event) => setDraft({ ...draft, owner: event.target.value })} />
          <TextField label="Preferred hostname" value={draft.hostname ?? ""} onChange={(event) => setDraft({ ...draft, hostname: event.target.value })} />
          <TextField label="IP address" value={draft.ip_address ?? ""} onChange={(event) => setDraft({ ...draft, ip_address: event.target.value })} />
          <TextField label="Operating system" value={draft.operating_system ?? ""} onChange={(event) => setDraft({ ...draft, operating_system: event.target.value })} />
          <TextField select label="EDR status" value={draft.edr_status ?? "unknown"} onChange={(event) => setDraft({ ...draft, edr_status: event.target.value as AssetDraft["edr_status"] })}>
            {["active", "missing", "outdated", "not_applicable", "unknown"].map((value) => <MenuItem key={value} value={value}>{value.replace(/_/g, " ")}</MenuItem>)}
          </TextField>
          <TextField label="EDR product" value={draft.edr_product ?? ""} onChange={(event) => setDraft({ ...draft, edr_product: event.target.value })} />
          <TextField select label="Management status" value={draft.managed_status ?? "unknown"} onChange={(event) => setDraft({ ...draft, managed_status: event.target.value as AssetDraft["managed_status"] })}>
            {["managed", "unmanaged", "unknown"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}
          </TextField>
          <TextField label="Data sources (comma-separated)" value={(draft.data_sources ?? []).join(", ")} onChange={(event) => setDraft({ ...draft, data_sources: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void saveAsset()} disabled={!draft.name || !draft.environment}>Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
