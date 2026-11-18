import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { AuthHero } from '../src/components/AuthHero';
import { OtpDigitsInput } from '../src/components/OtpDigitsInput';
import { PrimaryButton } from '../src/components/PrimaryButton';
import { CIRCA } from '../src/lib/theme';
import { confirmSignUpAndLogin, startPhoneAuth, verifyLoginOtp } from '../src/lib/cognito';
import { fetchMyProfile } from '../src/lib/api';
import { saveSession } from '../src/lib/session';

const RESEND_SECONDS = 60;

export default function OtpEntry() {
  const params = useLocalSearchParams<{ phone: string; mode: 'signup' | 'login'; session: string }>();
  const [code, setCode] = useState('');
  const [session, setSession] = useState(params.session);
  const [mode, setMode] = useState(params.mode);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(RESEND_SECONDS);
  // Cognito sends a 6-digit code for ConfirmSignUp, but an 8-digit code for the
  // SMS_OTP sign-in challenge — no pool setting controls this, it's fixed per flow.
  const codeLength = mode === 'signup' ? 6 : 8;

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const handleVerify = async () => {
    if (code.length < codeLength) {
      setError(`Enter the ${codeLength}-digit code.`);
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      const tokens =
        mode === 'signup'
          ? await confirmSignUpAndLogin(params.phone, code, session)
          : await verifyLoginOtp(params.phone, code, session);
      await saveSession(tokens);
      const profile = await fetchMyProfile(tokens.accessToken);
      router.replace(profile ? '/home' : '/onboarding');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Incorrect code. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setError(null);
    try {
      const result = await startPhoneAuth(params.phone);
      setSession(result.session);
      setMode(result.mode);
      setCode('');
      setSecondsLeft(RESEND_SECONDS);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resend the code.');
    } finally {
      setResending(false);
    }
  };

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: CIRCA.paper }} edges={['bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} className="flex-1">
        <ScrollView contentContainerClassName="flex-grow" keyboardShouldPersistTaps="handled">
          <AuthHero icon="phone" tagline="Secure mobile verification" stepLabel="02 — 03" onBack={() => router.back()} />

          <View className="px-6 pb-8 pt-8">
            <Text
              className="text-[28px] leading-[32px] tracking-tight"
              style={{ color: CIRCA.ink, fontFamily: 'Manrope_800ExtraBold' }}
            >
              Verify it&apos;s you
            </Text>
            <Text
              className="mt-3 text-[14px] leading-[20px]"
              style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}
            >
              Enter the {codeLength}-digit code sent to {params.phone}.
            </Text>

            <View className="mt-7">
              <OtpDigitsInput value={code} onChange={setCode} length={codeLength} />
              {error && (
                <Text className="mt-2 text-[11px]" style={{ color: CIRCA.danger }}>
                  {error}
                </Text>
              )}

              <View className="mt-5">
                <PrimaryButton onPress={handleVerify} loading={submitting}>
                  Verify & continue
                </PrimaryButton>
              </View>

              <Pressable
                onPress={handleResend}
                disabled={secondsLeft > 0 || resending}
                className="mt-4 min-h-[44px] items-center justify-center"
                accessibilityRole="button"
                accessibilityLabel="Resend code"
              >
                <Text
                  className="text-[13px] font-bold"
                  style={{ color: secondsLeft > 0 ? CIRCA.muted : CIRCA.brand, fontFamily: 'DMSans_700Bold' }}
                >
                  {resending
                    ? 'Sending…'
                    : secondsLeft > 0
                      ? `Resend code in ${Math.floor(secondsLeft / 60)}:${String(secondsLeft % 60).padStart(2, '0')}`
                      : 'Resend code'}
                </Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
