import express from 'express';
import { createServer } from 'http';
import { ExpressPeerServer } from 'peer';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const server = createServer(app);
const PORT = process.env.PORT || 3000;

// PeerJS Server
const peerServer = ExpressPeerServer(server, {
  debug: true,
  path: '/'
});

app.use('/peerjs', peerServer);

// Serve static files (for production) -- requires 'npm run build' first
app.use(express.static(join(__dirname, 'dist')));

// Fallback for SPA routing
app.use((req, res) => {
  // If dist/index.html exists, serve it. Otherwise tell user to run dev.
  try {
    res.sendFile(join(__dirname, 'dist', 'index.html'));
  } catch (e) {
    res.send('Frontend not built. Run "npm run dev" for development or "npm run build" then start this server.');
  }
});

server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`PeerJS service available at /peerjs`);
});
