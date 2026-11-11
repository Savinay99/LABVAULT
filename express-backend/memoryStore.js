import bcrypt from 'bcryptjs';

const users = [];
const themes = [
  { id: 'light', name: 'Light', primary: '#2563eb', background: '#ffffff', surface: '#f8fafc', text: '#0f172a' },
  { id: 'dark', name: 'Dark', primary: '#3b82f6', background: '#0f172a', surface: '#1e293b', text: '#f8fafc' },
  { id: 'neon', name: 'Neon', primary: '#22d3ee', background: '#020617', surface: '#0f172a', text: '#ffffff' },
];

const memoryStore = {
  users,
  themes,
  async findUserByEmail(email) {
    return users.find((u) => u.email === email.toLowerCase()) || null;
  },
  async findUserById(id) {
    return users.find((u) => u._id === id) || null;
  },
  async createUser({ name, email, password }) {
    const hash = await bcrypt.hash(password, 10);
    const user = { _id: Date.now().toString(), name, email: email.toLowerCase(), password: hash, role: 'user', theme: 'light', createdAt: new Date(), updatedAt: new Date() };
    users.push(user);
    return user;
  },
  async comparePassword(candidate, stored) {
    return bcrypt.compare(candidate, stored);
  },
  async getThemes() {
    return themes;
  },
};

export default memoryStore;
