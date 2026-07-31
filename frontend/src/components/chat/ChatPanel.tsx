import React, { useState } from "react";
import { Box, Card, CardContent, Chip, List, ListItem, ListItemText, TextField, IconButton } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import { sendChatMessage } from "@/services/api";
import { ChatMessage } from "@/types";

export const ChatPanel = ({ docked = false }: { docked?: boolean }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();

  const send = async () => {
    if (!input.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const { data } = await sendChatMessage(userMsg.content, conversationId);
    setConversationId(data.conversation_id);
    setMessages((prev) => [...prev, { role: "assistant", content: data.reply, agent_trace: data.agent_trace }]);
  };

  return (
    <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <CardContent sx={{ flexGrow: 1, overflowY: "auto" }}>
        <List>
          {messages.map((m, i) => (
            <ListItem key={i} sx={{ flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
              <ListItemText primary={m.content} secondary={m.role === "user" ? "You" : "CSOS AI"} />
              {m.agent_trace && m.agent_trace.map((a) => <Chip key={a} label={a} size="small" sx={{ mr: 0.5 }} />)}
            </ListItem>
          ))}
          {messages.length === 0 && (
            <ListItem>
              <ListItemText primary="Ask about assets, risks, or compliance." secondary="Model reasoning is planned for Phase 3" />
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
        <IconButton onClick={send}><SendIcon /></IconButton>
      </Box>
    </Card>
  );
};
