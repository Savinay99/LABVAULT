import dotenv from 'dotenv';
dotenv.config();
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { connectDB } from './config/db.js';
const app = express();
connectDB();

app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '10mb' }));

const authMod = await import('./routes/auth.js');
const themesMod = await import('./routes/themes.js');
app.use('/api/auth', authMod.default);
app.use('/api/themes', themesMod.default);

app.get('/api/health', (_req, res) => res.json({ status: 'ok', db: 'mongodb' }));

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Express server running on port ${PORT}`));
