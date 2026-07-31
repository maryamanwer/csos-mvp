import React, { useEffect, useState } from "react";
import {
  Alert,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  List,
  ListItem,
  ListItemText,
  Typography,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { executiveDashboard } from "@/services/api";
import { ExecutiveSummary } from "@/types";
import { riskColor } from "@/theme";

// Recharts 2 exposes several legacy class component declarations that are not
// accepted as JSX elements by newer TypeScript React typings. Runtime behavior
// is unaffected, so adapt those declarations at this boundary.
const ChartBar = Bar as unknown as React.ComponentType<Record<string, unknown>>;
const ChartTooltip = Tooltip as unknown as React.ComponentType<Record<string, unknown>>;
const ChartXAxis = XAxis as unknown as React.ComponentType<Record<string, unknown>>;
const ChartYAxis = YAxis as unknown as React.ComponentType<Record<string, unknown>>;

const KpiCard = ({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) => (
  <Card sx={{ height: "100%" }}>
    <CardContent>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h4">{value}{suffix}</Typography>
    </CardContent>
  </Card>
);

export const ExecutiveDashboard = () => {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    executiveDashboard()
      .then((response) => setSummary(response.data))
      .catch(() => setError("Dashboard data could not be loaded. Confirm that Neo4j is running."));
  }, []);

  if (!summary && !error) return <CircularProgress />;

  return (
    <>
      <Typography variant="h4" gutterBottom>Executive Dashboard</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {summary && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} lg={3}><KpiCard label="Overall Risk Score" value={summary.overall_risk_score} /></Grid>
            <Grid item xs={12} sm={6} lg={3}><KpiCard label="Assets" value={summary.asset_count} /></Grid>
            <Grid item xs={12} sm={6} lg={3}><KpiCard label="Open Vulnerabilities" value={summary.open_vulnerability_count} /></Grid>
            <Grid item xs={12} sm={6} lg={3}><KpiCard label="Compliance" value={summary.compliance_pct} suffix="%" /></Grid>
          </Grid>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Assets by Criticality</Typography>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={summary.asset_criticality}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <ChartXAxis dataKey="label" />
                      <ChartYAxis allowDecimals={false} />
                      <ChartTooltip />
                      <ChartBar dataKey="value" name="Assets" fill="#1f4d7a" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Vulnerabilities by Severity</Typography>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={summary.vulnerability_severity}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <ChartXAxis dataKey="label" />
                      <ChartYAxis allowDecimals={false} />
                      <ChartTooltip />
                      <ChartBar dataKey="value" name="Vulnerabilities" fill="#c62828" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={2}>
            <Grid item xs={12} md={7}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Top Risks</Typography>
                  <List disablePadding>
                    {summary.top_risks.map((risk) => (
                      <ListItem key={risk.id} divider secondaryAction={
                        <Chip label={risk.score} sx={{ bgcolor: riskColor(risk.impact), color: "white" }} />
                      }>
                        <ListItemText
                          primary={risk.title}
                          secondary={`Impact: ${risk.impact} · Status: ${risk.status}`}
                        />
                      </ListItem>
                    ))}
                    {summary.top_risks.length === 0 && <ListItem><ListItemText primary="No open risks" /></ListItem>}
                  </List>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={5}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Framework Coverage</Typography>
                  <List disablePadding>
                    {summary.compliance_frameworks.map((framework) => (
                      <ListItem key={framework.framework} divider>
                        <ListItemText
                          primary={framework.framework}
                          secondary={`${framework.controls_met} of ${framework.total_controls} controls implemented`}
                        />
                        <Typography fontWeight={700}>{framework.coverage_pct}%</Typography>
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </>
  );
};
