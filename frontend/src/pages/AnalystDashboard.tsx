import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from "@mui/material";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { analystDashboard } from "@/services/api";
import { InvestigationItem } from "@/types";
import { riskColor } from "@/theme";

export const AnalystDashboard = () => {
  const [items, setItems] = useState<InvestigationItem[]>([]);
  const [selected, setSelected] = useState<InvestigationItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analystDashboard()
      .then((response) => {
        setItems(response.data);
        setSelected(response.data[0] ?? null);
      })
      .catch(() => setError("The investigation queue could not be loaded."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Typography variant="h4" gutterBottom>Analyst Dashboard</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading ? <CircularProgress /> : (
        <Grid container spacing={2}>
          <Grid item xs={12} lg={4}>
            <Card sx={{ height: 560, overflow: "auto" }}>
              <CardContent>
                <Typography variant="h6">Investigation Queue</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {items.length} prioritized open items
                </Typography>
                <List disablePadding>
                  {items.map((item) => (
                    <ListItemButton
                      key={`${item.item_type}-${item.id}`}
                      selected={selected?.id === item.id}
                      onClick={() => setSelected(item)}
                      divider
                    >
                      <ListItemText primary={item.title} secondary={`${item.item_type} · ${item.status}`} />
                      <Chip
                        size="small"
                        label={Math.round(item.priority_score)}
                        sx={{ bgcolor: riskColor(item.severity), color: "white" }}
                      />
                    </ListItemButton>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} lg={4}>
            <Card sx={{ height: 560 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Investigation Detail</Typography>
                {selected ? (
                  <Box sx={{ display: "grid", gap: 2 }}>
                    <Typography variant="h5">{selected.title}</Typography>
                    <Box><Chip label={selected.item_type} /> <Chip label={selected.severity} sx={{ bgcolor: riskColor(selected.severity), color: "white" }} /></Box>
                    <Typography><strong>Priority:</strong> {selected.priority_score}</Typography>
                    <Typography><strong>Status:</strong> {selected.status}</Typography>
                    <Typography><strong>Reference:</strong> {selected.reference ?? "Not assigned"}</Typography>
                    <Typography><strong>Affected assets:</strong> {selected.asset_ids.join(", ") || "None linked"}</Typography>
                  </Box>
                ) : <Typography color="text.secondary">No open investigation items.</Typography>}
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} lg={4}>
            <Box sx={{ height: 560 }}><ChatPanel docked /></Box>
          </Grid>
        </Grid>
      )}
    </>
  );
};
