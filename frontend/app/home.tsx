import { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router } from 'expo-router';
import { AURORA } from '../src/lib/theme';
import { fetchMe, fetchMyProfile, getValidSession, PURPOSE_LABELS, type Profile } from '../src/lib/api';
import { clearAppLock, isAppLockEnabled } from '../src/lib/appLock';
import { clearSession } from '../src/lib/session';

type NextStep = {
  title: string;
  description: string;
  icon: keyof typeof Feather.glyphMap;
  accent: string;
  accentSoft: string;
  href?: '/skills' | '/tags' | '/requirements';
};

const NEXT_STEPS: NextStep[] = [
  {
    title: 'Add your skills',
    description: 'Record what you do, or upload a resume and we’ll suggest the rest.',
    icon: 'star',
    accent: '#2E9B6B',
    accentSoft: '#E1F4EA',
    href: '/skills',
  },
  {
    title: 'Tag someone you know',
    description: 'Describe a person you trust, even if they don’t have an account yet.',
    icon: 'user-plus',
    accent: AURORA.hue4,
    accentSoft: '#F0EBFC',
    href: '/tags',
  },
  {
    title: 'Build your circle',
    description: 'Connect with people you trust so matches can surface between you.',
    icon: 'users',
    accent: AURORA.primary,
    accentSoft: AURORA.avBg,
  },
  {
    title: 'Post a requirement',
    description: 'Describe what you need — matches surface from inside your circle.',
    icon: 'clipboard',
    accent: AURORA.hue3,
    accentSoft: '#E6F4FB',
    href: '/requirements',
  },
];

