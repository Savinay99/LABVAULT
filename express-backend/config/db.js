import mongoose from 'mongoose';

let connected = false;

const connectDB = async () => {
  try {
    await mongoose.connect(process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/gsap-theme-db');
    connected = true;
    console.log('MongoDB connected');
  } catch (err) {
    connected = false;
    console.warn('MongoDB unavailable — running in-memory fallback:', err.message);
  }
};

export { connectDB, connected };
