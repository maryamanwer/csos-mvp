import React, { useEffect, useState } from "react";
import { Card, CardContent, Grid, List, ListItem, ListItemText, Typography } from "@mui/material";
import { topRisks } from "@/services/api";
import { Risk } from "@/types";

const KpiCard = ({ label, value }: { label: string; value: string | number }) => (
  <Card>
    <CardContent>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h4">{value}</Typography>
    </CardContent>
  </Card>
);

export const ExecutiveDashboard = () => {
  const [risks, setRisks] = useState<Risk[]>([]);

  useEffect(() => {
    topRisks(5).then((res) => setRisks(res.data)).catch(() => setRisks([]));
  }, []);

  return (
    <>
      <Typography variant="h4" gutterBottom>Executive Dashboard</Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={3}><KpiCard label="Overall Risk Score" value="—" /></Grid>
        <Grid item xs={3}><KpiCard label="Assets" value="—" /></Grid>
        <Grid item xs={3}><KpiCard label="Open Vulnerabilities" value="—" /></Grid>
        <Grid item xs={3}><KpiCard label="Compliance %" value="—" /></Grid>
      </Grid>
      {/* TODO(P2/P4): replace KPI placeholders with real aggregated values,
          and add risk-trend + compliance-by-framework charts (recharts). */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Top 5 Risks</Typography>
          <List>
            {risks.length === 0 && <ListItem><ListItemText primary="No risk data yet (backend not connected to live DB)." /></ListItem>}
            {risks.map((r) => (
              <ListItem key={r.id}>
                <ListItemText primary={r.title} secondary={`Score: ${r.score} · Status: ${r.status}`} />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    </>
  );
};
