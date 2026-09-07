import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, List, ListItem, ListItemText, MenuItem, TextField, Typography } from '@mui/material';
import { api } from '@/services/api';
export const ChatPanel = ({docked = false}: {docked?: boolean}) => {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState(''); const [conversation, setConversation] = useState<string>();
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [models, setModels] = useState<string[]>([]); const [model, setModel] = useState('');
  const [runtime, setRuntime] = useState('checking');
  useEffect(()=>{api.get('/ai/models').then(r=>{setModels(r.data.enabled);setModel(r.data.default);setRuntime(r.data.status);}).catch(()=>setRuntime('unavailable'));},[]);
  const send = async () => {
    if (!input.trim() || busy) return;
    const message = input.trim(); setBusy(true); setError('');
    try {
      const {data} = await api.post('/chat',{message, conversation_id:conversation, model});
      setMessages(prev=>[...prev,{role:'user',content:message},{role:'assistant',content:data.reply, trace:data.agent_trace, citations:data.citations}]);
      setConversation(data.conversation_id); setInput('');
    } catch(e:any) { setError(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Unable to get an answer. Please retry.'); }
    finally {setBusy(false);}
  };
  return <Card sx={{height:'100%',display:'flex',flexDirection:'column'}}>
    <CardContent sx={{flexGrow:1,overflowY:'auto'}}>
      <Typography variant="caption">AI runtime: {runtime}</Typography>
      {!!models.length && <TextField fullWidth select label="Model" value={model} onChange={e=>setModel(e.target.value)} sx={{mt:1}}>{models.map(m=><MenuItem key={m} value={m}>{m}</MenuItem>)}</TextField>}
      {error && <Alert severity="error">{error}</Alert>}
      <List>{messages.map((m,i)=><ListItem key={i} sx={{display:'block'}}>
        <ListItemText primary={m.content} secondary={m.role==='user'?'You':'CSOS AI'} sx={{whiteSpace:'pre-wrap'}} />
        {m.trace?.map((t:string)=><Chip key={t} label={t} size="small" />)}
        {!!m.citations?.length && <Typography variant="caption" display="block">Retrieved evidence: {m.citations.map((c:any)=>`${c.label} [${c.id}]`).join(', ')}</Typography>}
      </ListItem>)}</List>
      {!messages.length && <Typography>Ask about assets, risks, or compliance. Answers use evidence available to your role.</Typography>}
      {busy && <Typography role="status">Retrieving evidence and preparing an answer…</Typography>}
    </CardContent>
    <Box sx={{display:'flex',p:1,gap:1}}>
      <TextField fullWidth label="Ask CSOS" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')void send();}} disabled={busy} />
      <Button onClick={send} disabled={busy || !input.trim()}>Send</Button>
    </Box>
  </Card>;
};
