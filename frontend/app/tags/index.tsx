import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { AURORA } from '../../src/lib/theme';
import { fetchMyTags, getValidSession, type Tag } from '../../src/lib/api';

export default function TagsList() {
  const [loading, setLoading] = useState(true);
  const [tags, setTags] = useState<Tag[]>([]);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        const session = await getValidSession();
        if (!session) {
          router.replace('/');
          return;
        }
        setTags(await fetchMyTags(session.accessToken));
        setLoading(false);
      })();
    }, []),
  );

  const openEdit = (tag: Tag) => {
    router.push({ pathname: '/tags/[id]', params: { id: tag.id, tag: JSON.stringify(tag) } });
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
              People you&apos;ve tagged
            </Text>
          </View>

          <Pressable
            onPress={() => router.push('/tags/new')}
            className="h-10 w-10 items-center justify-center rounded-full"
            style={{ backgroundColor: AURORA.primary }}
            accessibilityRole="button"
            accessibilityLabel="Tag someone new"
          >
            <Feather name="plus" size={18} color="#fff" />
          </Pressable>
        </View>

        {tags.length === 0 ? (
          <View className="mt-10 items-center">
            <Text className="text-center text-[13.5px]" style={{ color: AURORA.ink2 }}>
              No one tagged yet. Tag someone you know and trust to make their skills discoverable
              inside your circle.
            </Text>
          </View>
        ) : (
          <View className="mt-6" style={{ gap: 10 }}>
            {tags.map((tag) => (
              <Pressable
                key={tag.id}
                onPress={() => openEdit(tag)}
                className="flex-row items-center rounded-[16px] p-4"
                style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}
              >
                <View className="h-11 w-11 items-center justify-center rounded-full" style={{ backgroundColor: AURORA.avBg }}>
                  <Text className="text-[15px] font-bold" style={{ color: AURORA.avFg }}>
                    {tag.person.name.charAt(0).toUpperCase()}
                  </Text>
                </View>
                <View className="ml-3 flex-1">
                  <Text className="text-[14.5px] font-bold" style={{ color: AURORA.ink }}>
                    {tag.person.name}
                    {tag.nickname ? ` · ${tag.nickname}` : ''}
                  </Text>
                  <Text className="mt-0.5 text-[12px]" style={{ color: AURORA.ink2 }} numberOfLines={1}>
                    {[...tag.skills, ...tag.tools].slice(0, 4).join(', ') || 'No skills added yet'}
                  </Text>
                </View>
                <View
                  className="rounded-full px-2.5 py-1"
                  style={{ backgroundColor: tag.isOpen ? '#E1F4EA' : AURORA.surface2 }}
                >
                  <Text className="text-[10px] font-bold uppercase" style={{ color: tag.isOpen ? '#2E9B6B' : AURORA.ink3 }}>
                    {tag.isOpen ? 'Open' : 'Closed'}
                  </Text>
                </View>
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
