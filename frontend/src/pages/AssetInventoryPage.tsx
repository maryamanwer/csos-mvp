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
  importAssetRelationships,
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
  data_sensitivity: "internal",
  owner: "",
  exposure: "internal",
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
  const canWrite = user?.role === "Admin" || user?.role === "Engineer" || user?.role === "SecurityArchitect";

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
      data_sensitivity: asset.data_sensitivity ?? "internal",
      owner: asset.owner ?? "",
      exposure: asset.exposure ?? "internal",
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

  const uploadRelationships = async (file?: File) => {
    if (!file) return;
    try {
      const { data } = await importAssetRelationships(file);
      setMessage({ severity: data.failed ? "error" : "success", text: `${data.imported} relationships imported; ${data.failed} rows failed.` });
      loadAssets();
    } catch {
      setMessage({ severity: "error", text: "Relationship import failed. Use source_id, target_id, and relationship_type columns." });
    }
  };

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, gap: 2, flexWrap: "wrap" }}>
        <Typography variant="h4">Asset Inventory</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          {canWrite && (
            <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
              Import Relationships
              <input hidden type="file" accept=".csv,.xlsx,.xls" onChange={(event) => void uploadRelationships(event.target.files?.[0])} />
            </Button>
          )}
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
              <TableCell>Owner</TableCell>
              <TableCell>Criticality</TableCell>
              <TableCell>Data sensitivity</TableCell>
              <TableCell>Environment</TableCell>
              <TableCell>Risk Score</TableCell>
              {canWrite && <TableCell align="right">Actions</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.map((asset) => (
              <TableRow key={asset.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/assets/${asset.id}`)}>
                <TableCell>{asset.name}</TableCell>
                <TableCell>{asset.type.replace(/_/g, " ")}</TableCell>
                <TableCell>{asset.owner ?? "—"}</TableCell>
                <TableCell><Chip label={asset.criticality} sx={{ bgcolor: riskColor(asset.criticality), color: "#fff" }} size="small" /></TableCell>
                <TableCell>{asset.data_sensitivity}</TableCell>
                <TableCell>{asset.environment}</TableCell>
                <TableCell>{asset.risk_score ?? 0}</TableCell>
                {canWrite && (
                  <TableCell align="right">
                    <Tooltip title="Edit asset"><IconButton onClick={(event) => { event.stopPropagation(); openEdit(asset); }}><EditIcon /></IconButton></Tooltip>
                    <Tooltip title="Delete asset"><IconButton color="error" onClick={(event) => { event.stopPropagation(); void removeAsset(asset); }}><DeleteIcon /></IconButton></Tooltip>
                  </TableCell>
                )}
              </TableRow>
            ))}
            {assets.length === 0 && <TableRow><TableCell colSpan={canWrite ? 8 : 7}>No matching assets.</TableCell></TableRow>}
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
              ["identity", "Identity"], ["database", "Database"], ["cloud_resource", "Cloud resource"],
            ].map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
          </TextField>
          <TextField label="Environment" value={draft.environment} onChange={(event) => setDraft({ ...draft, environment: event.target.value })} required />
          <TextField select label="Criticality" value={draft.criticality} onChange={(event) => setDraft({ ...draft, criticality: event.target.value as AssetDraft["criticality"] })}>
            {["low", "medium", "high", "critical"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}
          </TextField>
          <TextField select label="Data sensitivity" value={draft.data_sensitivity} onChange={(event) => setDraft({ ...draft, data_sensitivity: event.target.value as AssetDraft["data_sensitivity"] })}>
            {["public", "internal", "confidential", "restricted"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}
          </TextField>
          <TextField select label="Exposure" value={draft.exposure ?? "internal"} onChange={event => setDraft({...draft, exposure: event.target.value as AssetDraft["exposure"]})}>
            {["internal", "partner", "internet"].map(value => <MenuItem key={value} value={value}>{value}</MenuItem>)}
          </TextField>
          <TextField label="Owner" value={draft.owner ?? ""} onChange={(event) => setDraft({ ...draft, owner: event.target.value })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void saveAsset()} disabled={!draft.name || !draft.environment}>Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
