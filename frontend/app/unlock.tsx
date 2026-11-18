import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router } from 'expo-router';
import { PrimaryButton } from '../src/components/PrimaryButton';
import { CIRCA } from '../src/lib/theme';
import { getAppLockMethod, promptBiometric, verifyPin, clearAppLock } from '../src/lib/appLock';
import { clearSession } from '../src/lib/session';

export default function Unlock() {
  const [method, setMethod] = useState<'biometric' | 'pin' | null>(null);
  const [checkingMethod, setCheckingMethod] = useState(true);
  const [pin, setPinInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const tryBiometric = async () => {
    setSubmitting(true);
    setError(null);
    const success = await promptBiometric();
    setSubmitting(false);
    if (success) {
      router.replace('/home');
    } else {
      setError('Could not verify. Try again.');
    }
  };

  useEffect(() => {
    (async () => {
      const m = await getAppLockMethod();
      setMethod(m);
      setCheckingMethod(false);
      if (m === 'biometric') {
        await tryBiometric();
      }
    })();
  }, []);

  const handlePinSubmit = async () => {
    setSubmitting(true);
    setError(null);
    const ok = await verifyPin(pin);
    setSubmitting(false);
    if (ok) {
      router.replace('/home');
    } else {
      setError('Incorrect PIN.');
      setPinInput('');
    }
  };

  const handleLogoutInstead = async () => {
    await clearAppLock();
    await clearSession();
    router.replace('/');
  };

  if (checkingMethod) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: CIRCA.paper }}>
        <ActivityIndicator color={CIRCA.brand} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: CIRCA.paper }}>
      <View className="flex-1 items-center justify-center px-6">
        <View className="h-16 w-16 items-center justify-center rounded-full" style={{ backgroundColor: CIRCA.brandSoft }}>
          <Feather name={method === 'biometric' ? 'smartphone' : 'lock'} size={26} color={CIRCA.brand} />
        </View>
        <Text className="mt-5 text-[20px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'Manrope_800ExtraBold' }}>
          Welcome back
        </Text>

        {method === 'biometric' ? (
          <>
            <Text className="mt-2 text-center text-[13px]" style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>
              Verify it&apos;s you to continue.
            </Text>
            {error && (
              <Text className="mt-3 text-[11px]" style={{ color: CIRCA.danger }}>
                {error}
              </Text>
            )}
            <View className="mt-5 w-full">
              <PrimaryButton onPress={tryBiometric} loading={submitting} icon="smartphone">
                Try again
              </PrimaryButton>
            </View>
          </>
        ) : (
          <>
            <Text className="mt-2 text-center text-[13px]" style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>
              Enter your 4-digit PIN.
            </Text>
            <TextInput
              value={pin}
              onChangeText={(t) => setPinInput(t.replace(/\D/g, '').slice(0, 4))}
              placeholder="••••"
              placeholderTextColor="#97A3AD"
              keyboardType="number-pad"
              secureTextEntry
              maxLength={4}
              autoFocus
              className="mt-6 h-14 w-40 rounded-[15px] text-center text-[20px] font-bold tracking-[0.4em]"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, color: CIRCA.ink, fontFamily: 'Manrope_700Bold' }}
            />
            {error && (
              <Text className="mt-3 text-[11px]" style={{ color: CIRCA.danger }}>
                {error}
              </Text>
            )}
            <View className="mt-6 w-full">
              <PrimaryButton onPress={handlePinSubmit} loading={submitting}>
                Unlock
              </PrimaryButton>
            </View>
          </>
        )}

        <Pressable onPress={handleLogoutInstead} className="mt-5 min-h-[44px] items-center justify-center">
          <Text className="text-[12.5px] font-semibold" style={{ color: CIRCA.muted, fontFamily: 'DMSans_600SemiBold' }}>
            Log out instead
          </Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}
