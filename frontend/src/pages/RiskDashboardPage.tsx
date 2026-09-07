import React, {useEffect,useState} from 'react';
import {Alert, Chip, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography, Stack} from '@mui/material';
import {api} from '@/services/api';
export const RiskDashboardPage=()=>{
 const [rows,setRows]=useState<any[]>([]);const [error,setError]=useState('');
 useEffect(()=>{api.get('/risk/assessments').then(r=>setRows(r.data)).catch(()=>setError('Unable to calculate risk. Check graph availability.'));},[]);
 return <Stack spacing={2}><Typography variant="h4">Risk Dashboard</Typography>
 {error&&<Alert severity="error">{error}</Alert>}
 <Typography>Scores prioritize assets using active vulnerability severity, business criticality, and exposure. Internal exposure is assumed when unset. This is a prioritization model, not a probability of attack.</Typography>
 <Paper sx={{overflowX:'auto'}}><Table><TableHead><TableRow>{['Asset','Score / 100','Likelihood','Impact','Explanation'].map(h=><TableCell key={h}>{h}</TableCell>)}</TableRow></TableHead>
 <TableBody>{rows.map(r=><TableRow key={r.affected_asset_id}><TableCell>{r.title}</TableCell><TableCell><Chip label={r.score} color={r.score>70?'error':r.score>40?'warning':'success'}/></TableCell><TableCell>{r.likelihood}</TableCell><TableCell>{r.impact}</TableCell><TableCell>{r.explanation}</TableCell></TableRow>)}</TableBody></Table></Paper>
 {!rows.length&&!error&&<Typography>No assets to assess.</Typography>}
 </Stack>;
};
