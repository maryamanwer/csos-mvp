import React,{useEffect,useState} from 'react';
import {Alert,LinearProgress,MenuItem,Stack,TextField,Typography,Card,CardContent} from '@mui/material';
import {api} from '@/services/api';
export const ComplianceDashboardPage=()=>{
 const [coverage,setCoverage]=useState<any[]>([]);const [gaps,setGaps]=useState<any[]>([]);const [framework,setFramework]=useState('');const [error,setError]=useState('');
 useEffect(()=>{Promise.all([api.get('/compliance/coverage'),api.get('/compliance/gaps')]).then(([a,b])=>{setCoverage(a.data);setGaps(b.data);}).catch(()=>setError('Unable to load compliance evidence.'));},[]);
 return <Stack spacing={2}><Typography variant="h4">Compliance Dashboard</Typography>{error&&<Alert severity="error">{error}</Alert>}
 <Typography>Coverage reflects implementation status of controls in your graph. A gap also includes controls without asset mappings; coverage alone is not an audit certification.</Typography>
 <TextField select label="Framework" value={framework} onChange={e=>setFramework(e.target.value)}><MenuItem value="">All frameworks</MenuItem>{coverage.map(c=><MenuItem key={c.framework} value={c.framework}>{c.framework}</MenuItem>)}</TextField>
 {coverage.filter(c=>!framework||c.framework===framework).map(c=><Card key={c.framework}><CardContent><Typography>{c.framework} · {c.controls_met}/{c.total_controls} implemented · {c.coverage_pct}%</Typography><LinearProgress variant="determinate" value={c.coverage_pct}/></CardContent></Card>)}
 <Typography variant="h6">Control gaps</Typography>
 {gaps.filter(g=>!framework||g.framework===framework).map(g=><Alert severity="warning" key={g.framework+g.id}>{g.name||g.id} · {g.framework} · {g.reason}</Alert>)}
 {!coverage.length&&!error&&<Typography>No frameworks in the graph yet.</Typography>}
 </Stack>;
};
