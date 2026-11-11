import express from 'express';
import memoryStore from '../memoryStore.js';

const router = express.Router();

router.get('/', async (_req, res) => {
  res.json(await memoryStore.getThemes());
});

export default router;
