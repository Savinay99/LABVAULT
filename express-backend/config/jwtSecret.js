import { randomBytes } from 'node:crypto';

const configuredSecret = process.env.JWT_SECRET;

if (process.env.NODE_ENV === 'production' && !configuredSecret) {
  throw new Error('JWT_SECRET must be configured in production');
}

// A process-local key is suitable only for this isolated development prototype.
// Restarting the process invalidates its tokens; production must configure JWT_SECRET.
const jwtSecret = configuredSecret || randomBytes(48).toString('hex');

export default jwtSecret;
