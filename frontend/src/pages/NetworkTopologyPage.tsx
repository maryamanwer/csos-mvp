import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { TopologyGraph as TopologyGraphView } from "@/components/topology/TopologyGraph";
import { getTopology } from "@/services/api";
import { TopologyEdge, TopologyGraph, TopologyNode } from "@/types";

const EMPTY_GRAPH: TopologyGraph = { nodes: [], edges: [], truncated: false };
const RISK_COLORS = { high: "#D92D20", medium: "#F79009", low: "#12B76A" };
const RELATIONSHIP_COLORS = {
  network: "#344054",
  vulnerability: "#D92D20",
  risk: "#F79009",
  identity: "#7A5AF8",
  control: "#0E9384",
  other: "#98A2B3",
};

export interface TopologyFilters {
  assetType: string;
  riskLevel: string;
  environment: string;
  relationship: string;
  search: string;
}

export const filterTopologyGraph = (
  graph: TopologyGraph,
  { assetType, riskLevel, environment, relationship, search }: TopologyFilters,
): TopologyGraph => {
  const candidateEdges = relationship === "all"
    ? graph.edges
    : graph.edges.filter((edge) => edge.category === relationship);
  const term = search.trim().toLowerCase();
  const filteringAssets = assetType !== "all" || riskLevel !== "all" || environment !== "all";
  const seedIds = new Set<string>();

  graph.nodes.forEach((node) => {
    const searchable = `${node.label} ${node.ip_address ?? ""} ${Object.values(node.properties).join(" ")}`.toLowerCase();
    const searchMatch = !term || searchable.includes(term);
    if (node.type === "Asset") {
      const assetMatch = (assetType === "all" || node.asset_type === assetType)
        && (riskLevel === "all" || node.risk_level === riskLevel)
        && (environment === "all" || node.properties.environment === environment);
      if (assetMatch && searchMatch) seedIds.add(node.id);
    } else if (!filteringAssets && searchMatch) seedIds.add(node.id);
  });

  if (!term && !filteringAssets && relationship === "all") return graph;
  const visibleIds = new Set(seedIds);
  candidateEdges.forEach((edge) => {
    if (seedIds.has(edge.source) || seedIds.has(edge.target)) {
      visibleIds.add(edge.source);
      visibleIds.add(edge.target);
    }
  });
  if (relationship !== "all" && !term && !filteringAssets) {
    candidateEdges.forEach((edge) => {
      visibleIds.add(edge.source);
      visibleIds.add(edge.target);
    });
  }
  return {
    nodes: graph.nodes.filter((node) => visibleIds.has(node.id)),
    edges: candidateEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    truncated: graph.truncated,
  };
};

const valueText = (value: unknown) => {
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return value === null || value === undefined || value === "" ? "—" : String(value);
};

