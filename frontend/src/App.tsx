import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router';
import { AppLayout } from './components/layout/AppLayout';
import { RootRoute } from './routes/root';
import { ChatRoute } from './routes/chat';
import { MeetingRoute } from './routes/meeting';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<RootRoute />} />
          <Route path="/chats/:chatId" element={<ChatRoute />} />
          <Route path="/chats/:chatId/meetings/:meetingId" element={<MeetingRoute />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
