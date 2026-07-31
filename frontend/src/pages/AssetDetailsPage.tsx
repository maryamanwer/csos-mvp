import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Alert, Box, Chip, Tab, Tabs, Typography } from "@mui/material";
import { getAsset, getTopology } from "@/services/api";
import { Asset, TopologyGraph as TopologyGraphData } from "@/types";
import { riskColor } from "@/theme";
import { TopologyGraph } from "@/components/topology/TopologyGraph";

const EMPTY_GRAPH: TopologyGraphData = { nodes: [], edges: [] };

export const AssetDetailsPage = () => {
  const { assetId } = useParams();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [tab, setTab] = useState(0);
  const [topology, setTopology] = useState<TopologyGraphData>(EMPTY_GRAPH);
  const [topologyError, setTopologyError] = useState(false);

  useEffect(() => {
    if (assetId) getAsset(assetId).then((res) => setAsset(res.data)).catch(() => setAsset(null));
  }, [assetId]);

  useEffect(() => {
    if (tab !== 1 || !assetId) return;
    setTopologyError(false);
    getTopology(assetId)
      .then((res) => setTopology(res.data))
      .catch(() => {
        setTopology(EMPTY_GRAPH);
        setTopologyError(true);
      });
  }, [assetId, tab]);

  if (!asset) return <Typography>Loading asset…</Typography>;

  return (
    <>
      <Typography variant="h4">
        {asset.name}{" "}
        <Chip label={asset.criticality} sx={{ bgcolor: riskColor(asset.criticality), color: "#fff" }} />
      </Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Overview" /><Tab label="Relationships" /><Tab label="Vulnerabilities" />
        <Tab label="Compliance Controls" /><Tab label="History" />
      </Tabs>
      <Box>
        {tab === 0 && (
          <Typography>
            Type: {asset.type} · Environment: {asset.environment} · Owner: {asset.owner ?? "—"}
          </Typography>
        )}
        {tab === 1 && (
          <>
            {topologyError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                Relationship data could not be loaded from Neo4j.
              </Alert>
            )}
            <TopologyGraph graph={topology} focusNodeId={assetId} height={520} />
          </>
        )}
        {/* TODO(P2/P3): Vulnerabilities/Controls tabs -> query respective endpoints */}
        {tab > 1 && <Typography color="text.secondary">Planned for a later implementation phase.</Typography>}
      </Box>
    </>
  );
};