export const NetworkTopologyPage = () => {
  const [graph, setGraph] = useState<TopologyGraph>(EMPTY_GRAPH);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<TopologyEdge | null>(null);
  const [assetType, setAssetType] = useState("all");
  const [riskLevel, setRiskLevel] = useState("all");
  const [environment, setEnvironment] = useState("all");
  const [relationship, setRelationship] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTopology = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getTopology();
      setGraph(response.data as TopologyGraph);
    } catch {
      setGraph(EMPTY_GRAPH);
      setError("Topology data could not be loaded from the Cyber Knowledge Graph.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadTopology(); }, [loadTopology]);

  const assetTypes = useMemo(() => Array.from(new Set(graph.nodes.filter((node) => node.type === "Asset").map((node) => node.asset_type).filter(Boolean) as string[])).sort(), [graph.nodes]);
  const environments = useMemo(() => Array.from(new Set(graph.nodes.filter((node) => node.type === "Asset").map((node) => String(node.properties.environment ?? "")).filter(Boolean))).sort(), [graph.nodes]);

  const filteredGraph = useMemo(() => {
    return filterTopologyGraph(graph, { assetType, riskLevel, environment, relationship, search });
  }, [assetType, environment, graph, relationship, riskLevel, search]);

  const selectedRelationships = useMemo(() => {
    if (!selectedNode) return [];
    return graph.edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id);
  }, [graph.edges, selectedNode]);

  const relatedNodes = useMemo(() => {
    if (!selectedNode) return [];
    const ids = new Set(selectedRelationships.flatMap((edge) => [edge.source, edge.target]));
    ids.delete(selectedNode.id);
    return graph.nodes.filter((node) => ids.has(node.id));
  }, [graph.nodes, selectedNode, selectedRelationships]);

  const selectNode = (node: TopologyNode) => { setSelectedNode(node); setSelectedEdge(null); };
  const selectEdge = (edge: TopologyEdge) => { setSelectedEdge(edge); setSelectedNode(null); };

  const detailGroups: Record<string, TopologyNode[]> = selectedNode ? {
    Network: relatedNodes.filter((node) => ["Asset", "NetworkInterface", "NetworkSegment"].includes(node.type)),
    Vulnerabilities: relatedNodes.filter((node) => node.type === "Vulnerability"),
    Risks: relatedNodes.filter((node) => node.type === "Risk"),
    Identities: relatedNodes.filter((node) => node.type === "Identity"),
    Controls: relatedNodes.filter((node) => ["Control", "Policy", "Framework"].includes(node.type)),
  } : {};

  return (
    <Box>
      <Stack direction={{ xs: "column", lg: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Cyber Knowledge Graph Topology</Typography>
          <Typography color="text.secondary">Network paths, interfaces, vulnerabilities, risks, identities, and controls from actual CSOS relationships.</Typography>
        </Box>
        <Button startIcon={<RefreshIcon />} variant="outlined" onClick={() => void loadTopology()} disabled={loading}>Refresh Graph</Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {graph.truncated && <Alert severity="info" sx={{ mb: 2 }}>This is a bounded topology view. Refine filters or select an asset to investigate its relationships.</Alert>}

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={1.5} alignItems="center">
          <Grid item xs={12} md={4}><TextField fullWidth size="small" label="Search asset, hostname, IP, CVE, risk, or identity" value={search} onChange={(event) => setSearch(event.target.value)} /></Grid>
          <Grid item xs={6} sm={3} md={2}><FormControl fullWidth size="small"><InputLabel>Asset type</InputLabel><Select label="Asset type" value={assetType} onChange={(event) => setAssetType(event.target.value)}><MenuItem value="all">All asset types</MenuItem>{assetTypes.map((value) => <MenuItem key={value} value={value}>{value.replace(/_/g, " ")}</MenuItem>)}</Select></FormControl></Grid>
          <Grid item xs={6} sm={3} md={2}><FormControl fullWidth size="small"><InputLabel>Risk</InputLabel><Select label="Risk" value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)}><MenuItem value="all">All risk levels</MenuItem>{["high", "medium", "low"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</Select></FormControl></Grid>
          <Grid item xs={6} sm={3} md={2}><FormControl fullWidth size="small"><InputLabel>Environment</InputLabel><Select label="Environment" value={environment} onChange={(event) => setEnvironment(event.target.value)}><MenuItem value="all">All environments</MenuItem>{environments.map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</Select></FormControl></Grid>
          <Grid item xs={6} sm={3} md={2}><FormControl fullWidth size="small"><InputLabel>Relationship</InputLabel><Select label="Relationship" value={relationship} onChange={(event) => setRelationship(event.target.value)}><MenuItem value="all">All relationships</MenuItem>{["network", "vulnerability", "risk", "identity", "control"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</Select></FormControl></Grid>
        </Grid>
        <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} alignItems="center" flexWrap="wrap" useFlexGap>
          <Chip label={`${filteredGraph.nodes.length} entities`} /><Chip label={`${filteredGraph.edges.length} relationships`} />
          <Button size="small" onClick={() => { setSearch(""); setAssetType("all"); setRiskLevel("all"); setEnvironment("all"); setRelationship("all"); }}>Clear filters</Button>
        </Stack>
      </Paper>

      {loading && <LinearProgress sx={{ mb: 1 }} />}
      <Grid container spacing={2}>
        <Grid item xs={12} lg={selectedNode || selectedEdge ? 9 : 12}>
          <TopologyGraphView graph={filteredGraph} selectedNodeId={selectedNode?.id} selectedEdgeId={selectedEdge?.id} onSelectNode={selectNode} onSelectEdge={selectEdge} />
        </Grid>
        {(selectedNode || selectedEdge) && <Grid item xs={12} lg={3}>
          <Card variant="outlined" sx={{ height: 760, overflow: "auto" }}>
            <CardContent>
              {selectedNode && <Stack spacing={2}>
                <Box>
                  <Typography variant="overline" color="text.secondary">{selectedNode.type}</Typography>
                  <Typography variant="h6" fontWeight={700}>{selectedNode.label}</Typography>
                  {selectedNode.type === "Asset" && <Stack direction="row" spacing={1} sx={{ mt: 1 }}><Chip size="small" label={`${selectedNode.risk_level ?? "low"} risk`} sx={{ bgcolor: RISK_COLORS[selectedNode.risk_level ?? "low"], color: "white" }} /><Chip size="small" variant="outlined" label={selectedNode.criticality ?? "unknown criticality"} /></Stack>}
                </Box>
                <Divider />
                <Box><Typography fontWeight={700}>Asset information</Typography>{["name", "hostname", "ip_address", "type", "environment", "criticality", "owner", "operating_system", "edr_status", "edr_product"].filter((key) => selectedNode.properties[key] !== undefined).map((key) => <Box key={key} sx={{ mt: 0.75 }}><Typography variant="caption" color="text.secondary">{key.replace(/_/g, " ")}</Typography><Typography variant="body2">{valueText(selectedNode.properties[key])}</Typography></Box>)}</Box>
                {Object.entries(detailGroups).map(([label, nodes]) => <Box key={label}><Typography fontWeight={700}>{label}</Typography>{nodes.length ? <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mt: 0.75 }}>{nodes.map((node) => <Chip size="small" key={node.id} label={node.label} onClick={() => selectNode(node)} />)}</Stack> : <Typography variant="body2" color="text.secondary">None recorded</Typography>}</Box>)}
                <Divider />
                <Box><Typography fontWeight={700}>Relationships</Typography>{selectedRelationships.map((edge) => <Paper key={edge.id} variant="outlined" sx={{ p: 1, mt: 0.75, cursor: "pointer" }} onClick={() => selectEdge(edge)}><Typography variant="caption" fontWeight={700}>{edge.type.replace(/_/g, " ")}</Typography><Typography variant="body2" color="text.secondary">{edge.source_interface || edge.target_interface ? `${edge.source_interface ?? "?"} ↔ ${edge.target_interface ?? "?"}` : "Stored graph relationship"}</Typography></Paper>)}</Box>
              </Stack>}
              {selectedEdge && <Stack spacing={2}>
                <Box><Typography variant="overline" color="text.secondary">{selectedEdge.category} relationship</Typography><Typography variant="h6" fontWeight={700}>{selectedEdge.type.replace(/_/g, " ")}</Typography></Box>
                <Divider />
                <Box><Typography variant="caption" color="text.secondary">Source interface</Typography><Typography>{selectedEdge.source_interface ?? "Not reported"}</Typography></Box>
                <Box><Typography variant="caption" color="text.secondary">Target interface</Typography><Typography>{selectedEdge.target_interface ?? "Not reported"}</Typography></Box>
                {Object.entries(selectedEdge.properties).map(([key, value]) => <Box key={key}><Typography variant="caption" color="text.secondary">{key.replace(/_/g, " ")}</Typography><Typography variant="body2">{valueText(value)}</Typography></Box>)}
              </Stack>}
            </CardContent>
          </Card>
        </Grid>}
      </Grid>

      <Paper variant="outlined" sx={{ p: 1.5, mt: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={3} justifyContent="space-between">
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap><Typography fontWeight={700}>Risk</Typography>{Object.entries(RISK_COLORS).map(([label, color]) => <Stack direction="row" spacing={0.5} alignItems="center" key={label}><Box sx={{ width: 14, height: 14, bgcolor: color, borderRadius: "50%" }} /><Typography variant="body2">{label}</Typography></Stack>)}</Stack>
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap><Typography fontWeight={700}>Relationships</Typography>{Object.entries(RELATIONSHIP_COLORS).filter(([key]) => key !== "other").map(([label, color]) => <Stack direction="row" spacing={0.5} alignItems="center" key={label}><Box sx={{ width: 28, borderTop: `3px solid ${color}` }} /><Typography variant="body2">{label}</Typography></Stack>)}</Stack>
        </Stack>
      </Paper>
    </Box>
  );
};
