import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import * as LocalAuthentication from 'expo-local-authentication';

const store = {
  getItem: (key: string) =>
    Platform.OS === 'web' ? Promise.resolve(globalThis.localStorage?.getItem(key) ?? null) : SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) =>
    Platform.OS === 'web'
      ? Promise.resolve(globalThis.localStorage?.setItem(key, value))
      : SecureStore.setItemAsync(key, value),
  removeItem: (key: string) =>
    Platform.OS === 'web' ? Promise.resolve(globalThis.localStorage?.removeItem(key)) : SecureStore.deleteItemAsync(key),
};

const KEYS = {
  method: 'sic_app_lock_method', // 'biometric' | 'pin' | undefined (not set up)
  pinHash: 'sic_app_lock_pin_hash',
} as const;

export type AppLockMethod = 'biometric' | 'pin';

/** Whether this device can prompt Face ID / fingerprint at all. */
export async function canUseBiometrics(): Promise<boolean> {
  const [hasHardware, isEnrolled] = await Promise.all([
    LocalAuthentication.hasHardwareAsync(),
    LocalAuthentication.isEnrolledAsync(),
  ]);
  return hasHardware && isEnrolled;
}

export async function getAppLockMethod(): Promise<AppLockMethod | null> {
  const method = await store.getItem(KEYS.method);
  return method === 'biometric' || method === 'pin' ? method : null;
}

export async function isAppLockEnabled(): Promise<boolean> {
  return (await getAppLockMethod()) !== null;
}

export async function enableBiometricLock(): Promise<void> {
  await store.setItem(KEYS.method, 'biometric');
}

async function hashPin(pin: string): Promise<string> {
  return Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, pin);
}

export async function setPin(pin: string): Promise<void> {
  const hash = await hashPin(pin);
  await store.setItem(KEYS.pinHash, hash);
  await store.setItem(KEYS.method, 'pin');
}

export async function verifyPin(pin: string): Promise<boolean> {
  const stored = await store.getItem(KEYS.pinHash);
  if (!stored) return false;
  return (await hashPin(pin)) === stored;
}

/** Prompts Face ID / fingerprint. Resolves true only on a genuine success. */
export async function promptBiometric(): Promise<boolean> {
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Unlock SearchInCircle',
    cancelLabel: 'Use PIN instead',
    disableDeviceFallback: true,
  });
  return result.success;
}

/** Clears the app-lock setup — called on a full log out, not on every unlock. */
export async function clearAppLock(): Promise<void> {
  await store.removeItem(KEYS.method);
  await store.removeItem(KEYS.pinHash);
}
