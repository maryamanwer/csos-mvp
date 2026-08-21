import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Divider,
  Drawer,
  FormControl,
  Grid,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import RefreshIcon from "@mui/icons-material/Refresh";
import SaveIcon from "@mui/icons-material/Save";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { useNavigate } from "react-router-dom";
import {
  exportSecurityFindings,
  getSecurityFinding,
  listSecurityFindings,
} from "@/services/api";
import {
  FindingDetail,
  FindingsSummary,
  SecurityFinding,
  SecurityFindingsPage as FindingsPageData,
} from "@/types";

type SortDirection = "asc" | "desc";

interface FindingFilters {
  search: string;
  risk_level: string;
  criticality: string;
  severity: string;
  edr_coverage: string;
  asset_type: string;
  owner: string;
  status: string;
  data_source: string;
}

interface SavedView {
  id: string;
  name: string;
  filters: FindingFilters;
  sortBy: string;
  sortDirection: SortDirection;
}

const EMPTY_FILTERS: FindingFilters = {
  search: "",
  risk_level: "",
  criticality: "",
  severity: "",
  edr_coverage: "",
  asset_type: "",
  owner: "",
  status: "",
  data_source: "",
};

const EMPTY_SUMMARY: FindingsSummary = {
  total_findings: 0,
  critical_findings: 0,
  sla_breaches: 0,
  critical_assets_without_edr: 0,
  critical_vulnerabilities_on_critical_assets: 0,
  outdated_security_agents: 0,
  assets_missing_controls: 0,
  unmanaged_assets: 0,
};

const DATA_SOURCES = [
  "EDR / XDR",
  "Vulnerability Management",
  "CMDB",
  "Active Directory / Identity",
  "SIEM",
  "Cloud platforms",
  "Network discovery",
  "Firewall",
  "Patch Management",
];

const ASSET_TYPES = [
  "server",
  "application",
  "database",
  "firewall",
  "router",
  "switch",
  "endpoint",
  "workstation",
  "cloud_resource",
  "other",
];

const riskTone = (level: string) => {
  if (level === "high" || level === "critical") return { bg: "#FDECEC", fg: "#B42318", border: "#D92D20" };
  if (level === "medium") return { bg: "#FFF3E0", fg: "#B54708", border: "#F79009" };
  return { bg: "#ECFDF3", fg: "#027A48", border: "#12B76A" };
};

const formatDate = (value?: string) => value
  ? new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "2-digit" }).format(new Date(value))
  : "—";

const loadSavedViews = (): SavedView[] => {
  try {
    return JSON.parse(localStorage.getItem("csos_findings_saved_views") ?? "[]") as SavedView[];
  } catch {
    return [];
  }
};

const SummaryCard = ({ label, value, tone }: { label: string; value: number; tone: string }) => (
  <Card variant="outlined" sx={{ height: "100%", borderTop: `4px solid ${tone}` }}>
    <CardContent>
      <Typography variant="h4" fontWeight={700}>{value.toLocaleString()}</Typography>
      <Typography color="text.secondary" variant="body2">{label}</Typography>
    </CardContent>
  </Card>
);

