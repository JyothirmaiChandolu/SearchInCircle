import { useEffect, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { PrimaryButton } from '../src/components/PrimaryButton';
import { CIRCA } from '../src/lib/theme';
import { createProfile, fetchMyProfile, getValidSession, ProfileError, type Purpose } from '../src/lib/api';

const PURPOSE_OPTIONS: { value: Purpose; label: string; icon: keyof typeof Feather.glyphMap }[] = [
  { value: 'HIRE_OR_STAFF', label: 'Hiring or staffing', icon: 'briefcase' },
  { value: 'FIND_WORK', label: 'Find work', icon: 'search' },
  { value: 'FIND_A_SERVICE', label: 'Find a service', icon: 'tool' },
  { value: 'PERSONAL_HOBBY', label: 'Personal / hobby', icon: 'heart' },
  { value: 'OTHER', label: 'Other', icon: 'more-horizontal' },
];

const USERNAME_PATTERN = /^[a-z0-9_]{3,24}$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Onboarding() {
  const [checkingProfile, setCheckingProfile] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [nickname, setNickname] = useState('');
  const [email, setEmail] = useState('');
  const [purpose, setPurpose] = useState<Purpose | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const session = await getValidSession();
      if (!session) {
        router.replace('/');
        return;
      }

      // Already onboarded (e.g. navigated back here after it already succeeded) —
      // don't show a form that can only fail with "profile already exists".
      const existingProfile = await fetchMyProfile(session.accessToken);
      if (existingProfile) {
        router.replace('/home');
        return;
      }

      setAccessToken(session.accessToken);
      setCheckingProfile(false);
    })();
  }, []);

  if (checkingProfile) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: CIRCA.paper }}>
        <ActivityIndicator color={CIRCA.brand} />
      </SafeAreaView>
    );
  }

  const handleContinue = async () => {
    if (!accessToken) return;

    if (!USERNAME_PATTERN.test(username)) {
      setError('Username must be 3-24 characters: lowercase letters, numbers, or underscores.');
      return;
    }
    if (nickname.trim().length < 1) {
      setError('Enter a nickname.');
      return;
    }
    if (email.trim() && !EMAIL_PATTERN.test(email.trim())) {
      setError('Enter a valid email address, or leave it blank.');
      return;
    }
    if (!purpose) {
      setError('Choose why you’re using SearchInCircle.');
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await createProfile(accessToken, {
        username,
        nickname: nickname.trim(),
        email: email.trim() || undefined,
        purpose,
      });
      router.replace('/app-lock-setup');
    } catch (err) {
      setError(err instanceof ProfileError ? err.message : 'Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: CIRCA.paper }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} className="flex-1">
        <ScrollView contentContainerClassName="flex-grow px-6 pb-8 pt-10" keyboardShouldPersistTaps="handled">
          <Text
            className="text-[26px] leading-[32px] tracking-tight"
            style={{ color: CIRCA.ink, fontFamily: 'Manrope_800ExtraBold' }}
          >
            Tell us about you
          </Text>
          <Text className="mt-2 text-[14px] leading-[20px]" style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>
            A few details and you&apos;re at your dashboard. Skills, resume, and your circle can all wait until later.
          </Text>

          <View className="mt-7">
            <Text className="mb-1.5 text-[12px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}>
              Username
            </Text>
            <TextInput
              value={username}
              onChangeText={(t) => setUsername(t.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
              placeholder="yourname"
              placeholderTextColor="#97A3AD"
              autoCapitalize="none"
              autoCorrect={false}
              className="h-14 rounded-[15px] px-4 text-[15px] font-semibold"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, color: CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}
            />
          </View>

          <View className="mt-4">
            <Text className="mb-1.5 text-[12px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}>
              Nickname
            </Text>
            <TextInput
              value={nickname}
              onChangeText={setNickname}
              placeholder="What should people call you?"
              placeholderTextColor="#97A3AD"
              className="h-14 rounded-[15px] px-4 text-[15px] font-semibold"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, color: CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}
            />
          </View>

          <View className="mt-4">
            <Text className="mb-1.5 text-[12px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}>
              Email <Text style={{ color: CIRCA.muted, fontFamily: 'DMSans_400Regular' }}>(optional)</Text>
            </Text>
            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor="#97A3AD"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              className="h-14 rounded-[15px] px-4 text-[15px] font-semibold"
              style={{ backgroundColor: CIRCA.soft, borderWidth: 1, borderColor: CIRCA.line, color: CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}
            />
          </View>

          <View className="mt-5">
            <Text className="mb-2 text-[12px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}>
              Why are you here?
            </Text>
            <View style={{ gap: 8 }}>
              {PURPOSE_OPTIONS.map((opt) => {
                const selected = purpose === opt.value;
                return (
                  <Pressable
                    key={opt.value}
                    onPress={() => setPurpose(opt.value)}
                    accessibilityRole="radio"
                    accessibilityState={{ selected }}
                    className="h-14 flex-row items-center rounded-[15px] px-4"
                    style={{
                      backgroundColor: selected ? CIRCA.brandSoft : CIRCA.soft,
                      borderWidth: selected ? 2 : 1,
                      borderColor: selected ? CIRCA.brand : CIRCA.line,
                    }}
                  >
                    <Feather name={opt.icon} size={18} color={selected ? CIRCA.brand : CIRCA.muted} />
                    <Text
                      className="ml-3 text-[14px] font-semibold"
                      style={{ color: selected ? CIRCA.brandDark : CIRCA.ink, fontFamily: 'DMSans_600SemiBold' }}
                    >
                      {opt.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          {error && (
            <Text className="mt-3 text-[11px]" style={{ color: CIRCA.danger }}>
              {error}
            </Text>
          )}

          <View className="mt-6">
            <PrimaryButton onPress={handleContinue} loading={submitting}>
              Continue
            </PrimaryButton>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