export default function Home() {
  const [checking, setChecking] = useState(true);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [appLockEnabled, setAppLockEnabled] = useState(false);

  useEffect(() => {
    (async () => {
      const session = await getValidSession();
      const me = session ? await fetchMe(session.accessToken) : null;

      if (!session || !me) {
        // Underlying Cognito session truly died (refresh token expired/revoked) —
        // clear the local app-lock too, or /login would keep bouncing back here.
        await clearAppLock();
        await clearSession();
        router.replace('/');
        return;
      }

      const fetchedProfile = await fetchMyProfile(session.accessToken);
      if (!fetchedProfile) {
        router.replace('/onboarding');
        return;
      }

      setProfile(fetchedProfile);
      setAppLockEnabled(await isAppLockEnabled());
      setChecking(false);
    })();
  }, []);

  const handleLogout = async () => {
    if (appLockEnabled) {
      // Quick unlock is set up — lock the app instead of wiping the session.
      // Next open asks for PIN/biometric, not phone+OTP.
      router.replace('/unlock');
      return;
    }
    await clearAppLock();
    await clearSession();
    router.replace('/');
  };

  if (checking) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: AURORA.bg }}>
        <ActivityIndicator color={AURORA.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: AURORA.bg }}>
      <ScrollView contentContainerClassName="px-6 pb-10 pt-6" showsVerticalScrollIndicator={false}>
        <View className="flex-row items-center justify-between">
          <View>
            <Text className="text-[13px] font-semibold" style={{ color: AURORA.ink3 }}>
              Welcome back
            </Text>
            <Text className="mt-0.5 text-[24px] font-bold tracking-tight" style={{ color: AURORA.ink }}>
              {profile?.nickname}
            </Text>
          </View>

          <Pressable
            onPress={() => setMenuOpen(true)}
            className="h-11 w-11 items-center justify-center rounded-full"
            style={{ backgroundColor: AURORA.avBg }}
            accessibilityRole="button"
            accessibilityLabel="Profile menu"
          >
            <Feather name="user" size={20} color={AURORA.avFg} />
          </Pressable>
        </View>

        <View
          className="mt-6 flex-row items-center rounded-[18px] p-4"
          style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}
        >
          <View className="h-12 w-12 items-center justify-center rounded-full" style={{ backgroundColor: AURORA.avBg }}>
            <Text className="text-[16px] font-bold" style={{ color: AURORA.avFg }}>
              {profile?.nickname?.charAt(0).toUpperCase()}
            </Text>
          </View>
          <View className="ml-3 flex-1">
            <Text className="text-[14.5px] font-bold" style={{ color: AURORA.ink }}>
              @{profile?.username}
            </Text>
            <Text className="mt-0.5 text-[12px]" style={{ color: AURORA.ink2 }}>
              {profile && PURPOSE_LABELS[profile.purpose]}
            </Text>
          </View>
        </View>

        <Text className="mb-3 mt-7 text-[13px] font-bold uppercase tracking-wide" style={{ color: AURORA.ink3 }}>
          What&apos;s next
        </Text>

        <View style={{ gap: 10 }}>
          {NEXT_STEPS.map((step) => {
            const CardWrapper = step.href ? Pressable : View;
            return (
              <CardWrapper
                key={step.title}
                onPress={step.href ? () => router.push(step.href!) : undefined}
                className="flex-row items-start rounded-[18px] p-4"
                style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}
              >
                <View
                  className="h-11 w-11 items-center justify-center rounded-[13px]"
                  style={{ backgroundColor: step.accentSoft }}
                >
                  <Feather name={step.icon} size={20} color={step.accent} />
                </View>
                <View className="ml-3.5 flex-1">
                  <View className="flex-row items-center justify-between">
                    <Text className="text-[14.5px] font-bold" style={{ color: AURORA.ink }}>
                      {step.title}
                    </Text>
                    {step.href ? (
                      <Feather name="chevron-right" size={16} color={AURORA.ink3} />
                    ) : (
                      <View className="rounded-full px-2.5 py-1" style={{ backgroundColor: AURORA.surface2 }}>
                        <Text className="text-[10px] font-bold uppercase" style={{ color: AURORA.ink3 }}>
                          Coming soon
                        </Text>
                      </View>
                    )}
                  </View>
                  <Text className="mt-1 text-[12.5px] leading-[17px]" style={{ color: AURORA.ink2 }}>
                    {step.description}
                  </Text>
                </View>
              </CardWrapper>
            );
          })}
        </View>
      </ScrollView>

      <Modal visible={menuOpen} transparent animationType="fade" onRequestClose={() => setMenuOpen(false)}>
        <Pressable style={{ flex: 1 }} onPress={() => setMenuOpen(false)}>
          <View
            className="absolute w-44 rounded-[14px] py-1.5"
            style={{
              top: 64,
              right: 24,
              backgroundColor: '#fff',
              borderWidth: 1,
              borderColor: AURORA.line,
              shadowColor: '#000',
              shadowOpacity: 0.12,
              shadowRadius: 12,
              shadowOffset: { width: 0, height: 6 },
              elevation: 6,
            }}
          >
            <Pressable
              onPress={() => {
                setMenuOpen(false);
                router.push('/app-lock-setup');
              }}
              className="flex-row items-center gap-2.5 px-4 py-3"
              accessibilityRole="button"
              accessibilityLabel="Quick unlock settings"
            >
              <Feather name="lock" size={16} color={AURORA.ink} />
              <Text className="text-[13.5px] font-semibold" style={{ color: AURORA.ink }}>
                {appLockEnabled ? 'Change quick unlock' : 'Set up quick unlock'}
              </Text>
            </Pressable>

            <View style={{ height: 1, backgroundColor: AURORA.line, marginVertical: 4 }} />

            <Pressable
              onPress={() => {
                setMenuOpen(false);
                handleLogout();
              }}
              className="flex-row items-center gap-2.5 px-4 py-3"
              accessibilityRole="button"
              accessibilityLabel="Log out"
            >
              <Feather name="log-out" size={16} color={AURORA.danger} />
              <Text className="text-[13.5px] font-semibold" style={{ color: AURORA.danger }}>
                Log out
              </Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
