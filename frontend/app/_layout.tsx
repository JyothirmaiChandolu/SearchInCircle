import '../global.css';

import { useEffect, useRef } from 'react';
import { AppState } from 'react-native';
import { useFonts, DMSans_400Regular, DMSans_500Medium, DMSans_600SemiBold, DMSans_700Bold } from '@expo-google-fonts/dm-sans';
import { Manrope_600SemiBold, Manrope_700Bold, Manrope_800ExtraBold } from '@expo-google-fonts/manrope';
import { router, Stack, usePathname } from 'expo-router';
import { isAppLockEnabled } from '../src/lib/appLock';

// Screens where it would be wrong to force a PIN/biometric prompt — the auth flow
// itself, and the unlock/setup screens, which already handle this on their own.
const APP_LOCK_EXEMPT_PATHS = new Set(['/', '/login', '/otp', '/onboarding', '/unlock', '/app-lock-setup']);

function AppLockOnResume() {
  const pathname = usePathname();
  const pathnameRef = useRef(pathname);

  useEffect(() => {
    pathnameRef.current = pathname;
  }, [pathname]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', async (state) => {
      if (state !== 'active') return;
      if (APP_LOCK_EXEMPT_PATHS.has(pathnameRef.current)) return;
      if (await isAppLockEnabled()) {
        router.replace('/unlock');
      }
    });
    return () => subscription.remove();
  }, []);

  return null;
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    DMSans_400Regular,
    DMSans_500Medium,
    DMSans_600SemiBold,
    DMSans_700Bold,
    Manrope_600SemiBold,
    Manrope_700Bold,
    Manrope_800ExtraBold,
  });

  if (!fontsLoaded) return null;

  return (
    <>
      <Stack screenOptions={{ headerShown: false }} />
      <AppLockOnResume />
    </>
  );
}