export const SecurityFindingsPage = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<FindingFilters>(EMPTY_FILTERS);
  const [items, setItems] = useState<SecurityFinding[]>([]);
  const [summary, setSummary] = useState<FindingsSummary>(EMPTY_SUMMARY);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [sortBy, setSortBy] = useState("risk_score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [savedViews, setSavedViews] = useState<SavedView[]>(loadSavedViews);
  const [selectedView, setSelectedView] = useState("");
  const [detail, setDetail] = useState<FindingDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const requestParams = useMemo(() => ({
    ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value)),
    sort_by: sortBy,
    sort_direction: sortDirection,
    page: page + 1,
    page_size: pageSize,
  }), [filters, page, pageSize, sortBy, sortDirection]);

  const loadFindings = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const { data } = await listSecurityFindings(requestParams) as { data: FindingsPageData };
      setItems(data.items);
      setTotal(data.total);
      setSummary(data.summary);
    } catch {
      setMessage("Security findings could not be loaded from the Cyber Knowledge Graph.");
    } finally {
      setLoading(false);
    }
  }, [requestParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadFindings(), 250);
    return () => window.clearTimeout(timer);
  }, [loadFindings]);

  const updateFilter = (key: keyof FindingFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(0);
  };

  const requestSort = (field: string) => {
    if (sortBy === field) setSortDirection((current) => current === "asc" ? "desc" : "asc");
    else {
      setSortBy(field);
      setSortDirection("asc");
    }
    setPage(0);
  };

  const saveView = () => {
    const name = window.prompt("Name this CSOS findings view");
    if (!name?.trim()) return;
    const next = [
      ...savedViews,
      { id: crypto.randomUUID(), name: name.trim(), filters, sortBy, sortDirection },
    ];
    setSavedViews(next);
    localStorage.setItem("csos_findings_saved_views", JSON.stringify(next));
  };

  const applySavedView = (id: string) => {
    setSelectedView(id);
    const view = savedViews.find((item) => item.id === id);
    if (!view) return;
    setFilters(view.filters);
    setSortBy(view.sortBy);
    setSortDirection(view.sortDirection);
    setPage(0);
  };

  const exportCsv = async () => {
    try {
      const exportParams = {
        ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value)),
        sort_by: sortBy,
        sort_direction: sortDirection,
      };
      const { data } = await exportSecurityFindings(exportParams);
      const url = URL.createObjectURL(data as Blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "csos-security-findings.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setMessage("CSV export could not be generated.");
    }
  };

  const openFinding = async (finding: SecurityFinding) => {
    setDetailLoading(true);
    setDetail(null);
    try {
      const { data } = await getSecurityFinding(finding.finding_id, finding.asset_id);
      setDetail(data as FindingDetail);
    } catch {
      setMessage("Finding details could not be loaded.");
    } finally {
      setDetailLoading(false);
    }
  };

  const sortableHeader = (label: string, field: string) => (
    <TableSortLabel
      active={sortBy === field}
      direction={sortBy === field ? sortDirection : "asc"}
      onClick={() => requestSort(field)}
    >{label}</TableSortLabel>
  );

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return (
    <Box>
      <Stack direction={{ xs: "column", lg: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Security Findings</Typography>
          <Typography color="text.secondary">
            Correlated vulnerabilities, asset context, controls, risk, remediation, and connected security sources.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => void loadFindings()}>Refresh</Button>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => void exportCsv()}>Export CSV</Button>
          <Button variant="contained" startIcon={<SaveIcon />} onClick={saveView}>Save View</Button>
        </Stack>
      </Stack>

      {message && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setMessage(null)}>{message}</Alert>}

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}><SummaryCard label="Unified Findings" value={summary.total_findings} tone="#1E3A5F" /></Grid>
        <Grid item xs={6} md={3}><SummaryCard label="Critical Findings" value={summary.critical_findings} tone="#D92D20" /></Grid>
        <Grid item xs={6} md={3}><SummaryCard label="SLA Breaches" value={summary.sla_breaches} tone="#F79009" /></Grid>
        <Grid item xs={6} md={3}><SummaryCard label="Critical Assets Without EDR" value={summary.critical_assets_without_edr} tone="#7A5AF8" /></Grid>
      </Grid>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }}>
          <TextField
            size="small"
            label="Search finding, CVE, asset, hostname, IP, or owner"
            value={filters.search}
            onChange={(event) => updateFilter("search", event.target.value)}
            sx={{ flex: 1, minWidth: 320 }}
          />
          <Button
            variant={activeFilterCount > (filters.search ? 1 : 0) ? "contained" : "outlined"}
            startIcon={<FilterAltIcon />}
            onClick={() => setFiltersOpen((value) => !value)}
          >Advanced Filters{activeFilterCount ? ` (${activeFilterCount})` : ""}</Button>
          <FormControl size="small" sx={{ minWidth: 210 }}>
            <InputLabel>Saved views</InputLabel>
            <Select label="Saved views" value={selectedView} onChange={(event) => applySavedView(event.target.value)}>
              <MenuItem value="">None</MenuItem>
              {savedViews.map((view) => <MenuItem key={view.id} value={view.id}>{view.name}</MenuItem>)}
            </Select>
          </FormControl>
          <Button onClick={() => { setFilters(EMPTY_FILTERS); setSelectedView(""); setPage(0); }}>Clear</Button>
        </Stack>

        <Collapse in={filtersOpen}>
          <Divider sx={{ my: 2 }} />
          <Grid container spacing={1.5}>
            {[
              ["risk_level", "Risk Level", ["high", "medium", "low"]],
              ["criticality", "Asset Criticality", ["critical", "high", "medium", "low"]],
              ["severity", "CVSS Severity", ["critical", "high", "medium", "low"]],
              ["edr_coverage", "EDR Coverage", ["covered", "outdated", "missing"]],
              ["asset_type", "Asset Type", ASSET_TYPES],
              ["status", "Status", ["open", "in_progress", "resolved", "accepted_risk"]],
              ["data_source", "Data Source", DATA_SOURCES],
            ].map(([key, label, values]) => (
              <Grid item xs={12} sm={6} md={3} key={key as string}>
                <TextField
                  select fullWidth size="small" label={label as string}
                  value={filters[key as keyof FindingFilters]}
                  onChange={(event) => updateFilter(key as keyof FindingFilters, event.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  {(values as string[]).map((value) => <MenuItem key={value} value={value}>{value.replace(/_/g, " ")}</MenuItem>)}
                </TextField>
              </Grid>
            ))}
            <Grid item xs={12} sm={6} md={3}>
              <TextField fullWidth size="small" label="Asset Owner" value={filters.owner} onChange={(event) => updateFilter("owner", event.target.value)} />
            </Grid>
          </Grid>
        </Collapse>
      </Paper>

      <Paper variant="outlined" sx={{ p: 1.5, mb: 2, bgcolor: "#F8FAFC" }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <WarningAmberIcon color="warning" />
          <Typography fontWeight={700}>Security gaps</Typography>
          <Chip size="small" label={`${summary.critical_vulnerabilities_on_critical_assets} critical exposures`} />
          <Chip size="small" label={`${summary.outdated_security_agents} outdated agents`} />
          <Chip size="small" label={`${summary.assets_missing_controls} assets missing controls`} />
          <Chip size="small" label={`${summary.unmanaged_assets} unmanaged assets`} />
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        {loading && <LinearProgress />}
        <TableContainer sx={{ maxHeight: "calc(100vh - 390px)" }}>
          <Table stickyHeader size="small" sx={{ minWidth: 3050 }}>
            <TableHead><TableRow>
              <TableCell sx={{ minWidth: 150 }}>{sortableHeader("Finding ID / CVE", "finding_id")}</TableCell>
              <TableCell sx={{ minWidth: 190 }}>{sortableHeader("Preferred Hostname", "asset_name")}</TableCell>
              <TableCell>{sortableHeader("Asset Type", "asset_type")}</TableCell>
              <TableCell>{sortableHeader("Criticality", "asset_criticality")}</TableCell>
              <TableCell sx={{ minWidth: 150 }}>{sortableHeader("Owner", "asset_owner")}</TableCell>
              <TableCell>IP Address</TableCell><TableCell sx={{ minWidth: 190 }}>Operating System</TableCell>
              <TableCell>EDR Status</TableCell><TableCell sx={{ minWidth: 160 }}>EDR Product</TableCell>
              <TableCell>{sortableHeader("Severity", "severity")}</TableCell>
              <TableCell>{sortableHeader("CVSS", "cvss_score")}</TableCell>
              <TableCell>{sortableHeader("Risk Score", "risk_score")}</TableCell>
              <TableCell>{sortableHeader("Risk Level", "risk_level")}</TableCell>
              <TableCell>{sortableHeader("Status", "status")}</TableCell>
              <TableCell>{sortableHeader("First Detected", "first_detected")}</TableCell>
              <TableCell>{sortableHeader("Last Seen", "last_seen")}</TableCell>
              <TableCell sx={{ minWidth: 150 }}>{sortableHeader("SLA / Remediation", "sla_due_at")}</TableCell>
              <TableCell sx={{ minWidth: 230 }}>Data Sources</TableCell>
              <TableCell sx={{ minWidth: 320 }}>Recommended Remediation</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {items.map((item) => {
                const risk = riskTone(item.risk_level);
                const severity = riskTone(item.severity);
                return (
                  <TableRow key={`${item.finding_id}-${item.asset_id}`} hover onClick={() => void openFinding(item)} sx={{ cursor: "pointer" }}>
                    <TableCell><Typography color="primary" fontWeight={700} variant="body2">{item.cve_id ?? item.finding_id}</Typography></TableCell>
                    <TableCell>
                      <Typography fontWeight={600} variant="body2">{item.preferred_hostname ?? item.asset_name}</Typography>
                      <Typography variant="caption" color="text.secondary">{item.asset_name}</Typography>
                    </TableCell>
                    <TableCell>{item.asset_type.replace(/_/g, " ")}</TableCell>
                    <TableCell><Chip size="small" label={item.asset_criticality} variant="outlined" /></TableCell>
                    <TableCell>{item.asset_owner ?? "Unassigned"}</TableCell>
                    <TableCell>{item.ip_address ?? "—"}</TableCell><TableCell>{item.operating_system ?? "Unknown"}</TableCell>
                    <TableCell><Chip size="small" label={item.edr_status.replace(/_/g, " ")} color={item.edr_status === "active" ? "success" : item.edr_status === "outdated" ? "warning" : "error"} /></TableCell>
                    <TableCell>{item.edr_product ?? "—"}</TableCell>
                    <TableCell><Chip size="small" label={item.severity} sx={{ bgcolor: severity.bg, color: severity.fg, border: `1px solid ${severity.border}` }} /></TableCell>
                    <TableCell>{item.cvss_score.toFixed(1)}</TableCell><TableCell>{item.risk_score.toFixed(0)}</TableCell>
                    <TableCell><Chip size="small" label={item.risk_level} sx={{ bgcolor: risk.bg, color: risk.fg, border: `1px solid ${risk.border}` }} /></TableCell>
                    <TableCell>{item.status.replace(/_/g, " ")}</TableCell>
                    <TableCell>{formatDate(item.first_detected)}</TableCell><TableCell>{formatDate(item.last_seen)}</TableCell>
                    <TableCell>
                      <Typography variant="body2" color={item.sla_status === "breached" ? "error" : "text.primary"}>{item.sla_status.replace(/_/g, " ")}</Typography>
                      <Typography variant="caption" color="text.secondary">{formatDate(item.sla_due_at)}</Typography>
                    </TableCell>
                    <TableCell><Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>{item.data_sources.map((source) => <Chip size="small" variant="outlined" key={source} label={source} />)}</Stack></TableCell>
                    <TableCell><Tooltip title={item.recommended_remediation ?? "No remediation recorded"}><Typography variant="body2" noWrap>{item.recommended_remediation ?? "—"}</Typography></Tooltip></TableCell>
                  </TableRow>
                );
              })}
              {!loading && items.length === 0 && <TableRow><TableCell colSpan={19} align="center" sx={{ py: 8 }}>No correlated findings match this view.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div" count={total} page={page} rowsPerPage={pageSize}
          onPageChange={(_, value) => setPage(value)}
          onRowsPerPageChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Paper>

      <Drawer anchor="right" open={detailLoading || Boolean(detail)} onClose={() => { setDetail(null); setDetailLoading(false); }}>
        <Box sx={{ width: { xs: 360, sm: 520 }, p: 3 }}>
          {detailLoading && <LinearProgress />}
          {detail && <Stack spacing={2.5}>
            <Box>
              <Typography variant="overline" color="text.secondary">Security Finding</Typography>
              <Typography variant="h5" fontWeight={700}>{detail.finding.cve_id ?? detail.finding.finding_id}</Typography>
              <Typography color="text.secondary">{detail.finding.title}</Typography>
            </Box>
            <Stack direction="row" spacing={1}>
              <Chip label={detail.finding.risk_level} sx={{ bgcolor: riskTone(detail.finding.risk_level).bg, color: riskTone(detail.finding.risk_level).fg }} />
              <Chip label={`CVSS ${detail.finding.cvss_score}`} variant="outlined" />
              <Chip label={detail.finding.status.replace(/_/g, " ")} variant="outlined" />
            </Stack>
            <Divider />
            <Box>
              <Typography variant="h6">Relationship chain</Typography>
              <Stack spacing={1} sx={{ mt: 1 }}>
                {detail.relationship_chain.map((step, index) => (
                  <Paper variant="outlined" sx={{ p: 1.25 }} key={`${step.from}-${index}`}>
                    <Typography variant="body2"><strong>{step.from}</strong> → {step.relationship.replace(/_/g, " ")} → <strong>{step.to}</strong></Typography>
                  </Paper>
                ))}
              </Stack>
            </Box>
            <Box>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">Asset</Typography>
                <Button size="small" onClick={() => navigate(`/assets/${detail.finding.asset_id}`)}>Open Asset</Button>
              </Stack>
              <Grid container spacing={1} sx={{ mt: 0.5 }}>
                {[
                  ["Name", detail.finding.asset_name], ["Hostname", detail.finding.preferred_hostname],
                  ["IP", detail.finding.ip_address], ["Type", detail.finding.asset_type],
                  ["Criticality", detail.finding.asset_criticality], ["Owner", detail.finding.asset_owner],
                  ["OS", detail.finding.operating_system], ["EDR", `${detail.finding.edr_status}${detail.finding.edr_product ? ` · ${detail.finding.edr_product}` : ""}`],
                ].map(([label, value]) => <Grid item xs={6} key={label}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="body2">{value ?? "—"}</Typography></Grid>)}
              </Grid>
            </Box>
            <Box><Typography variant="h6">Recommended remediation</Typography><Typography variant="body2">{detail.finding.recommended_remediation ?? "No remediation has been recorded."}</Typography></Box>
            <Box><Typography variant="h6">Security controls</Typography><Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>{detail.controls.length ? detail.controls.map((control, index) => <Chip key={String(control.id ?? index)} label={String(control.name ?? control.id ?? "Control")} />) : <Typography variant="body2" color="error">No mapped controls</Typography>}</Stack></Box>
            <Box><Typography variant="h6">Risks</Typography>{detail.risks.length ? detail.risks.map((risk, index) => <Typography variant="body2" key={String(risk.id ?? index)}>• {String(risk.title ?? risk.id)} · score {String(risk.score ?? "—")}</Typography>) : <Typography variant="body2">No explicit risk relationship.</Typography>}</Box>
            <Box><Typography variant="h6">Associated identities</Typography>{detail.owner_identities.length ? detail.owner_identities.map((identity, index) => <Typography variant="body2" key={String(identity.id ?? index)}>• {String(identity.name ?? identity.username ?? identity.id)}</Typography>) : <Typography variant="body2">No identity relationship recorded.</Typography>}</Box>
          </Stack>}
        </Box>
      </Drawer>
    </Box>
  );
};
