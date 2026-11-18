import React, { useEffect, useState } from 'react';
import { SafeAreaView, View, Text, TextInput, Button, StyleSheet, Alert } from 'react-native';
import messaging from '@react-native-firebase/messaging';

// A physical device can't reach your laptop's "localhost" — use your
// machine's LAN IP (ipconfig getifaddr en0 on macOS) instead.
const SERVER_URL = 'http://YOUR_LOCAL_IP:4100';

export default function App() {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [receivedCode, setReceivedCode] = useState(null);
  const [status, setStatus] = useState('idle');
  const [fcmToken, setFcmToken] = useState(null);

  useEffect(() => {
    requestPermissionAndRegister();

    const unsubscribe = messaging().onMessage(async (remoteMessage) => {
      if (remoteMessage.data?.type === 'otp') {
        setReceivedCode(remoteMessage.data.code);
      }
    });
    return unsubscribe;
  }, []);

  async function requestPermissionAndRegister() {
    const authStatus = await messaging().requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;
    if (!enabled) {
      setStatus('push permission denied');
      return;
    }
    const token = await messaging().getToken();
    setFcmToken(token);
    setStatus(`fcm token acquired: ${token.slice(0, 12)}...`);
  }

  async function registerToken() {
    if (!phone || !fcmToken) {
      Alert.alert('Enter a phone number and wait for the FCM token first.');
      return;
    }
    await fetch(`${SERVER_URL}/register-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, token: fcmToken }),
    });
    setStatus('token registered with server');
  }

  async function sendOtp() {
    const res = await fetch(`${SERVER_URL}/send-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    const body = await res.json();
    setStatus(res.ok ? 'otp sent — waiting for push' : `send failed: ${body.error}`);
  }

  async function verifyOtp() {
    const res = await fetch(`${SERVER_URL}/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, code }),
    });
    const body = await res.json();
    setStatus(res.ok ? 'verified' : `verify failed: ${body.error}`);
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>FCM OTP spike</Text>
      <Text style={styles.status}>{status}</Text>

      <TextInput
        style={styles.input}
        placeholder="Phone number"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
      />
      <Button title="Register device token" onPress={registerToken} />
      <View style={styles.spacer} />
      <Button title="Send OTP" onPress={sendOtp} />

      <View style={styles.spacer} />
      {receivedCode && <Text style={styles.received}>Received via push: {receivedCode}</Text>}

      <TextInput
        style={styles.input}
        placeholder="Enter code (or use received one)"
        value={code}
        onChangeText={setCode}
        keyboardType="number-pad"
      />
      <Button title="Verify" onPress={verifyOtp} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 8 },
  status: { color: '#555', marginBottom: 16 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 12 },
  spacer: { height: 12 },
  received: { color: 'green', fontWeight: '600', marginBottom: 12 },
});
