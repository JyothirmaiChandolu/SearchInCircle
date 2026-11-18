import { useEffect, useState } from 'react';
import { ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { TagForm } from '../../src/components/TagForm';
import { AURORA } from '../../src/lib/theme';
import { getValidSession } from '../../src/lib/api';

export default function NewTag() {
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const session = await getValidSession();
      if (!session) {
        router.replace('/');
        return;
      }
      setAccessToken(session.accessToken);
    })();
  }, []);

  if (!accessToken) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: AURORA.bg }}>
        <ActivityIndicator color={AURORA.primary} />
      </SafeAreaView>
    );
  }

  return <TagForm accessToken={accessToken} mode="create" />;
}
