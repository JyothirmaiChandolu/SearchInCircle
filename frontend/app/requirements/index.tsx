import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { AURORA } from '../../src/lib/theme';
import { deleteRequirement, fetchMyRequirements, getValidSession, updateRequirement, type Requirement } from '../../src/lib/api';

export default function RequirementsList() {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [requirements, setRequirements] = useState<Requirement[]>([]);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        const session = await getValidSession();
        if (!session) {
          router.replace('/');
          return;
        }
        setAccessToken(session.accessToken);
        setRequirements(await fetchMyRequirements(session.accessToken));
        setLoading(false);
      })();
    }, []),
  );

  const toggleOpen = async (requirement: Requirement) => {
    if (!accessToken) return;
    const updated = await updateRequirement(accessToken, requirement.id, { isOpen: !requirement.isOpen });
    setRequirements((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  };

  const remove = async (requirement: Requirement) => {
    if (!accessToken) return;
    await deleteRequirement(accessToken, requirement.id);
    setRequirements((prev) => prev.filter((r) => r.id !== requirement.id));
  };

  if (loading) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: AURORA.bg }}>
        <ActivityIndicator color={AURORA.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: AURORA.bg }}>
      <ScrollView contentContainerClassName="px-6 pb-10 pt-6">
        <View className="flex-row items-center justify-between">
          <View className="flex-row items-center">
            <Pressable
              onPress={() => router.back()}
              className="h-9 w-9 items-center justify-center rounded-full"
              style={{ backgroundColor: '#fff' }}
              accessibilityRole="button"
              accessibilityLabel="Back"
            >
              <Feather name="arrow-left" size={18} color={AURORA.ink} />
            </Pressable>
            <Text className="ml-3 text-[20px] font-bold tracking-tight" style={{ color: AURORA.ink }}>
              Your requirements
            </Text>
          </View>

          <Pressable
            onPress={() => router.push('/requirements/new')}
            className="h-10 w-10 items-center justify-center rounded-full"
            style={{ backgroundColor: AURORA.primary }}
            accessibilityRole="button"
            accessibilityLabel="Post a requirement"
          >
            <Feather name="plus" size={18} color="#fff" />
          </Pressable>
        </View>

        {requirements.length === 0 ? (
          <View className="mt-10 items-center">
            <Text className="text-center text-[13.5px]" style={{ color: AURORA.ink2 }}>
              Nothing posted yet. Describe what you need and matches will surface from your circle.
            </Text>
          </View>
        ) : (
          <View className="mt-6" style={{ gap: 10 }}>
            {requirements.map((req) => (
              <View
                key={req.id}
                className="rounded-[16px] p-4"
                style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}
              >
                <View className="flex-row items-start justify-between">
                  <Text className="flex-1 text-[14.5px] font-bold" style={{ color: AURORA.ink }}>
                    {req.title}
                  </Text>
                  <Pressable onPress={() => remove(req)} className="ml-2 h-6 w-6 items-center justify-center">
                    <Feather name="trash-2" size={15} color={AURORA.danger} />
                  </Pressable>
                </View>
                <Text className="mt-1 text-[12px] leading-[17px]" style={{ color: AURORA.ink2 }} numberOfLines={2}>
                  {req.description}
                </Text>
                <Text className="mt-1.5 text-[11.5px]" style={{ color: AURORA.ink3 }}>
                  {req.workType === 'REMOTE' ? 'Remote' : req.location} · {req.skillsNeeded.join(', ') || 'No skills listed'}
                </Text>

                <View className="mt-3 flex-row items-center justify-between">
                  <Text className="text-[12.5px] font-semibold" style={{ color: req.isOpen ? '#2E9B6B' : AURORA.ink3 }}>
                    {req.isOpen ? 'Open — accepting matches' : 'Closed'}
                  </Text>
                  <Switch value={req.isOpen} onValueChange={() => toggleOpen(req)} trackColor={{ true: AURORA.primary }} />
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
