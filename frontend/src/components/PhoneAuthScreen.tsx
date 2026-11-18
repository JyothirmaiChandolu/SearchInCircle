import { useEffect, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { AuthHero } from './AuthHero';
import { CountryCodeInput } from './CountryCodeInput';
import { PrimaryButton } from './PrimaryButton';
import { CIRCA } from '../lib/theme';
import { startPhoneAuth } from '../lib/cognito';
import { toE164 } from '../lib/phone';
import { fetchMe, fetchMyProfile, getValidSession } from '../lib/api';
import { isAppLockEnabled } from '../lib/appLock';
import { loadRememberedPhone, saveRememberedPhone } from '../lib/session';

const DEFAULT_COUNTRY = { dialCode: '+1', flag: '🇺🇸', code: 'US' };

type Copy = {
  tagline: string;
  title: string;
  subtitle: string;
  switchPrompt: string;
  switchLabel: string;
  switchHref: '/' | '/login';
};

const COPY: Record<'signup' | 'login', Copy> = {
  signup: {
    tagline: 'The right people, through people you trust.',
    title: 'Opportunity lives in your circle.',
    subtitle: 'Build a trusted network, share what you need, and discover the right fit through people you know.',
    switchPrompt: 'Already a member? ',
    switchLabel: 'Log in',
    switchHref: '/login',
  },
  login: {
    tagline: 'Welcome back to your circle.',
    title: 'Good to see you again.',
    subtitle: 'Log in with your mobile number to pick up right where you left off.',
    switchPrompt: 'New here? ',
    switchLabel: 'Create an account',
    switchHref: '/',
  },
};

/** Shared phone-entry UI for both the sign-up and login routes. Cognito itself decides
 * signup vs login per phone number (see startPhoneAuth) — this only changes the copy/CTA. */
export function PhoneAuthScreen({ variant }: { variant: 'signup' | 'login' }) {
  const copy = COPY[variant];
  const [phone, setPhone] = useState('');
  const [country, setCountry] = useState(DEFAULT_COUNTRY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    (async () => {
      // Quick unlock set up on this device? Go straight there — never show phone/OTP
      // again as long as a PIN or biometric is configured, even if the underlying
      // Cognito session needs a refresh (unlock → home re-validates that).
      if (await isAppLockEnabled()) {
        router.replace('/unlock');
        return;
      }

      const session = await getValidSession();
      if (session && (await fetchMe(session.accessToken))) {
        const profile = await fetchMyProfile(session.accessToken);
        router.replace(profile ? '/home' : '/onboarding');
        return;
      }

      // No usable session — at least save the user retyping their number.
      const remembered = await loadRememberedPhone();
      if (remembered) {
        setCountry(remembered.country);
        setPhone(remembered.phone);
      }
      setCheckingSession(false);
    })();
  }, []);

  const handleContinue = async () => {
    if (phone.trim().replace(/\D/g, '').length < 6) {
      setError('Enter a valid mobile number.');
      return;
    }

    const e164Phone = toE164(country.dialCode, phone);
    setError(null);
    setSubmitting(true);
    try {
      const { mode, session } = await startPhoneAuth(e164Phone);
      await saveRememberedPhone(country, phone);
      router.push({ pathname: '/otp', params: { phone: e164Phone, mode, session } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (checkingSession) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: CIRCA.paper }}>
        <ActivityIndicator color={CIRCA.brand} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: CIRCA.paper }} edges={['bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} className="flex-1">
        <ScrollView contentContainerClassName="flex-grow" keyboardShouldPersistTaps="handled">
          <AuthHero icon="users" tagline={copy.tagline} />

          <View className="px-6 pb-8 pt-8">
            <Text
              className="max-w-[340px] text-[28px] leading-[32px] tracking-tight"
              style={{ color: CIRCA.ink, fontFamily: 'Manrope_800ExtraBold' }}
            >
              {copy.title}
            </Text>
            <Text className="mt-3 text-[14px] leading-[20px]" style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>
              {copy.subtitle}
            </Text>

            <View
              className="mt-6 h-14 flex-row items-center overflow-hidden rounded-[15px]"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line }}
            >
              <CountryCodeInput value={country} onChange={setCountry} />
              <TextInput
                value={phone}
                onChangeText={setPhone}
                placeholder="98765 43210"
                placeholderTextColor="#97A3AD"
                keyboardType="phone-pad"
                autoComplete="tel"
                textContentType="telephoneNumber"
                accessibilityLabel="Mobile number"
                className="h-full flex-1 px-4 text-[15px] font-semibold"
                style={{ color: CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}
              />
            </View>
            {error && (
              <Text className="mt-2 text-[11px]" style={{ color: CIRCA.danger }}>
                {error}
              </Text>
            )}

            <View className="mt-4">
              <PrimaryButton onPress={handleContinue} loading={submitting}>
                Send OTP
              </PrimaryButton>
            </View>

            <Pressable
              onPress={() => router.replace(copy.switchHref)}
              accessibilityRole="button"
              accessibilityLabel={`${copy.switchPrompt}${copy.switchLabel}`}
              className="mt-5 min-h-[32px] flex-row items-center justify-center"
            >
              <Text className="text-[12.5px]" style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>
                {copy.switchPrompt}
              </Text>
              <Text className="text-[12.5px] font-bold" style={{ color: CIRCA.brand, fontFamily: 'DMSans_700Bold' }}>
                {copy.switchLabel}
              </Text>
            </Pressable>

            <Text className="mt-3 text-center text-[11px] leading-[16px]" style={{ color: CIRCA.muted }}>
              By continuing, you agree to our Terms and Privacy Policy.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
