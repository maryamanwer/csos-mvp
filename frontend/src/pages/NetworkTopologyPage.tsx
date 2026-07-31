import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { TopologyGraph as TopologyGraphView } from "@/components/topology/TopologyGraph";
import { getTopology } from "@/services/api";
import { TopologyGraph, TopologyNode } from "@/types";

const EMPTY_GRAPH: TopologyGraph = { nodes: [], edges: [] };

export const NetworkTopologyPage = () => {
  const [graph, setGraph] = useState<TopologyGraph>(EMPTY_GRAPH);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [entityType, setEntityType] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTopology = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getTopology();
      setGraph(response.data);
    } catch {
      setGraph(EMPTY_GRAPH);
      setError("Topology data could not be loaded. Confirm that Neo4j is running and the graph schema has been initialized.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTopology();
  }, [loadTopology]);

  const entityTypes = useMemo(
    () => Array.from(new Set(graph.nodes.map((node) => node.type))).sort(),
    [graph.nodes],
  );

  const filteredGraph = useMemo(() => {
    const typeAllowed = new Set(
      graph.nodes
        .filter((node) => entityType === "all" || node.type === entityType)
        .map((node) => node.id),
    );
    const term = search.trim().toLowerCase();
    let visibleIds = new Set(typeAllowed);

    if (term) {
      const matches = new Set(
        graph.nodes
          .filter((node) => {
            if (!typeAllowed.has(node.id)) return false;
            const properties = Object.values(node.properties).join(" ").toLowerCase();
            return `${node.label} ${node.type} ${properties}`.toLowerCase().includes(term);
          })
          .map((node) => node.id),
      );
      visibleIds = new Set(matches);
      graph.edges.forEach((edge) => {
        if (matches.has(edge.source) && typeAllowed.has(edge.target)) visibleIds.add(edge.target);
        if (matches.has(edge.target) && typeAllowed.has(edge.source)) visibleIds.add(edge.source);
      });
    }

    return {
      nodes: graph.nodes.filter((node) => visibleIds.has(node.id)),
      edges: graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    };
  }, [entityType, graph, search]);

  useEffect(() => {
    if (selectedNode && !filteredGraph.nodes.some((node) => node.id === selectedNode.id)) {
      setSelectedNode(null);
    }
  }, [filteredGraph.nodes, selectedNode]);

  return (
    <>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h4">Network Topology</Typography>
          <Typography color="text.secondary">
            Interactive relationships generated automatically from the Cyber Knowledge Graph.
          </Typography>
        </Box>
        <Button startIcon={<RefreshIcon />} onClick={() => void loadTopology()} disabled={loading}>
          Refresh graph
        </Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Search assets and relationships"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ minWidth: 320 }}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Entity type</InputLabel>
          <Select label="Entity type" value={entityType} onChange={(event) => setEntityType(event.target.value)}>
            <MenuItem value="all">All entity types</MenuItem>
            {entityTypes.map((type) => <MenuItem key={type} value={type}>{type}</MenuItem>)}
          </Select>
        </FormControl>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip label={`${filteredGraph.nodes.length} entities`} />
          <Chip label={`${filteredGraph.edges.length} relationships`} />
        </Stack>
      </Stack>

      <Grid container spacing={2}>
        <Grid item xs={12} lg={selectedNode ? 9 : 12}>
          {loading ? (
            <Card variant="outlined" sx={{ height: 620, display: "grid", placeItems: "center" }}>
              <Typography color="text.secondary">Loading topology…</Typography>
            </Card>
          ) : (
            <TopologyGraphView
              graph={filteredGraph}
              selectedNodeId={selectedNode?.id}
              onSelectNode={setSelectedNode}
            />
          )}
        </Grid>
        {selectedNode && (
          <Grid item xs={12} lg={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="overline" color="text.secondary">{selectedNode.type}</Typography>
                <Typography variant="h6" gutterBottom>{selectedNode.label}</Typography>
                <Stack spacing={1}>
                  {Object.entries(selectedNode.properties).map(([key, value]) => (
                    <Box key={key}>
                      <Typography variant="caption" color="text.secondary">{key.replace(/_/g, " ")}</Typography>
                      <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
                        {typeof value === "object" ? JSON.stringify(value) : String(value)}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </>
  );
};
