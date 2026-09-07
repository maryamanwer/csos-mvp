import React, {useEffect, useState} from 'react';
import {Alert, Button, Card, CardContent, Stack, TextField, Typography} from '@mui/material';
import {api} from '@/services/api';
export const WorkflowsPage = () => {
  const [items,setItems]=useState<any[]>([]); const [notes,setNotes]=useState<any[]>([]);
  const [title,setTitle]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false);
  const load=async()=>{const [a,b]=await Promise.all([api.get('/workflows'),api.get('/notifications')]);setItems(a.data);setNotes(b.data);};
  useEffect(()=>{load().catch(()=>setError('Could not load workflows.'));},[]);
  const run=async(action:()=>Promise<any>)=>{setBusy(true);setError('');try{await action();await load();}catch{setError('Action failed. Refresh and retry.');}finally{setBusy(false);}};
  const next:Record<string,string[]>={open:['in_progress'],in_progress:['open','resolved'],resolved:['in_progress','closed'],closed:['open']};
  return <Stack spacing={2}><Typography variant="h4">Workflows</Typography>
    {error&&<Alert severity="error">{error}</Alert>}
    <TextField label="Remediation task" value={title} onChange={e=>setTitle(e.target.value)}/>
    <Button disabled={busy||!title.trim()} onClick={()=>run(async()=>{await api.post('/workflows',{title});setTitle('');})}>Create task</Button>
    {items.map(t=><Card key={t.id}><CardContent><Typography>{t.title} · {t.status.replace('_',' ')}</Typography>
      {next[t.status].map(s=><Button key={s} disabled={busy} onClick={()=>run(()=>api.patch(`/workflows/${t.id}`,{status:s,expected_status:t.status}))}>{s.replace('_',' ')}</Button>)}
    </CardContent></Card>)}
    <Typography variant="h6">Notifications</Typography>
    {notes.map(n=><Alert severity="info" key={n.id} action={!n.read&&<Button disabled={busy} onClick={()=>run(()=>api.patch(`/notifications/${n.id}/read`))}>Mark read</Button>}>{n.body}</Alert>)}
  </Stack>;
};
