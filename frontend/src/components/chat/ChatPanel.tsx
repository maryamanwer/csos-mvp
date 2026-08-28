import React, { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, List, ListItem, ListItemText, TextField, IconButton, Stack, Typography } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import { getChatConversationMessages, listChatConversations, sendChatMessage } from "@/services/api";
import { ChatConversation, ChatMessage } from "@/types";

export const ChatPanel = ({ docked = false }: { docked?: boolean }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const restore = async () => {
      try {
        const response = await listChatConversations();
        const latest = (response.data as ChatConversation[])[0];
        if (!latest) return;
        const history = await getChatConversationMessages(latest.id);
        setConversationId(latest.id);
        setMessages(history.data as ChatMessage[]);
      } catch {
        // A new conversation remains available even if history cannot be loaded.
      }
    };
    void restore();
  }, []);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true); setError(null);
    try {
      const { data } = await sendChatMessage(userMsg.content, conversationId);
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, {
        role: "assistant", content: data.reply,
        agent_trace: data.agent_trace, citations: data.citations,
      }]);
    } catch {
      setError("CSOS could not produce a response. Check the API and local-model status.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 2, pt: 1.5 }}>
        <Typography fontWeight={700}>Grounded CSOS Assistant</Typography>
        <Button size="small" onClick={() => { setMessages([]); setConversationId(undefined); setError(null); }}>New chat</Button>
      </Stack>
      <CardContent sx={{ flexGrow: 1, overflowY: "auto" }}>
        {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}
        <List>
          {messages.map((m, i) => (
            <ListItem key={i} sx={{ flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
              <ListItemText primary={m.content} secondary={m.role === "user" ? "You" : "CSOS AI"} />
              {m.agent_trace && m.agent_trace.map((a) => <Chip key={a} label={a} size="small" sx={{ mr: 0.5 }} />)}
              {m.citations?.map((citation) => <Chip
                key={`${citation.entity_type}-${citation.entity_id}`}
                label={`${citation.label} · ${citation.entity_id}`}
                size="small" variant="outlined" sx={{ mr: 0.5, mt: 0.5 }}
              />)}
            </ListItem>
          ))}
          {messages.length === 0 && (
            <ListItem>
              <ListItemText primary="Ask about assets, risks, findings, attack paths, or compliance." secondary="Grounded by CSOS specialist agents and the Cyber Knowledge Graph" />
            </ListItem>
          )}
        </List>
      </CardContent>
      <Box sx={{ display: "flex", p: 1, borderTop: "1px solid #eee" }}>
        <TextField
          fullWidth size="small" placeholder="Ask CSOS AI…" value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <IconButton onClick={send} disabled={sending || !input.trim()}><SendIcon /></IconButton>
      </Box>
    </Card>
  );
};
