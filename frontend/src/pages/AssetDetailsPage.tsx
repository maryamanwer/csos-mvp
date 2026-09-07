import React, { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import AddLinkIcon from "@mui/icons-material/AddLink";
import {
  createAssetRelationship,
  getAsset,
  getTopology,
  listAssets,
  listVulnerabilities,
} from "@/services/api";
import { Asset, TopologyGraph as TopologyGraphData, Vulnerability } from "@/types";
import { riskColor } from "@/theme";
import { TopologyGraph } from "@/components/topology/TopologyGraph";
import { useAuth } from "@/contexts/AuthContext";

const EMPTY_GRAPH: TopologyGraphData = { nodes: [], edges: [] };

export const AssetDetailsPage = () => {
  const { assetId } = useParams();
  const { user } = useAuth();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [assetError, setAssetError] = useState(false);
  const [tab, setTab] = useState(0);
  const [topology, setTopology] = useState<TopologyGraphData>(EMPTY_GRAPH);
  const [topologyError, setTopologyError] = useState(false);
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [relationshipOpen, setRelationshipOpen] = useState(false);
  const [availableAssets, setAvailableAssets] = useState<Asset[]>([]);
  const [targetId, setTargetId] = useState("");
  const [relationshipType, setRelationshipType] = useState("CONNECTS_TO");
  const [message, setMessage] = useState<string | null>(null);
  const canWrite = user?.role === "Admin" || user?.role === "Engineer" || user?.role === "SecurityArchitect";

  useEffect(() => {
    if (!assetId) return;
    getAsset(assetId)
      .then((response) => setAsset(response.data))
      .catch(() => setAssetError(true));
  }, [assetId]);

  const loadTopology = useCallback(() => {
    if (!assetId) return;
    setTopologyError(false);
    getTopology(assetId)
      .then((response) => setTopology(response.data))
      .catch(() => {
        setTopology(EMPTY_GRAPH);
        setTopologyError(true);
      });
  }, [assetId]);

  useEffect(() => {
    if (tab === 1) loadTopology();
    if (tab === 2 && assetId) {
      listVulnerabilities({ asset_id: assetId })
        .then((response) => setVulnerabilities(response.data))
        .catch(() => setVulnerabilities([]));
    }
  }, [assetId, loadTopology, tab]);

  const openRelationship = async () => {
    try {
      const response = await listAssets();
      setAvailableAssets(response.data.filter((item: Asset) => item.id !== assetId));
      setTargetId(response.data.find((item: Asset) => item.id !== assetId)?.id ?? "");
      setRelationshipOpen(true);
    } catch {
      setMessage("Assets could not be loaded for relationship creation.");
    }
  };

  const saveRelationship = async () => {
    if (!assetId || !targetId) return;
    try {
      await createAssetRelationship(assetId, {
        target_id: targetId,
        relationship_type: relationshipType,
      });
      setRelationshipOpen(false);
      setMessage("Relationship created.");
      loadTopology();
    } catch {
      setMessage("The relationship could not be created.");
    }
  };

  if (assetError) return <Alert severity="error">Asset could not be loaded.</Alert>;
  if (!asset) return <Typography>Loading asset…</Typography>;

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2 }}>
        <Typography variant="h4">
          {asset.name}{" "}<Chip label={asset.criticality} sx={{ bgcolor: riskColor(asset.criticality), color: "#fff" }} />
        </Typography>
        {tab === 1 && canWrite && <Button startIcon={<AddLinkIcon />} variant="contained" onClick={() => void openRelationship()}>Add Relationship</Button>}
      </Box>
      {message && <Alert severity={message.includes("created") ? "success" : "error"} sx={{ mt: 2 }} onClose={() => setMessage(null)}>{message}</Alert>}
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab label="Overview" /><Tab label="Relationships" /><Tab label="Vulnerabilities" />
        <Tab label="Compliance Controls" /><Tab label="History" />
      </Tabs>
      <Box>
        {tab === 0 && <Box sx={{ display: "grid", gap: 1 }}>
          <Typography><strong>Type:</strong> {asset.type.replace(/_/g, " ")}</Typography>
          <Typography><strong>Environment:</strong> {asset.environment}</Typography>
          <Typography><strong>Data sensitivity:</strong> {asset.data_sensitivity}</Typography>
          <Typography><strong>Owner:</strong> {asset.owner ?? "—"}</Typography>
          <Typography><strong>IP address:</strong> {asset.ip_address ?? "—"}</Typography>
          <Typography><strong>Description:</strong> {asset.description ?? "—"}</Typography>
          <Typography><strong>Risk score:</strong> {asset.risk_score ?? 0}</Typography>
        </Box>}
        {tab === 1 && <>
          {topologyError && <Alert severity="error" sx={{ mb: 2 }}>Relationship data could not be loaded from Neo4j.</Alert>}
          <TopologyGraph graph={topology} focusNodeId={assetId} height={520} />
        </>}
        {tab === 2 && <List>
          {vulnerabilities.map((item) => <ListItem key={item.id} divider secondaryAction={
            <Chip label={item.severity} sx={{ bgcolor: riskColor(item.severity), color: "white" }} />
          }>
            <ListItemText primary={item.title} secondary={`${item.cve_id ?? "Internal"} · CVSS ${item.cvss_score} · ${item.status}`} />
          </ListItem>)}
          {vulnerabilities.length === 0 && <ListItem><ListItemText primary="No vulnerabilities linked to this asset." /></ListItem>}
        </List>}
        {tab === 3 && <Typography color="text.secondary">Mapped controls appear in Network Topology and the Compliance gap analysis.</Typography>}
        {tab === 4 && <Typography color="text.secondary">Asset changes are recorded in the Administration audit log.</Typography>}
      </Box>

      <Dialog open={relationshipOpen} onClose={() => setRelationshipOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add Asset Relationship</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: "16px !important" }}>
          <TextField select label="Target asset" value={targetId} onChange={(event) => setTargetId(event.target.value)}>
            {availableAssets.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField select label="Relationship type" value={relationshipType} onChange={(event) => setRelationshipType(event.target.value)}>
            {["CONNECTS_TO", "DEPENDS_ON", "HOSTS", "COMMUNICATES_WITH"].map((value) => <MenuItem key={value} value={value}>{value.replace(/_/g, " ")}</MenuItem>)}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRelationshipOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!targetId} onClick={() => void saveRelationship()}>Create</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
