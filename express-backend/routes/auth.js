import express from 'express';
import memoryStore from '../memoryStore.js';
import jwt from 'jsonwebtoken';
import JWT_SECRET from '../config/jwtSecret.js';

const router = express.Router();

const signToken = (id) => jwt.sign({ id }, JWT_SECRET, { expiresIn: '7d' });

router.post('/register', async (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email || !password) return res.status(400).json({ msg: 'Please enter all fields' });
  if (await memoryStore.findUserByEmail(email)) return res.status(400).json({ msg: 'User already exists' });
  const user = await memoryStore.createUser({ name, email, password });
  const token = signToken(user._id);
  res.json({ token, user: { id: user._id, name: user.name, email: user.email } });
});

router.post('/login', async (req, res) => {
  const { email, password } = req.body;
  const user = await memoryStore.findUserByEmail(email);
  if (!user || !(await memoryStore.comparePassword(password, user.password))) return res.status(400).json({ msg: 'Invalid credentials' });
  const token = signToken(user._id);
  res.json({ token, user: { id: user._id, name: user.name, email: user.email } });
});

router.get('/me', async (req, res) => {
  const token = req.header('x-auth-token') || (req.headers.authorization && req.headers.authorization.replace('Bearer ', ''));
  if (!token) return res.status(401).json({ msg: 'No token, authorization denied' });
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const user = await memoryStore.findUserById(decoded.id);
    if (!user) return res.status(401).json({ msg: 'User not found' });
    const { password, ...rest } = user;
    res.json(rest);
  } catch (err) {
    res.status(401).json({ msg: 'Token is not valid' });
  }
});

export default router;
