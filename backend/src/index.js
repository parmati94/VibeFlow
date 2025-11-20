import express from 'express';
import cors from 'cors';
import session from 'express-session';
import dotenv from 'dotenv';
import spotifyAuthRoutes from './routes/spotifyAuth.js';
import tidalAuthRoutes from './routes/tidalAuth.js';
import playlistRoutes from './routes/playlists.js';
import syncRoutes from './routes/sync.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors({
  origin: [
    process.env.FRONTEND_URL || 'http://localhost:5173',
    'http://127.0.0.1:5173'
  ],
  credentials: true
}));
app.use(express.json());
app.use(session({
  secret: process.env.SESSION_SECRET || 'default-secret-change-this',
  resave: false,
  saveUninitialized: true, // Changed to true to ensure session is created
  name: 'vibeflow.sid', // Custom name to avoid conflicts
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'lax', // Allow cookies on redirects
    // Don't set domain for local dev - allows both localhost and 127.0.0.1
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));

// Routes
app.use('/auth/spotify', spotifyAuthRoutes);
app.use('/auth/tidal', tidalAuthRoutes);
app.use('/api/playlists', playlistRoutes);
app.use('/api/sync', syncRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Vibeflow API is running' });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

app.listen(PORT, () => {
  console.log(`🚀 Vibeflow backend running on http://localhost:${PORT}`);
});
