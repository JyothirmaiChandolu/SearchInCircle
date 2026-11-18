import { useEffect, useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router } from 'expo-router';
import { PrimaryButton } from '../src/components/PrimaryButton';
import { CIRCA } from '../src/lib/theme';
import { canUseBiometrics, enableBiometricLock, promptBiometric, setPin } from '../src/lib/appLock';

const PIN_PATTERN = /^\d{4}$/;

export default function AppLockSetup() {
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [mode, setMode] = useState<'choose' | 'pin'>('choose');
  const [pin, setPinInput] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    canUseBiometrics().then(setBiometricAvailable);
  }, []);

  const finish = () => router.replace('/home');

  const handleEnableBiometric = async () => {
    setSubmitting(true);
    setError(null);
    const success = await promptBiometric();
    setSubmitting(false);
    if (!success) {
      setError('Could not verify. Try again, or set up a PIN instead.');
      return;
    }
    await enableBiometricLock();
    finish();
  };

  const handleSavePin = async () => {
    if (!PIN_PATTERN.test(pin)) {
      setError('PIN must be exactly 4 digits.');
      return;
    }
    if (pin !== confirmPin) {
      setError('PINs don’t match.');
      return;
    }
    setError(null);
    setSubmitting(true);
    await setPin(pin);
    setSubmitting(false);
    finish();
  };

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: CIRCA.paper }}>
      <View className="flex-1 px-6 pt-10">
        <Text
          className="text-[26px] leading-[32px] tracking-tight"
          style={{ color: CIRCA.ink, fontFamily: 'Manrope_800ExtraBold' }}
        >
          Quick unlock
        </Text>
        <Text className="mt-2 text-[14px] leading-[20px]" style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>
          Skip retyping your phone number and OTP every time. Unlock with {biometricAvailable ? 'your fingerprint/Face ID or a' : 'a'}{' '}
          4-digit PIN instead.
        </Text>

        {mode === 'choose' ? (
          <View className="mt-8" style={{ gap: 10 }}>
            {biometricAvailable && (
              <Pressable
                onPress={handleEnableBiometric}
                disabled={submitting}
                className="h-14 flex-row items-center rounded-[15px] px-4"
                style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, opacity: submitting ? 0.6 : 1 }}
              >
                <Feather name="smartphone" size={18} color={CIRCA.brand} />
                <Text className="ml-3 text-[14px] font-semibold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}>
                  Use fingerprint / Face ID
                </Text>
              </Pressable>
            )}

            <Pressable
              onPress={() => setMode('pin')}
              className="h-14 flex-row items-center rounded-[15px] px-4"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line }}
            >
              <Feather name="hash" size={18} color={CIRCA.brand} />
              <Text className="ml-3 text-[14px] font-semibold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}>
                Create a 4-digit PIN
              </Text>
            </Pressable>

            <Pressable onPress={finish} className="mt-2 min-h-[44px] items-center justify-center">
              <Text className="text-[13px] font-semibold" style={{ color: CIRCA.muted, fontFamily: 'DMSans_600SemiBold' }}>
                Skip for now
              </Text>
            </Pressable>
          </View>
        ) : (
          <View className="mt-8">
            <Text className="mb-1.5 text-[12px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}>
              Create PIN
            </Text>
            <TextInput
              value={pin}
              onChangeText={(t) => setPinInput(t.replace(/\D/g, '').slice(0, 4))}
              placeholder="••••"
              placeholderTextColor="#97A3AD"
              keyboardType="number-pad"
              secureTextEntry
              maxLength={4}
              className="h-14 rounded-[15px] px-4 text-[18px] font-bold tracking-[0.3em]"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, color: CIRCA.ink, fontFamily: 'Manrope_700Bold' }}
            />

            <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}>
              Confirm PIN
            </Text>
            <TextInput
              value={confirmPin}
              onChangeText={(t) => setConfirmPin(t.replace(/\D/g, '').slice(0, 4))}
              placeholder="••••"
              placeholderTextColor="#97A3AD"
              keyboardType="number-pad"
              secureTextEntry
              maxLength={4}
              className="h-14 rounded-[15px] px-4 text-[18px] font-bold tracking-[0.3em]"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, color: CIRCA.ink, fontFamily: 'Manrope_700Bold' }}
            />

            {error && (
              <Text className="mt-3 text-[11px]" style={{ color: CIRCA.danger }}>
                {error}
              </Text>
            )}

            <View className="mt-6">
              <PrimaryButton onPress={handleSavePin} loading={submitting}>
                Save PIN
              </PrimaryButton>
            </View>
          </View>
        )}

        {mode === 'choose' && error && (
          <Text className="mt-3 text-[11px]" style={{ color: CIRCA.danger }}>
            {error}
          </Text>
        )}
      </View>
    </SafeAreaView>
  );
}
