require('dotenv').config();
const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');
const path = require('path');

const serviceAccountPath = path.resolve(
  process.env.FIREBASE_SERVICE_ACCOUNT_PATH || './firebase-service-account.json'
);
admin.initializeApp({
  credential: admin.credential.cert(require(serviceAccountPath)),
});

const app = express();
app.use(cors());
app.use(express.json());

// phone -> { token, code, expiresAt }
// In-memory only, spike-grade. A real build needs a persistent store + rate limiting.
const sessions = new Map();

const OTP_TTL_MS = 5 * 60 * 1000;

function generateCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

app.post('/register-token', (req, res) => {
  const { phone, token } = req.body;
  if (!phone || !token) {
    return res.status(400).json({ error: 'phone and token are required' });
  }
  const existing = sessions.get(phone) || {};
  sessions.set(phone, { ...existing, token });
  res.json({ ok: true });
});

app.post('/send-otp', async (req, res) => {
  const { phone } = req.body;
  const session = sessions.get(phone);
  if (!session?.token) {
    return res.status(400).json({ error: 'no registered device token for this phone, call /register-token first' });
  }

  const code = generateCode();
  sessions.set(phone, { ...session, code, expiresAt: Date.now() + OTP_TTL_MS });

  try {
    await admin.messaging().send({
      token: session.token,
      data: {
        type: 'otp',
        code,
        phone,
      },
      android: { priority: 'high' },
      apns: {
        headers: { 'apns-priority': '10', 'apns-push-type': 'background' },
        payload: { aps: { 'content-available': 1 } },
      },
    });
    res.json({ ok: true, sentAt: Date.now() });
  } catch (err) {
    res.status(502).json({ error: 'fcm send failed', detail: err.message });
  }
});

app.post('/verify-otp', (req, res) => {
  const { phone, code } = req.body;
  const session = sessions.get(phone);
  if (!session?.code || !session.expiresAt) {
    return res.status(400).json({ error: 'no otp pending for this phone' });
  }
  if (Date.now() > session.expiresAt) {
    return res.status(401).json({ error: 'otp expired' });
  }
  if (session.code !== code) {
    return res.status(401).json({ error: 'otp mismatch' });
  }
  sessions.delete(phone);
  res.json({ ok: true, verified: true });
});

const port = process.env.PORT || 4100;
app.listen(port, () => console.log(`fcm-otp-spike server on :${port}`));
