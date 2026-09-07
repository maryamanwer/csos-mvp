import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { api } from '@/services/api';
export const CustomStandardsPage = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [control, setControl] = useState({id:'', name:'', framework:'', description:'', status:'not_implemented', asset_ids:''});
  const load = () => api.get('/standards').then(r => setHistory(r.data));
  useEffect(() => { load().catch(() => setError('Could not load upload history.')); }, []);
  const submit = async (file?: File) => {
    setBusy(true); setError(''); setNotice('');
    try {
      let response;
      if (file) { const form = new FormData(); form.append('file', file); response = await api.post('/standards/upload', form); }
      else response = await api.post('/standards/controls', {...control, asset_ids:control.asset_ids.split(';').map(v=>v.trim()).filter(Boolean)});
      setNotice(`Processed ${response.data.controls_parsed} control(s).`); await load();
    } catch (e: any) { setError(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Unable to process controls. Check required fields and asset IDs.'); }
    finally { setBusy(false); }
  };
  return <Stack spacing={2}>
    <Typography variant="h4">Custom Standards & Policies</Typography>
    {error && <Alert severity="error">{error}</Alert>}{notice && <Alert severity="success">{notice}</Alert>}
    <Card><CardContent><Stack spacing={2}>
      <Typography>Import CSV, XLSX, JSON, a Word control table, or a text PDF with pipe-separated rows. PDF header: id | name | framework. Scans and free-form policies require conversion before import. Required columns: id, name, framework. Optional: description, status, asset_ids (separated by semicolons). Maximum 10 MB / 5,000 controls.</Typography>
      <Button component="label" variant="contained" disabled={busy}>Upload standard
        <input type="file" hidden accept=".csv,.xlsx,.json,.docx,.pdf" onChange={e=>{const file=e.target.files?.[0]; if(file) void submit(file); e.target.value='';}} />
      </Button>
    </Stack></CardContent></Card>
    <Card><CardContent><Stack spacing={2}>
      <Typography variant="h6">Enter or update a control</Typography>
      <Typography variant="body2">The same framework and reference ID updates an existing control and replaces its asset mappings.</Typography>
      {(['id','name','framework','description','asset_ids'] as const).map(key => <TextField key={key} label={key === 'id' ? 'Reference ID' : key.replace('_', ' ')} value={control[key]} onChange={e=>setControl({...control,[key]:e.target.value})} />)}
      <TextField select label="Status" value={control.status} onChange={e=>setControl({...control,status:e.target.value})}>
        {['not_implemented','partial','implemented'].map(v=><MenuItem key={v} value={v}>{v.replace('_',' ')}</MenuItem>)}
      </TextField>
      <Button disabled={busy || !control.id.trim() || !control.name.trim() || !control.framework.trim()} onClick={()=>submit()} variant="contained">Save control</Button>
    </Stack></CardContent></Card>
    <Typography variant="h6">Import history</Typography>
    {history.map(r=><Typography key={r.id}>{r.file_name} · {r.status} · {r.controls_parsed} controls</Typography>)}
  </Stack>;
};
