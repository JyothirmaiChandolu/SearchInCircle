import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// expo-secure-store only supports iOS/Android/tvOS. Web has no secure-storage
// equivalent, so fall back to localStorage there — web is a dev-preview
// convenience only, not a real target platform for this app.
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
  accessToken: 'sic_access_token',
  idToken: 'sic_id_token',
  refreshToken: 'sic_refresh_token',
  expiresAt: 'sic_expires_at',
  rememberedDialCode: 'sic_remembered_dial_code',
  rememberedPhone: 'sic_remembered_phone',
} as const;

export type StoredSession = {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresAt: number;
};

export async function saveSession(tokens: {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresIn: number;
}): Promise<void> {
  const expiresAt = Date.now() + tokens.expiresIn * 1000;
  await Promise.all([
    store.setItem(KEYS.accessToken, tokens.accessToken),
    store.setItem(KEYS.idToken, tokens.idToken),
    store.setItem(KEYS.refreshToken, tokens.refreshToken),
    store.setItem(KEYS.expiresAt, String(expiresAt)),
  ]);
}

export async function updateAccessToken(accessToken: string, idToken: string, expiresIn: number): Promise<void> {
  const expiresAt = Date.now() + expiresIn * 1000;
  await Promise.all([
    store.setItem(KEYS.accessToken, accessToken),
    store.setItem(KEYS.idToken, idToken),
    store.setItem(KEYS.expiresAt, String(expiresAt)),
  ]);
}

export async function loadSession(): Promise<StoredSession | null> {
  const [accessToken, idToken, refreshToken, expiresAt] = await Promise.all([
    store.getItem(KEYS.accessToken),
    store.getItem(KEYS.idToken),
    store.getItem(KEYS.refreshToken),
    store.getItem(KEYS.expiresAt),
  ]);

  if (!accessToken || !idToken || !refreshToken || !expiresAt) {
    return null;
  }

  return { accessToken, idToken, refreshToken, expiresAt: Number(expiresAt) };
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    store.removeItem(KEYS.accessToken),
    store.removeItem(KEYS.idToken),
    store.removeItem(KEYS.refreshToken),
    store.removeItem(KEYS.expiresAt),
  ]);
}

type RememberedCountry = { dialCode: string; flag: string; code: string };

/** Not sensitive — just so a returning user never has to retype their number. */
export async function saveRememberedPhone(country: RememberedCountry, phone: string): Promise<void> {
  await Promise.all([store.setItem(KEYS.rememberedDialCode, JSON.stringify(country)), store.setItem(KEYS.rememberedPhone, phone)]);
}

export async function loadRememberedPhone(): Promise<{ country: RememberedCountry; phone: string } | null> {
  const [countryJson, phone] = await Promise.all([store.getItem(KEYS.rememberedDialCode), store.getItem(KEYS.rememberedPhone)]);
  if (!countryJson || !phone) return null;
  try {
    return { country: JSON.parse(countryJson), phone };
  } catch {
    return null;
  }
}

export async function clearRememberedPhone(): Promise<void> {
  await Promise.all([store.removeItem(KEYS.rememberedDialCode), store.removeItem(KEYS.rememberedPhone)]);
}
