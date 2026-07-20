import React from "react";
import { Box, Typography } from "@mui/material";
import { ChatPanel } from "@/components/chat/ChatPanel";

export const ChatAssistantPage = () => {
  return (
    <>
      <Typography variant="h4" gutterBottom>AI Chat Assistant</Typography>
      <Box sx={{ height: "75vh" }}>
        <ChatPanel />
      </Box>
    </>
  );
};
