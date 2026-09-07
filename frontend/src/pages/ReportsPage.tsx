import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { api, generateReport } from '@/services/api';
export const ReportsPage = () => {
  const [kind, setKind] = useState('risk');
  const [format, setFormat] = useState('pdf');
  const [reports, setReports] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const load = () => api.get('/reports').then(r => setReports(r.data));
  useEffect(() => { load().catch(() => setError('Could not load report history.')); }, []);
  const download = async (report: any) => {
    try {
      const {data} = await api.get(`/reports/${report.id}/download`, {responseType: 'blob'});
      const url = URL.createObjectURL(data);
      const a = document.createElement('a'); a.href = url; a.download = `csos-${report.report_type}.${report.format}`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setError('Download failed. Please try again.'); }
  };
  const generate = async () => {
    setBusy(true); setError('');
    try { await generateReport(kind, format); await load(); }
    catch { setError('Report generation failed. Check that the database is available.'); }
    finally { setBusy(false); }
  };
  return <Stack spacing={2}>
    <Typography variant="h4">Reports</Typography>
    {error && <Alert severity="error">{error}</Alert>}
    <Card><CardContent><Stack spacing={2}>
      <TextField select label="Report type" value={kind} onChange={e => setKind(e.target.value)}>
        {['risk','compliance','asset'].map(v => <MenuItem key={v} value={v}>{v}</MenuItem>)}
      </TextField>
      <TextField select label="Format" value={format} onChange={e => setFormat(e.target.value)}>
        <MenuItem value="pdf">PDF</MenuItem><MenuItem value="xlsx">Excel</MenuItem>
      </TextField>
      <Button variant="contained" disabled={busy} onClick={generate}>{busy ? 'Generating…' : 'Generate report'}</Button>
    </Stack></CardContent></Card>
    <Typography variant="h6">Your report history</Typography>
    {!reports.length && <Typography>No reports generated yet.</Typography>}
    {reports.map(r => <Card key={r.id}><CardContent><Stack direction="row" justifyContent="space-between">
      <Typography>{r.report_type} · {r.format.toUpperCase()} · {new Date(r.created_at).toLocaleString()}</Typography>
      <Button onClick={() => download(r)}>Download</Button>
    </Stack></CardContent></Card>)}
  </Stack>;
};
